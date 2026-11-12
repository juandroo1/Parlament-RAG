"""OData-Client für ws.parlament.ch (plan.md, Abschnitt 3).

Schont den Dienst gemäss CLAUDE.md: Mindestabstand zwischen Requests, Retry mit
exponentiellem Backoff und ein Rohdaten-Cache, der jede erfolgreiche Antwort
byte-genau ablegt. Der Server blättert selbst (`__next` mit `$skiptoken`, höchstens
1000 Zeilen pro Antwort); der Client folgt diesen Links.
"""

import hashlib
import json
import logging
import os
import random
import re
import tempfile
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from types import TracebackType
from typing import Any, Self
from urllib.parse import quote, urlsplit

import httpx2
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from parlrag import __version__
from parlrag.config import Settings

logger = logging.getLogger(__name__)

USER_AGENT = f"parlrag/{__version__} (+https://github.com/juandroo1/Parlament-RAG)"
RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})
MAX_BACKOFF_SECONDS = 60.0
MAX_RETRY_AFTER_SECONDS = 300.0
# Zeichen, die in OData-Ausdrücken unkodiert bleiben dürfen (z. B. Language eq 'DE').
SAFE_QUERY_CHARS = "'(),:"

Row = dict[str, Any]


class ODataError(RuntimeError):
    """Der OData-Dienst lieferte keine verwertbare Antwort."""


class _Collection(BaseModel):
    model_config = ConfigDict(extra="ignore")

    results: list[Row]
    next_url: str | None = Field(default=None, alias="__next")
    count: int | None = Field(default=None, alias="__count")


class _Envelope(BaseModel):
    """Beide Formen von OData-v3-JSON: `{"d": [...]}` und `{"d": {"results": [...]}}`."""

    d: list[Row] | _Collection


@dataclass(frozen=True)
class ODataPage:
    rows: list[Row]
    next_url: str | None
    count: int | None


def parse_page(body: bytes) -> ODataPage:
    try:
        envelope = _Envelope.model_validate_json(body)
    except ValidationError as exc:
        raise ODataError(
            f"Unerwartete OData-Antwort ({exc.error_count()} Validierungsfehler)"
        ) from exc
    if isinstance(envelope.d, list):
        return ODataPage(rows=envelope.d, next_url=None, count=None)
    return ODataPage(rows=envelope.d.results, next_url=envelope.d.next_url, count=envelope.d.count)


def build_url(
    base_url: str,
    entity: str,
    *,
    filter: str | None = None,
    select: list[str] | None = None,
    orderby: str | None = None,
    expand: list[str] | None = None,
    top: int | None = None,
    inlinecount: bool = False,
) -> str:
    """Abfrage-URL mit kodierten Parametern; `$format=json` steht immer dabei."""
    params: list[tuple[str, str]] = []
    if filter:
        params.append(("$filter", filter))
    if select:
        params.append(("$select", ",".join(select)))
    if orderby:
        params.append(("$orderby", orderby))
    if expand:
        params.append(("$expand", ",".join(expand)))
    if top is not None:
        params.append(("$top", str(top)))
    if inlinecount:
        params.append(("$inlinecount", "allpages"))
    params.append(("$format", "json"))
    query = "&".join(f"{key}={quote(value, safe=SAFE_QUERY_CHARS)}" for key, value in params)
    return f"{base_url.rstrip('/')}/{entity}?{query}"


def ensure_json_format(url: str) -> str:
    """`__next`-Links des Servers enthalten kein `$format=json`; ohne käme XML zurück."""
    if re.search(r"[?&]\$format=", url):
        return url
    return f"{url}{'&' if '?' in url else '?'}$format=json"


class RawCache:
    """Ablage der Rohantworten unter `<root>/odata/<Entität>/<sha256(URL)>.json`.

    Daneben liegt `<…>.meta.json` mit URL und Abrufzeit. Sie wird zuletzt geschrieben
    und gilt als Zeichen, dass der Eintrag vollständig ist.
    """

    def __init__(self, root: Path) -> None:
        self.root = root / "odata"

    def paths(self, url: str) -> tuple[Path, Path]:
        key = hashlib.sha256(url.encode("utf-8")).hexdigest()
        entity = urlsplit(url).path.rstrip("/").rsplit("/", 1)[-1]
        folder = self.root / (entity if re.fullmatch(r"\w+", entity) else "_other")
        return folder / f"{key}.json", folder / f"{key}.meta.json"

    def get(self, url: str) -> bytes | None:
        body_path, meta_path = self.paths(url)
        if not meta_path.exists() or not body_path.exists():
            return None
        return body_path.read_bytes()

    def put(self, url: str, body: bytes, fetched_at: datetime) -> None:
        body_path, meta_path = self.paths(url)
        body_path.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write(body_path, body)
        meta = {"url": url, "fetched_at": fetched_at.isoformat(), "bytes": len(body)}
        _atomic_write(meta_path, json.dumps(meta, ensure_ascii=False, indent=2).encode("utf-8"))


