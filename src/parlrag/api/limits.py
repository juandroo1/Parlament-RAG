"""Schutz der öffentlichen Demo (Task 6.3a): Kostendeckel und Rate-Limit pro Besucher.

- **Kostendeckel:** `DEMO_MONTHLY_BUDGET_USD` gilt pro Kalendermonat (UTC). Jeden Tag steht der
  noch verfügbare Rest geteilt durch die verbleibenden Tage zur Verfügung. Was ein ruhiger Tag
  nicht braucht, verteilt sich so auf die restlichen Tage, und ein Ansturm verbraucht nie mehr als
  das Budget eines Tages. Die Ausgaben stehen in der Tabelle `api_usage` und überstehen einen
  Neustart. Geprüft wird vor dem Aufruf; eine einzelne Anfrage kann das Tagesbudget also um ihre
  eigenen Kosten überschreiten (mit Haiku rund 0,002 USD).
- **Rate-Limit:** `RATE_LIMIT_PER_HOUR` Fragen pro IP in einem gleitenden Fenster von einer Stunde.
  Die IP-Adressen bleiben nur im Arbeitsspeicher und werden nicht geloggt.

Beide Grenzen sind mit dem Wert 0 ausgeschaltet (Standard, lokale Entwicklung).
"""

import calendar
import datetime as dt
import math
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import Engine, text

SECONDS_PER_HOUR = 3600


class LimitExceeded(Exception):
    """Die Anfrage überschreitet eine Grenze der Demo; `retry_after` in Sekunden."""

    def __init__(self, kind: str, message: str, retry_after: int) -> None:
        super().__init__(message)
        self.kind = kind
        self.message = message
        self.retry_after = retry_after


def daily_allowance(monthly_budget: float, spent_before_today: float, today: dt.date) -> float:
    """Tagesbudget: Rest des Monatsbudgets geteilt durch die Tage ab heute bis Monatsende."""
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    days_left = days_in_month - today.day + 1
    return max(0.0, monthly_budget - spent_before_today) / days_left


def seconds_until_tomorrow(now: dt.datetime) -> int:
    tomorrow = dt.datetime.combine(now.date() + dt.timedelta(days=1), dt.time(), tzinfo=dt.UTC)
    return max(1, math.ceil((tomorrow - now).total_seconds()))


class UsageStore(Protocol):
    def spent(self, today: dt.date) -> tuple[float, float]:
        """Ausgaben im laufenden Monat vor heute und heute, in USD."""
        ...

    def record(self, day: dt.date, cost_usd: float) -> None: ...


class PostgresUsageStore:
    """Ausgaben pro Tag in der Tabelle `api_usage` (Migration 0002)."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def spent(self, today: dt.date) -> tuple[float, float]:
        query = text(
            """
            SELECT
                coalesce(sum(cost_usd) FILTER (WHERE day < :today), 0),
                coalesce(sum(cost_usd) FILTER (WHERE day = :today), 0)
            FROM api_usage
            WHERE day >= :month_start AND day <= :today
            """
        )
        with self.engine.connect() as connection:
            row = connection.execute(
                query, {"today": today, "month_start": today.replace(day=1)}
            ).one()
        return float(row[0]), float(row[1])

    def record(self, day: dt.date, cost_usd: float) -> None:
        query = text(
            """
            INSERT INTO api_usage (day, requests, cost_usd) VALUES (:day, 1, :cost)
            ON CONFLICT (day) DO UPDATE SET
                requests = api_usage.requests + 1,
                cost_usd = api_usage.cost_usd + EXCLUDED.cost_usd
            """
        )
        with self.engine.begin() as connection:
            connection.execute(query, {"day": day, "cost": cost_usd})


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


@dataclass
class CostGuard:
    """Kostendeckel pro Monat, verteilt auf die Tage."""

    store: UsageStore
    monthly_budget: float
    now: Callable[[], dt.datetime] = utc_now

    def check(self) -> None:
        current = self.now()
        before, today = self.store.spent(current.date())
        allowance = daily_allowance(self.monthly_budget, before, current.date())
        if today >= allowance:
            raise LimitExceeded(
                "budget",
                "Das Tagesbudget der Demo ist aufgebraucht. Ab Mitternacht (UTC) gibt es neue "
                "Fragen; die Suche in den Quellen ist auf parlament.ch jederzeit möglich.",
                seconds_until_tomorrow(current),
            )

    def record(self, cost_usd: float | None) -> None:
        self.store.record(self.now().date(), cost_usd or 0.0)


class RateLimiter:
    """Höchstens `limit` Anfragen pro Schlüssel (IP) in einem gleitenden Fenster."""

    def __init__(
        self,
        limit: int,
        window_seconds: float = SECONDS_PER_HOUR,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.limit = limit
        self.window = window_seconds
        self.clock = clock
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def hit(self, key: str) -> None:
        """Zählt die Anfrage oder wirft `LimitExceeded`, wenn das Limit erreicht ist."""
        now = self.clock()
        with self._lock:
            self._forget_older_than(now - self.window)
            hits = self._hits.setdefault(key, deque())
            if len(hits) >= self.limit:
                retry_after = max(1, math.ceil(hits[0] + self.window - now))
                raise LimitExceeded(
                    "rate",
                    f"Zu viele Fragen: Die Demo erlaubt {self.limit} Fragen pro Stunde. "
                    f"Bitte in {math.ceil(retry_after / 60)} Minuten wieder versuchen.",
                    retry_after,
                )
            hits.append(now)

    def _forget_older_than(self, cutoff: float) -> None:
        for key in list(self._hits):
            hits = self._hits[key]
            while hits and hits[0] <= cutoff:
                hits.popleft()
            if not hits:
                del self._hits[key]


@dataclass
class DemoLimits:
    """Beide Grenzen zusammen; `None` heisst ausgeschaltet."""

    cost: CostGuard | None = None
    rate: RateLimiter | None = None
    trust_proxy_headers: bool = False

    @property
    def active(self) -> bool:
        return self.cost is not None or self.rate is not None

    def admit(self, client_ip: str) -> None:
        """Vor dem Aufruf der Pipeline: wirft `LimitExceeded`, wenn eine Grenze erreicht ist."""
        if self.rate is not None:
            self.rate.hit(client_ip)
        if self.cost is not None:
            self.cost.check()

    def record(self, cost_usd: float | None) -> None:
        if self.cost is not None:
            self.cost.record(cost_usd)


def client_ip(forwarded_for: str | None, peer: str | None, trust_proxy_headers: bool) -> str:
    """IP der Besucherin: hinter dem eigenen Proxy der erste Eintrag von X-Forwarded-For.

    Caddy überschreibt den Header mit der echten Adresse (deploy/Caddyfile), nginx hängt seine
    eigene an. Ohne `trust_proxy_headers` zählt nur die direkte Verbindung, damit niemand das
    Limit mit einem selbst gesetzten Header umgehen kann.
    """
    if trust_proxy_headers and forwarded_for:
        first = forwarded_for.split(",")[0].strip()
        if first:
            return first
    return peer or "unbekannt"
