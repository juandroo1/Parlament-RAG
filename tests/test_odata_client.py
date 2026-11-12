"""Tests für den OData-Client, ohne Live-API (MockTransport und echte Fixtures aus Task 0.2)."""

import json
import random
from collections.abc import Callable
from pathlib import Path
from urllib.parse import unquote

import httpx2
import pytest

from parlrag.ingest.odata import (
    USER_AGENT,
    ODataClient,
    ODataError,
    RawCache,
    build_url,
    ensure_json_format,
    parse_page,
)

FIXTURES = Path(__file__).parent / "fixtures" / "odata"
BASE = "https://ws.parlament.ch/odata.svc/"

Handler = Callable[[httpx2.Request], httpx2.Response]


class FakeClock:
    """Uhr und sleep in einem: sleep lässt die Zeit fortschreiten und merkt sich die Pausen."""

    def __init__(self) -> None:
        self.now = 1000.0
        self.sleeps: list[float] = []

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def make_client(
    handler: Handler,
    *,
    cache_dir: Path | None = None,
    clock: FakeClock | None = None,
    min_interval: float = 1.0,
    max_retries: int = 3,
) -> tuple[ODataClient, FakeClock, list[httpx2.Request]]:
    seen: list[httpx2.Request] = []

    def recording(request: httpx2.Request) -> httpx2.Response:
        seen.append(request)
        return handler(request)

    fake = clock or FakeClock()
    client = ODataClient(
        base_url=BASE,
        cache=RawCache(cache_dir) if cache_dir else None,
        min_interval_seconds=min_interval,
        max_retries=max_retries,
        transport=httpx2.MockTransport(recording),
        clock=fake.time,
        sleep=fake.sleep,
        rng=random.Random(0),
    )
    return client, fake, seen


def page(rows: list[dict[str, object]], next_url: str | None = None) -> bytes:
    payload: dict[str, object] = {"results": rows}
    if next_url:
        payload["__next"] = next_url
    return json.dumps({"d": payload}).encode()


# --- Antworten und URLs -------------------------------------------------------------


def test_parse_page_accepts_plain_list_shape() -> None:
    result = parse_page((FIXTURES / "session_legislature52_de.json").read_bytes())
    assert len(result.rows) == 15
    assert result.next_url is None


def test_parse_page_accepts_results_shape() -> None:
    result = parse_page((FIXTURES / "transcript_subject82315_de.json").read_bytes())
    assert len(result.rows) == 11
    assert result.rows[0]["ID"] == "418868"


def test_parse_page_reads_count_and_next() -> None:
    body = b'{"d": {"results": [], "__count": "41245", "__next": "https://x/T?$skiptoken=1L"}}'
    result = parse_page(body)
    assert result.count == 41245
    assert result.next_url == "https://x/T?$skiptoken=1L"


@pytest.mark.parametrize("body", [b"not json", b'{"value": []}', b'{"d": "text"}'])
def test_parse_page_rejects_unexpected_bodies(body: bytes) -> None:
    with pytest.raises(ODataError):
        parse_page(body)


def test_build_url_encodes_parameters() -> None:
    url = build_url(
        BASE,
        "Transcript",
        filter="IdSubject eq 82315 and Language eq 'DE'",
        select=["ID", "Text"],
        orderby="SortOrder",
        top=10,
        inlinecount=True,
    )
    assert url == (
        "https://ws.parlament.ch/odata.svc/Transcript?"
        "$filter=IdSubject%20eq%2082315%20and%20Language%20eq%20'DE'"
        "&$select=ID,Text&$orderby=SortOrder&$top=10&$inlinecount=allpages&$format=json"
    )


def test_ensure_json_format_adds_format_to_next_links() -> None:
    next_url = "https://ws.parlament.ch/OData.svc/Transcript?$filter=x&$skiptoken=419690L,'DE'"
    assert ensure_json_format(next_url) == next_url + "&$format=json"
    assert ensure_json_format(next_url + "&$format=json") == next_url + "&$format=json"


# --- Paginierung und Drosselung ------------------------------------------------------


def test_iter_rows_follows_next_links_in_order() -> None:
    next_1 = "https://ws.parlament.ch/OData.svc/Transcript?$filter=x&$skiptoken=2L,'DE'"
    next_2 = "https://ws.parlament.ch/OData.svc/Transcript?$filter=x&$skiptoken=4L,'DE'"
    pages = [
        page([{"ID": 1}, {"ID": 2}], next_1),
        page([{"ID": 3}, {"ID": 4}], next_2),
        page([{"ID": 5}]),
    ]
    client, _, seen = make_client(
        lambda request: httpx2.Response(200, content=pages[len(seen) - 1])
    )

    rows = list(client.iter_rows("Transcript", filter="x"))

    assert [row["ID"] for row in rows] == [1, 2, 3, 4, 5]
    assert len(seen) == 3
    assert "$skiptoken=2L,'DE'" in unquote(str(seen[1].url))
    assert "$format=json" in str(seen[1].url)
    assert "$skiptoken=4L,'DE'" in unquote(str(seen[2].url))


def test_requests_are_throttled_to_min_interval() -> None:
    client, clock, _ = make_client(
        lambda request: httpx2.Response(200, content=page([])), min_interval=1.0
    )

    for index in range(3):
        client.get(f"{BASE}Session?$top={index}&$format=json")

    assert clock.sleeps == [1.0, 1.0]


def test_sends_identifying_user_agent_without_personal_data() -> None:
    client, _, seen = make_client(lambda request: httpx2.Response(200, content=page([])))
    client.get(f"{BASE}Session?$format=json")
    assert seen[0].headers["User-Agent"] == USER_AGENT
    assert "@" not in USER_AGENT