def _atomic_write(path: Path, data: bytes) -> None:
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.replace(tmp_name, path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise


def _parse_retry_after(value: str | None) -> float | None:
    if not value:
        return None
    try:
        seconds = float(value)
    except ValueError:
        try:
            seconds = (parsedate_to_datetime(value) - datetime.now(UTC)).total_seconds()
        except (TypeError, ValueError):
            return None
    return min(max(seconds, 0.0), MAX_RETRY_AFTER_SECONDS)


class ODataClient:
    """Gedrosselter, wiederholender und cachender Zugriff auf den OData-Dienst."""

    def __init__(
        self,
        *,
        base_url: str,
        cache: RawCache | None,
        min_interval_seconds: float = 1.0,
        max_retries: int = 5,
        timeout_seconds: float = 60.0,
        transport: httpx2.BaseTransport | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        rng: random.Random | None = None,
    ) -> None:
        self.base_url = base_url
        self._cache = cache
        self._min_interval = min_interval_seconds
        self._max_retries = max_retries
        self._clock = clock
        self._sleep = sleep
        self._rng = rng or random.Random()
        self._last_request_at: float | None = None
        self.requests_made = 0
        self.cache_hits = 0
        self._http = httpx2.Client(
            timeout=timeout_seconds,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            transport=transport,
            follow_redirects=True,
        )

    @classmethod
    def from_settings(cls, settings: Settings) -> Self:
        return cls(
            base_url=settings.odata_base_url,
            cache=RawCache(settings.raw_cache_dir),
            min_interval_seconds=settings.odata_min_interval_seconds,
            max_retries=settings.odata_max_retries,
            timeout_seconds=settings.odata_timeout_seconds,
        )

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        self._http.close()

    def iter_rows(
        self,
        entity: str,
        *,
        filter: str | None = None,
        select: list[str] | None = None,
        orderby: str | None = None,
        expand: list[str] | None = None,
        refresh: bool = False,
    ) -> Iterator[Row]:
        """Alle Zeilen einer Abfrage; folgt den `__next`-Links des Servers."""
        url: str | None = build_url(
            self.base_url, entity, filter=filter, select=select, orderby=orderby, expand=expand
        )
        while url is not None:
            page = self.fetch_page(url, refresh=refresh)
            yield from page.rows
            url = ensure_json_format(page.next_url) if page.next_url else None

    def count(self, entity: str, *, filter: str | None = None, refresh: bool = False) -> int:
        url = build_url(self.base_url, entity, filter=filter, top=1, inlinecount=True)
        page = self.fetch_page(url, refresh=refresh)
        if page.count is None:
            raise ODataError(f"Antwort ohne __count: {url}")
        return page.count

    def fetch_page(self, url: str, *, refresh: bool = False) -> ODataPage:
        return parse_page(self.get(url, refresh=refresh))

    def get(self, url: str, *, refresh: bool = False) -> bytes:
        """Rohantwort aus dem Cache oder vom Dienst; erfolgreiche Antworten werden gecacht."""
        if self._cache is not None and not refresh:
            cached = self._cache.get(url)
            if cached is not None:
                self.cache_hits += 1
                return cached
        body = self._request_with_retry(url)
        parse_page(body)  # nur gültige Antworten in den Cache
        if self._cache is not None:
            self._cache.put(url, body, datetime.now(UTC))
        return body

    def _request_with_retry(self, url: str) -> bytes:
        attempt = 0
        while True:
            self._throttle()
            retry_after: float | None = None
            try:
                response = self._http.get(url)
            except httpx2.TransportError as exc:  # Timeouts, Verbindungsfehler
                problem = type(exc).__name__
            else:
                if response.status_code == 200:
                    return response.content
                if response.status_code not in RETRYABLE_STATUS:
                    raise ODataError(f"HTTP {response.status_code} für {url}")
                problem = f"HTTP {response.status_code}"
                retry_after = _parse_retry_after(response.headers.get("Retry-After"))

            if attempt >= self._max_retries:
                raise ODataError(f"Aufgegeben nach {attempt + 1} Versuchen ({problem}): {url}")
            delay = retry_after if retry_after is not None else self._backoff(attempt)
            logger.warning(
                "OData-Request fehlgeschlagen (%s), neuer Versuch in %.1f s: %s",
                problem,
                delay,
                url,
            )
            self._sleep(delay)
            attempt += 1

    def _backoff(self, attempt: int) -> float:
        base: float = min(MAX_BACKOFF_SECONDS, 2.0**attempt)
        return base * (1.0 + 0.25 * self._rng.random())

    def _throttle(self) -> None:
        now = self._clock()
        if self._last_request_at is not None:
            wait = self._min_interval - (now - self._last_request_at)
            if wait > 0:
                self._sleep(wait)
                now = self._clock()
        self._last_request_at = now
        self.requests_made += 1
