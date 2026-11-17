"""Grenzen der öffentlichen Demo (Task 6.3a): Kostendeckel pro Monat und Rate-Limit pro IP."""

import datetime as dt
import logging
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text
from sqlalchemy.exc import OperationalError

from parlrag.api.ask import limits_provider, pipeline_provider
from parlrag.api.limits import (
    CostGuard,
    DemoLimits,
    LimitExceeded,
    PostgresUsageStore,
    RateLimiter,
    client_ip,
    daily_allowance,
    seconds_until_tomorrow,
)
from parlrag.api.main import app
from parlrag.config import Settings
from test_api_ask import QUESTION, FakePipeline, _answer

# --- Tagesbudget ---------------------------------------------------------------------------


def test_daily_allowance_spreads_the_rest_over_the_remaining_days() -> None:
    november = dt.date(2026, 11, 1)  # 30 Tage
    assert daily_allowance(5.0, 0.0, november) == pytest.approx(5.0 / 30)
    # Ruhige Tage: der Rest verteilt sich auf weniger Tage, das Tagesbudget steigt.
    assert daily_allowance(5.0, 1.0, dt.date(2026, 11, 21)) == pytest.approx(0.4)
    assert daily_allowance(5.0, 4.0, dt.date(2026, 11, 30)) == pytest.approx(1.0)
    assert daily_allowance(5.0, 5.5, dt.date(2026, 11, 30)) == 0.0  # nie negativ
    assert daily_allowance(5.0, 0.0, dt.date(2027, 2, 28)) == pytest.approx(5.0)


def test_seconds_until_tomorrow_in_utc() -> None:
    now = dt.datetime(2026, 11, 17, 23, 0, tzinfo=dt.UTC)
    assert seconds_until_tomorrow(now) == 3600
    assert seconds_until_tomorrow(dt.datetime(2026, 11, 17, 23, 59, 59, 999, tzinfo=dt.UTC)) == 1


class FakeStore:
    def __init__(self, before: float = 0.0, today: float = 0.0) -> None:
        self.before = before
        self.today = today
        self.recorded: list[tuple[dt.date, float]] = []

    def spent(self, today: dt.date) -> tuple[float, float]:
        return self.before, self.today

    def record(self, day: dt.date, cost_usd: float) -> None:
        self.recorded.append((day, cost_usd))
        self.today += cost_usd


NOW = dt.datetime(2026, 11, 1, 12, 0, tzinfo=dt.UTC)


def _guard(store: FakeStore, budget: float = 3.0) -> CostGuard:
    return CostGuard(store, budget, now=lambda: NOW)  # Tagesbudget 3.0 / 30 = 0.10


def test_cost_guard_admits_until_the_daily_budget_is_used() -> None:
    store = FakeStore(today=0.099)
    guard = _guard(store)
    guard.check()
    guard.record(0.002)
    assert store.recorded == [(dt.date(2026, 11, 1), 0.002)]

    with pytest.raises(LimitExceeded) as raised:
        guard.check()
    assert raised.value.kind == "budget"
    assert raised.value.retry_after == 12 * 3600
    assert "Tagesbudget" in raised.value.message


def test_cost_guard_records_requests_without_llm_as_free() -> None:
    store = FakeStore()
    _guard(store).record(None)
    assert store.recorded == [(dt.date(2026, 11, 1), 0.0)]


# --- Rate-Limit ----------------------------------------------------------------------------


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_rate_limiter_counts_per_ip_in_a_sliding_hour() -> None:
    clock = Clock()
    limiter = RateLimiter(2, clock=clock)
    limiter.hit("1.1.1.1")
    clock.now += 600
    limiter.hit("1.1.1.1")
    limiter.hit("2.2.2.2")  # andere IP, eigenes Kontingent

    with pytest.raises(LimitExceeded) as raised:
        limiter.hit("1.1.1.1")
    assert raised.value.kind == "rate"
    assert raised.value.retry_after == 3000  # bis die erste Anfrage aus dem Fenster fällt
    assert "2 Fragen pro Stunde" in raised.value.message and "50 Minuten" in raised.value.message

    clock.now += 3000
    limiter.hit("1.1.1.1")  # die erste Anfrage ist aus dem Fenster gefallen


def test_rate_limiter_forgets_idle_ips() -> None:
    clock = Clock()
    limiter = RateLimiter(1, clock=clock)
    limiter.hit("1.1.1.1")
    clock.now += 3601
    limiter.hit("2.2.2.2")
    assert list(limiter._hits) == ["2.2.2.2"]  # keine IP bleibt länger als nötig gespeichert


