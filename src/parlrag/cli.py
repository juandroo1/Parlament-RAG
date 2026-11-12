"""Kommandozeile `parlrag` (Typer)."""

import datetime as dt
import logging
from typing import Annotated, cast

import typer
from rich.console import Console
from rich.table import Table
from sqlalchemy.orm import sessionmaker

from parlrag.config import Settings
from parlrag.db.session import get_engine
from parlrag.embeddings import get_embedder
from parlrag.index.indexer import IndexConfig, IndexStats, index_documents, log_progress
from parlrag.ingest.mapping import LANGUAGES, Language
from parlrag.ingest.odata import ODataClient
from parlrag.ingest.pipeline import IngestStats, run_ingest
from parlrag.ingest.source import ODataSource
from parlrag.stats import CorpusStats, compute_stats

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


def load_stats(session_id: int | None) -> CorpusStats:
    """Liest die Statistik aus der Datenbank (in Tests ersetzbar)."""
    return compute_stats(get_engine(), session_id)


def _number(value: float) -> str:
    return f"{value:,.0f}".replace(",", "'")


@app.command()
def stats(
    session_id: Annotated[
        int | None, typer.Option(help="Nur diese Session (Voten und dort debattierte Geschäfte).")
    ] = None,
) -> None:
    """Statistik über die geladenen Dokumente: Umfang, Zeichen, Verteilung, Qualität."""
    result = load_stats(session_id)
    console = Console()
    scope = f"Session {session_id}" if session_id is not None else "gesamter Bestand"
    console.print(f"[bold]Dokumente ({scope}): {_number(result.total_documents)}[/bold]")
    if result.first_date:
        console.print(f"Voten vom {result.first_date} bis {result.last_date}")

    volume = Table("Art", "Sprache", "Dokumente", title="Umfang")
    for (source_type, language), count in sorted(result.by_type_language.items()):
        volume.add_row(source_type, language, _number(count))
    console.print(volume)

    lengths = Table(
        "Art", "Zeichen", "≈ Tokens", "Mittel", "Median", "P90", "Max", title="Textlänge (Zeichen)"
    )
    for source_type, length in sorted(result.lengths.items()):
        lengths.add_row(
            source_type,
            _number(length.total_chars),
            _number(length.estimated_tokens),
            _number(length.mean_chars),
            _number(length.median_chars),
            _number(length.p90_chars),
            _number(length.max_chars),
        )
    console.print(lengths)
    console.print("≈ Tokens: grobe Schätzung (Zeichen / 4); genaue Zahlen ab Task 2.1.")

    distribution = Table("Rat bzw. Fraktion", "Voten", title="Verteilung der Voten")
    for council, count in result.transcripts_by_council.items():
        distribution.add_row(f"Rat {council}", _number(count))
    for group, count in result.transcripts_by_parl_group.items():
        distribution.add_row(group, _number(count))
    console.print(distribution)

    quality = Table("Prüfung", "Dokumente", title="Qualität")
    for check, count in result.quality.items():
        quality.add_row(check, _number(count))
    console.print(quality)


def execute_index(session_id: int | None, limit: int | None, rebuild: bool) -> IndexStats:
    """Verdrahtet Konfiguration, Embedder und Datenbank (in Tests ersetzbar)."""
    settings = Settings()
    config = IndexConfig.from_settings(settings)
    typer.echo(f"Index-Signatur: {config.signature}")
    return index_documents(
        get_engine(),
        get_embedder(settings),
        config,
        session_id=session_id,
        limit=limit,
        rebuild=rebuild,
        progress=log_progress,
    )


@app.command()
def index(
    session_id: Annotated[
        int | None, typer.Option(help="Nur diese Session (Voten und dort debattierte Geschäfte).")
    ] = None,
    limit: Annotated[
        int | None, typer.Option(min=1, help="Höchstens so viele Dokumente (zum Testen).")
    ] = None,
    rebuild: Annotated[
        bool, typer.Option(help="Alles neu indexieren, auch wenn die Signatur passt.")
    ] = False,
) -> None:
    """Chunkt und bettet neue oder geänderte Dokumente ein (inkrementell)."""
    result = execute_index(session_id, limit, rebuild)
    if result.pending == 0:
        typer.echo("Nichts zu tun: Alle Dokumente sind mit der aktuellen Signatur indexiert.")
        return
    typer.echo(
        f"Indexiert: {result.documents} Dokumente, {result.chunks} Chunks in "
        f"{result.seconds:.0f} s ({result.chunks_per_second:.1f} Chunks/s)"
    )