def test_count_uses_inlinecount() -> None:
    body = b'{"d": {"results": [{"ID": "1"}], "__count": "36382"}}'
    client, _, seen = make_client(lambda request: httpx2.Response(200, content=body))

    assert client.count("Transcript", filter="Type eq 1") == 36382
    assert "$inlinecount=allpages" in str(seen[0].url)
    assert "$top=1" in str(seen[0].url)


# --- Retry -------------------------------------------------------------------------


def test_retries_server_errors_with_backoff_then_succeeds() -> None:
    responses = [httpx2.Response(503), httpx2.Response(502), httpx2.Response(200, content=page([]))]
    client, clock, seen = make_client(lambda request: responses[len(seen) - 1], min_interval=0)

    client.get(f"{BASE}Session?$format=json")

    assert len(seen) == 3
    # exponentiell: ca. 1 s, dann ca. 2 s (plus bis zu 25 % Zufallsanteil)
    assert 1.0 <= clock.sleeps[0] <= 1.25
    assert 2.0 <= clock.sleeps[1] <= 2.5


def test_honours_retry_after_on_429() -> None:
    responses = [
        httpx2.Response(429, headers={"Retry-After": "7"}),
        httpx2.Response(200, content=page([])),
    ]
    client, clock, seen = make_client(lambda request: responses[len(seen) - 1], min_interval=0)

    client.get(f"{BASE}Session?$format=json")

    assert clock.sleeps == [7.0]


def test_retries_timeouts() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        if len(seen) == 1:
            raise httpx2.ReadTimeout("zu langsam", request=request)
        return httpx2.Response(200, content=page([]))

    client, _, seen = make_client(handler, min_interval=0)
    client.get(f"{BASE}Session?$format=json")
    assert len(seen) == 2


def test_gives_up_after_max_retries() -> None:
    client, _, seen = make_client(lambda request: httpx2.Response(503), max_retries=2)

    with pytest.raises(ODataError, match="3 Versuchen"):
        client.get(f"{BASE}Session?$format=json")
    assert len(seen) == 3


def test_does_not_retry_client_errors() -> None:
    client, clock, seen = make_client(lambda request: httpx2.Response(404))

    with pytest.raises(ODataError, match="HTTP 404"):
        client.get(f"{BASE}Unknown?$format=json")
    assert len(seen) == 1
    assert clock.sleeps == []


# --- Cache -------------------------------------------------------------------------


def test_cache_serves_second_request_without_network(tmp_path: Path) -> None:
    body = (FIXTURES / "transcript_subject82315_de.json").read_bytes()
    client, _, seen = make_client(
        lambda request: httpx2.Response(200, content=body), cache_dir=tmp_path
    )
    url = build_url(BASE, "Transcript", filter="IdSubject eq 82315 and Language eq 'DE'")

    first = client.get(url)
    second = client.get(url)

    assert first == second == body
    assert len(seen) == 1
    assert client.cache_hits == 1


def test_cache_stores_raw_bytes_and_metadata(tmp_path: Path) -> None:
    body = (FIXTURES / "session_legislature52_de.json").read_bytes()
    client, _, _ = make_client(
        lambda request: httpx2.Response(200, content=body), cache_dir=tmp_path
    )
    url = build_url(BASE, "Session", filter="LegislativePeriodNumber eq 52")

    client.get(url)

    body_path, meta_path = RawCache(tmp_path).paths(url)
    assert body_path.parent == tmp_path / "odata" / "Session"
    assert body_path.read_bytes() == body
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta["url"] == url
    assert meta["bytes"] == len(body)
    assert not list(body_path.parent.glob("*.tmp"))


def test_refresh_bypasses_cache(tmp_path: Path) -> None:
    client, _, seen = make_client(
        lambda request: httpx2.Response(200, content=page([{"ID": len(seen)}])), cache_dir=tmp_path
    )
    url = f"{BASE}Session?$format=json"

    client.get(url)
    refreshed = client.get(url, refresh=True)

    assert len(seen) == 2
    assert parse_page(refreshed).rows == [{"ID": 2}]
    assert parse_page(client.get(url)).rows == [{"ID": 2}]  # Cache wurde aktualisiert


def test_errors_and_invalid_bodies_are_not_cached(tmp_path: Path) -> None:
    client, _, _ = make_client(
        lambda request: httpx2.Response(200, content=b'{"unexpected": true}'),
        cache_dir=tmp_path,
        max_retries=0,
    )
    url = f"{BASE}Session?$format=json"

    with pytest.raises(ODataError):
        client.get(url)
    assert RawCache(tmp_path).get(url) is None


def test_incomplete_cache_entry_is_ignored(tmp_path: Path) -> None:
    cache = RawCache(tmp_path)
    url = f"{BASE}Session?$format=json"
    body_path, _ = cache.paths(url)
    body_path.parent.mkdir(parents=True)
    body_path.write_bytes(b"half written")  # Metadatei fehlt: Eintrag gilt als unvollständig

    assert cache.get(url) is None


def test_different_urls_use_different_cache_files(tmp_path: Path) -> None:
    cache = RawCache(tmp_path)
    first, _ = cache.paths(f"{BASE}Transcript?$skiptoken=1L&$format=json")
    second, _ = cache.paths(f"{BASE}Transcript?$skiptoken=2L&$format=json")
    assert first != second
    assert first.parent == second.parent == tmp_path / "odata" / "Transcript"