def test_client_ip_trusts_forwarded_for_only_behind_the_own_proxy() -> None:
    assert client_ip("203.0.113.7, 172.18.0.5", "172.18.0.4", True) == "203.0.113.7"
    assert client_ip("203.0.113.7", "172.18.0.4", False) == "172.18.0.4"
    assert client_ip(None, "172.18.0.4", True) == "172.18.0.4"
    assert client_ip(" ", None, True) == "unbekannt"


def test_limits_are_off_by_default() -> None:
    settings = Settings(_env_file=None, postgres_password="x")  # type: ignore[arg-type]
    assert settings.demo_monthly_budget_usd == 0 and settings.rate_limit_per_hour == 0
    assert settings.trust_proxy_headers is False
    assert not DemoLimits().active


# --- POST /ask mit Grenzen -----------------------------------------------------------------


@pytest.fixture
def demo() -> Iterator[dict[str, Any]]:
    clock = Clock()
    store = FakeStore()
    state: dict[str, Any] = {
        "pipeline": FakePipeline(_answer()),
        "store": store,
        "limits": DemoLimits(
            cost=CostGuard(store, 3.0, now=lambda: NOW),
            rate=RateLimiter(2, clock=clock),
            trust_proxy_headers=True,
        ),
    }
    app.dependency_overrides[pipeline_provider] = lambda: lambda: state["pipeline"]
    app.dependency_overrides[limits_provider] = lambda: state["limits"]
    state["client"] = TestClient(app)
    yield state
    app.dependency_overrides.clear()


def _ask(demo: dict[str, Any], ip: str = "203.0.113.7") -> Any:
    return demo["client"].post(
        "/ask", json={"question": QUESTION}, headers={"X-Forwarded-For": f"{ip}, 172.18.0.5"}
    )


def test_ask_records_cost_and_enforces_rate_limit(
    demo: dict[str, Any], caplog: pytest.LogCaptureFixture
) -> None:
    assert _ask(demo).status_code == 200
    assert _ask(demo).status_code == 200
    assert demo["store"].recorded == [(dt.date(2026, 11, 1), 0.0161)] * 2

    with caplog.at_level(logging.INFO, logger="parlrag.api"):
        third = _ask(demo)
    assert third.status_code == 429
    assert int(third.headers["Retry-After"]) == 3600
    assert "X-Request-ID" in third.headers
    assert "2 Fragen pro Stunde" in third.json()["detail"]
    assert len(demo["pipeline"].calls) == 2  # abgelehnt vor der Pipeline
    assert "status=429" in caplog.text and "limit=rate" in caplog.text
    assert "203.0.113.7" not in caplog.text  # IP nicht im Log

    assert _ask(demo, ip="198.51.100.9").status_code == 200  # andere Besucherin


def test_ask_stops_when_the_daily_budget_is_used(demo: dict[str, Any]) -> None:
    demo["store"].today = 0.10
    response = _ask(demo)
    assert response.status_code == 429
    assert "Tagesbudget" in response.json()["detail"]
    assert int(response.headers["Retry-After"]) == 12 * 3600
    assert demo["pipeline"].calls == []


def test_ask_rejects_when_usage_cannot_be_read(demo: dict[str, Any]) -> None:
    class BrokenStore(FakeStore):
        def spent(self, today: dt.date) -> tuple[float, float]:
            raise OperationalError("SELECT", {}, Exception("db down"))

    demo["limits"].cost = CostGuard(BrokenStore(), 3.0, now=lambda: NOW)
    response = _ask(demo)
    assert response.status_code == 503
    assert demo["pipeline"].calls == []


# --- Speicher in Postgres ------------------------------------------------------------------


@pytest.fixture
def usage_db(migrated_engine: Engine) -> Iterator[Engine]:
    with migrated_engine.begin() as connection:
        connection.execute(text("TRUNCATE api_usage"))
    yield migrated_engine
    with migrated_engine.begin() as connection:
        connection.execute(text("TRUNCATE api_usage"))


@pytest.mark.db
def test_postgres_usage_store_sums_per_month(usage_db: Engine) -> None:
    store = PostgresUsageStore(usage_db)
    store.record(dt.date(2026, 10, 31), 1.0)  # Vormonat zählt nicht
    store.record(dt.date(2026, 11, 2), 0.25)
    store.record(dt.date(2026, 11, 3), 0.002)
    store.record(dt.date(2026, 11, 3), 0.0)

    assert store.spent(dt.date(2026, 11, 3)) == pytest.approx((0.25, 0.002))
    assert store.spent(dt.date(2026, 11, 1)) == (0.0, 0.0)
    with usage_db.connect() as connection:
        query = text("SELECT requests FROM api_usage WHERE day = '2026-11-03'")
        requests = connection.scalar(query)
    assert requests == 2
