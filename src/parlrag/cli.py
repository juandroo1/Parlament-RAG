"""Kommandozeile `parlrag` (Typer)."""

import datetime as dt
import logging
from typing import Annotated, cast

import typer
from sqlalchemy.orm import sessionmaker

from parlrag.config import Settings
from parlrag.db.session import get_engine
from parlrag.ingest.mapping import LANGUAGES, Language
from parlrag.ingest.odata import ODataClient
from parlrag.ingest.pipeline import IngestStats, run_ingest
from parlrag.ingest.source import ODataSource

DEFAULT_SINCE = dt.datetime(2023, 12, 1)  # Beginn der 52. Legislatur (spec.md, Abschnitt 5)

app = typer.Typer(help="Frag das Parlament", no_args_is_help=True, add_completion=False)


@app.callback()
def main(
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Ausführliche Logs.")] = False,
) -> None:
    """Fragen zu Debatten und Geschäften des Schweizer Bundesparlaments."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    # Jede Request-URL einzeln loggen nur mit --verbose; Warnungen (Retries) bleiben sichtbar.
    for noisy in ("httpx2", "httpcore2"):
        logging.getLogger(noisy).setLevel(logging.DEBUG if verbose else logging.WARNING)


def parse_languages(value: str) -> frozenset[Language]:
    codes = {part.strip().lower() for part in value.split(",") if part.strip()}
    allowed = set(LANGUAGES.values())
    if not codes or not codes <= allowed:
        raise typer.BadParameter(f"erlaubt sind {', '.join(sorted(allowed))} (kommagetrennt)")
    return frozenset(cast(set[Language], codes))


def execute_ingest(
    since: dt.date, until: dt.date, languages: frozenset[Language], refresh: bool
) -> IngestStats:
    """Verdrahtet Konfiguration, OData-Client und Datenbank (in Tests ersetzbar)."""
    settings = Settings()
    with ODataClient.from_settings(settings) as client:
        stats = run_ingest(
            ODataSource(client, refresh=refresh),
            sessionmaker(get_engine()),
            since,
            until,
            languages,
        )
        typer.echo(f"OData: {client.requests_made} Requests, {client.cache_hits} aus dem Cache")
    return stats


@app.command()
def ingest(
    since: Annotated[
        dt.datetime,
        typer.Option(formats=["%Y-%m-%d"], help="Erstes Sitzungsdatum (inklusive)."),
    ] = DEFAULT_SINCE,
    until: Annotated[
        dt.datetime | None,
        typer.Option(
            formats=["%Y-%m-%d"], help="Letztes Sitzungsdatum (inklusive); Standard: heute."
        ),
    ] = None,
    lang: Annotated[
        str, typer.Option("--lang", help="Sprachen der Dokumente, kommagetrennt.")
    ] = "de,fr",
    refresh: Annotated[
        bool, typer.Option(help="Rohdaten-Cache umgehen (z. B. für die laufende Session).")
    ] = False,
) -> None:
    """Lädt Voten und Geschäfte idempotent in die Datenbank."""
    start = since.date()
    end = until.date() if until else dt.date.today()
    if start > end:
        raise typer.BadParameter("--since liegt nach --until", param_hint="--since")
    languages = parse_languages(lang)

    stats = execute_ingest(start, end, languages, refresh)

    stored = stats.stored
    typer.echo(
        f"Zeitraum {start} bis {end}, Sprachen {','.join(sorted(languages))}: "
        f"{stats.sessions} Sessions, {stats.meetings} Sitzungen, {stats.subjects} Traktanden"
    )
    typer.echo(
        f"Voten: {stats.transcripts} geladen, {stats.skipped_transcripts} übersprungen; "
        f"Geschäfte: {stats.businesses}"
    )
    typer.echo(
        f"Dokumente: {stats.documents} (neu {stored.inserted}, geändert {stored.updated}, "
        f"unverändert {stored.unchanged})"
    )
