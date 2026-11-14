"""Kommandozeile `parlrag` (Typer)."""

import datetime as dt
import logging
import time
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any, cast

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table
from sqlalchemy.orm import sessionmaker

from parlrag.config import Settings
from parlrag.db.session import get_engine
from parlrag.embeddings import get_embedder
from parlrag.evals import DEFAULT_GOLDEN_PATH, GoldenSetError, load_golden
from parlrag.evals.answers import (
    AnswerResult,
    SupportsAsk,
    evaluate_answers,
    resume_mismatch,
    reusable_answers,
)
from parlrag.evals.judge import Judge
from parlrag.evals.results import (
    ANSWER_HEADER,
    DEFAULT_RESULTS_DIR,
    SUBSET_HEADER,
    THRESHOLD_HEADER,
    EvalError,
    EvalRun,
    answer_progress,
    answer_rows,
    answer_summary,
    comparison_warning,
    find_previous,
    git_state,
    load_run,
    metric_rows,
    misses,
    subset_rows,
    threshold_rows,
    write_run,
)
from parlrag.evals.runner import (
    CHUNKS_PER_QUERY,
    QuestionResult,
    corpus_snapshot,
    evaluate_retrieval,
    select_suite,
)
from parlrag.evals.threshold import threshold_report, threshold_summary
from parlrag.generation.formatting import answer_json, format_answer
from parlrag.generation.pipeline import build_pipeline
from parlrag.index.indexer import IndexConfig, IndexStats, index_documents, log_progress
from parlrag.ingest.mapping import LANGUAGES, Language
from parlrag.ingest.odata import ODataClient
from parlrag.ingest.pipeline import IngestStats, run_ingest
from parlrag.ingest.source import ODataSource
from parlrag.llm import LLMError, get_llm
from parlrag.retrieval import RetrievalConfig, Retriever, SearchFilters, SearchMode
from parlrag.retrieval.formatting import format_results, results_json
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

    index_table = Table("Kennzahl", "Wert", title="Index")
    index_table.add_row("indexierte Dokumente", _number(result.index.indexed_documents))
    index_table.add_row("Chunks", _number(result.index.chunks))
    index_table.add_row("Tokens je Chunk (Mittel)", _number(result.index.mean_chunk_tokens))
    for signature, count in result.index.chunks_by_signature.items():
        index_table.add_row(f"Signatur {signature}", _number(count))
    console.print(index_table)

    storage = Table("Objekt", "Grösse", title="Speicher (ganze Datenbank)")
    storage.add_row("Datenbank", _megabytes(result.storage.database))
    storage.add_row("Tabelle documents (mit Indizes)", _megabytes(result.storage.documents_table))
    storage.add_row("Tabelle chunks (mit Indizes)", _megabytes(result.storage.chunks_table))
    storage.add_row("davon HNSW-Index", _megabytes(result.storage.vector_index))
    console.print(storage)


def _megabytes(size: int) -> str:
    return f"{size / 1024 / 1024:,.0f} MB".replace(",", "'")


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


class ModeChoice(StrEnum):
    hybrid = "hybrid"
    fulltext = "fulltext"
    vector = "vector"


MODE_HELP = "Suchart; ohne Angabe gilt RETRIEVAL_MODE (Standard: vector)."


class CouncilChoice(StrEnum):
    NR = "NR"
    SR = "SR"
    V = "V"


def build_retriever() -> Retriever:
    """Verdrahtet Datenbank, Embedder und Konfiguration (in Tests ersetzbar)."""
    settings = Settings()
    return Retriever(get_engine(), get_embedder(settings), RetrievalConfig.from_settings(settings))


def _filters(
    council: "CouncilChoice | None",
    date_from: dt.datetime | None,
    date_to: dt.datetime | None,
    parl_group: str | None,
) -> SearchFilters:
    try:
        return SearchFilters(
            council=council.value if council else None,
            date_from=date_from.date() if date_from else None,
            date_to=date_to.date() if date_to else None,
            parl_group=parl_group,
        )
    except ValidationError as exc:
        raise typer.BadParameter(exc.errors()[0]["msg"], param_hint="--date-from") from exc


@app.command()
def search(
    query: Annotated[str, typer.Argument(help="Frage oder Suchbegriffe.")],
    mode: Annotated[ModeChoice | None, typer.Option(help=MODE_HELP)] = None,
    top: Annotated[int, typer.Option(min=1, max=100, help="Anzahl Treffer.")] = 10,
    council: Annotated[CouncilChoice | None, typer.Option(help="Nur dieser Rat.")] = None,
    date_from: Annotated[
        dt.datetime | None, typer.Option(formats=["%Y-%m-%d"], help="Ab Datum (inklusive).")
    ] = None,
    date_to: Annotated[
        dt.datetime | None, typer.Option(formats=["%Y-%m-%d"], help="Bis Datum (inklusive).")
    ] = None,
    parl_group: Annotated[
        str | None, typer.Option(help="Nur Voten dieser Fraktion, z. B. RL, S, V, M-E, G, GL.")
    ] = None,
    as_json: Annotated[bool, typer.Option("--json", help="Ausgabe als JSON.")] = False,
) -> None:
    """Nur Retrieval: Treffer mit Scores, Metadaten, Ausschnitt und Link (zum Prüfen)."""
    filters = _filters(council, date_from, date_to, parl_group)
    retriever = build_retriever()
    chosen = mode.value if mode else retriever.config.mode
    model_load_ms = None
    if chosen != "fulltext":
        # Modell vorab laden, damit die gemessene Suchzeit den einmaligen Start nicht enthält.
        start = time.monotonic()
        retriever.embedder.embed_query("Modell laden")
        model_load_ms = (time.monotonic() - start) * 1000
    start = time.monotonic()
    hits = retriever.search(query, filters, mode=chosen, top_n=top)
    duration_ms = (time.monotonic() - start) * 1000
    render = results_json if as_json else format_results
    typer.echo(render(query, chosen, filters, hits, duration_ms, model_load_ms))


class SuiteChoice(StrEnum):
    smoke = "smoke"
    full = "full"


def describe_eval(retriever: Retriever) -> tuple[dict[str, Any], dict[str, Any]]:
    """Konfiguration und Korpus-Stand für die Ergebnisdatei (in Tests ersetzbar)."""
    settings = Settings()
    config: dict[str, Any] = {
        "chunks_per_query": CHUNKS_PER_QUERY,
        "retrieval_candidates": retriever.config.candidates,
        "retrieval_rrf_k": retriever.config.rrf_k,
        "embedding_model": settings.embedding_model,
        "embedding_max_seq_length": settings.embedding_max_seq_length,
        "index_signature": IndexConfig.from_settings(settings).signature,
        "answer_min_similarity": settings.answer_min_similarity,
    }
    return config, corpus_snapshot(retriever.engine)


def build_answer_evaluation(
    retriever: Retriever,
) -> tuple[SupportsAsk, Judge, dict[str, Any]]:
    """Pipeline wie `ask` (mit geteiltem Retriever) und Judge (in Tests ersetzbar)."""
    settings = Settings()
    pipeline = build_pipeline(settings, retriever=retriever)
    judge = Judge(get_llm(settings, model=settings.judge_model, effort=settings.judge_effort))
    config: dict[str, Any] = {
        "answer_model": settings.anthropic_model,
        "answer_effort": settings.anthropic_effort,
        "llm_backend": settings.llm_backend,
        "judge_model": settings.judge_model,
        "judge_effort": settings.judge_effort,
        "answer_prompt_version": pipeline.generator.prompt.version,
        "judge_prompt_version": judge.prompt.version,
        "answer_context_chunks": settings.answer_context_chunks,
        "answer_min_similarity": settings.answer_min_similarity,
    }
    return pipeline, judge, config


@app.command("eval")
def eval_command(
    suite: Annotated[
        SuiteChoice, typer.Option(help="smoke: Fragen mit Tag smoke; full: alle Fragen.")
    ] = SuiteChoice.smoke,
    mode: Annotated[ModeChoice | None, typer.Option(help=MODE_HELP)] = None,
    compare: Annotated[
        Path | None,
        typer.Option(help="Mit diesem Lauf vergleichen statt mit dem letzten gleicher Art."),
    ] = None,
    golden: Annotated[Path, typer.Option(help="Goldset (JSONL).")] = DEFAULT_GOLDEN_PATH,
    results_dir: Annotated[
        Path, typer.Option(help="Verzeichnis der Ergebnisdateien.")
    ] = DEFAULT_RESULTS_DIR,
    answers: Annotated[
        bool,
        typer.Option(
            "--answers",
            help="Auch Antworten erzeugen und per Judge bewerten (LLM-Aufrufe, kostet).",
        ),
    ] = False,
    resume: Annotated[
        Path | None,
        typer.Option(
            help="Mit --answers: fehlerfreie Antworten dieses Laufs übernehmen, nur den Rest "
            "nachholen (gleiche Konfiguration nötig)."
        ),
    ] = None,
) -> None:
    """Evals auf dem Goldset; nur lokal mit uv (Git-SHA in der Ergebnisdatei).

    Ohne `--answers` nur Retrieval (deterministisch, ohne LLM).
    """
    console = Console()
    try:
        sha, dirty = git_state()
        items = load_golden(golden)
    except (EvalError, GoldenSetError, OSError) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    retriever = build_retriever()
    chosen = mode.value if mode else retriever.config.mode
    answer_parts = None
    if answers:
        try:  # vor dem Retrieval: ein fehlender Key oder eine fehlende CLI bricht sofort ab
            answer_parts = build_answer_evaluation(retriever)
        except LLMError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(1) from exc
    answer_model = answer_parts[2]["answer_model"] if answer_parts else None
    reuse: dict[str, AnswerResult] = {}
    if resume:
        try:
            resumed = load_run(resume)
        except EvalError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(1) from exc
        mismatch = resume_mismatch(resumed.answer_config, answer_parts[2]) if answer_parts else []
        if not answer_parts or mismatch:
            reason = (
                "--resume braucht --answers"
                if not answer_parts
                else "andere Konfiguration als im fortgesetzten Lauf: " + ", ".join(mismatch)
            )
            console.print(f"[red]{reason}[/red]")
            raise typer.Exit(1)
        reuse = reusable_answers(resumed.answers, load_golden(golden))
        console.print(f"Übernehme {len(reuse)} fehlerfreie Antworten aus {resume.name}.")
    try:
        previous_path = compare or (
            find_previous(results_dir, suite.value, chosen, answer_model)
            if results_dir.exists()
            else None
        )
        previous = load_run(previous_path) if previous_path else None
    except EvalError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    if dirty:
        console.print(
            "[yellow]Achtung: ungecommittete Änderungen; der Lauf ist nicht genau einem Commit "
            "zuzuordnen.[/yellow]"
        )
    selection = select_suite(items, suite.value)

    if chosen != "fulltext":
        retriever.embedder.embed_query("Modell laden")  # Ladezeit nicht in der Suchdauer
    config, corpus = describe_eval(retriever)

    def show_progress(result: QuestionResult) -> None:
        console.print(
            f"{result.id}  Recall@10 {result.metrics['recall@10']:.2f}  "
            f"MRR@10 {result.metrics['mrr@10']:.2f}  {result.search_ms:.0f} ms"
        )

    report = evaluate_retrieval(selection, retriever, chosen, progress=show_progress)
    answer_report = None
    if answer_parts:
        pipeline, judge, _ = answer_parts

        def show_answer(answer: AnswerResult) -> None:
            console.print(answer_progress(answer), highlight=False)

        console.print(f"\nAntworten ({answer_model}) und Judge ({judge.model}):")
        answer_report = evaluate_answers(
            selection, pipeline, judge, chosen, progress=show_answer, reuse=reuse
        )
    min_similarity = config.get("answer_min_similarity")
    threshold = (
        threshold_report(selection, report.similarities, float(min_similarity))
        if min_similarity is not None
        else None
    )
    run = EvalRun(
        created_at=dt.datetime.now().astimezone(),
        git_sha=sha,
        git_dirty=dirty,
        suite=suite.value,
        mode=chosen,
        golden=golden.as_posix(),
        questions_total=len(selection),
        skipped_unanswerable=report.skipped_unanswerable,
        config=config,
        corpus=corpus,
        metrics={**report.metrics, **(answer_report.metrics if answer_report else {})},
        subsets=report.subsets,
        questions=report.questions,
        previous=previous_path.name if previous_path else None,
        similarities=report.similarities,
        threshold=threshold,
        answer_config=answer_parts[2] if answer_parts else None,
        answer_counts=answer_report.counts if answer_report else {},
        answers=answer_report.answers if answer_report else [],
    )
    path = write_run(run, previous, results_dir)

    console.print(
        f"\n[bold]{suite.value} · {chosen}[/bold]: {len(report.questions)} Fragen gemessen, "
        f"{report.skipped_unanswerable} unbeantwortbare übersprungen"
    )
    console.print(
        f"Vergleich mit {previous_path.name}" if previous_path else "Kein Vorlauf zum Vergleich."
    )
    if warning := comparison_warning(run, previous):
        console.print(f"[yellow]{warning}[/yellow]")
    metrics_table = Table("Metrik", "Wert", "Vorlauf", "Δ", title="Metriken")
    for row in metric_rows(run.metrics, previous.metrics if previous else None):
        metrics_table.add_row(*row)
    console.print(metrics_table)
    subsets_table = Table(*SUBSET_HEADER, title="Teilsets")
    for subset_row in subset_rows(run, previous):
        subsets_table.add_row(*subset_row)
    console.print(subsets_table)
    if threshold:
        console.print(threshold_summary(threshold))
        threshold_table = Table(
            *THRESHOLD_HEADER, title="Schwelle für «keine ausreichende Grundlage»"
        )
        for threshold_row in threshold_rows(threshold):
            threshold_table.add_row(*threshold_row)
        console.print(threshold_table)
    if run.answers:
        console.print(answer_summary(run))
        answers_table = Table(*ANSWER_HEADER, title="Antworten")
        for answer_row in answer_rows(run):
            answers_table.add_row(*answer_row)
        console.print(answers_table)
    missed = misses(run)
    console.print(f"Verfehlte Quellen (Recall@10 < 1): {len(missed)}")
    for line in missed:
        console.print(f"  {line}", highlight=False)
    console.print(f"Ergebnis: {path} und {path.with_suffix('.md').name}")


@app.command()
def ask(
    question: Annotated[str, typer.Argument(help="Frage auf Deutsch oder Französisch.")],
    mode: Annotated[ModeChoice | None, typer.Option(help=MODE_HELP)] = None,
    council: Annotated[CouncilChoice | None, typer.Option(help="Nur dieser Rat.")] = None,
    date_from: Annotated[
        dt.datetime | None, typer.Option(formats=["%Y-%m-%d"], help="Ab Datum (inklusive).")
    ] = None,
    date_to: Annotated[
        dt.datetime | None, typer.Option(formats=["%Y-%m-%d"], help="Bis Datum (inklusive).")
    ] = None,
    parl_group: Annotated[
        str | None, typer.Option(help="Nur Voten dieser Fraktion, z. B. RL, S, V, M-E, G, GL.")
    ] = None,
    as_json: Annotated[bool, typer.Option("--json", help="Ausgabe als JSON.")] = False,
) -> None:
    """Antwort mit Quellen aus den Debatten und Geschäften (LLM gemäss LLM_BACKEND)."""
    filters = _filters(council, date_from, date_to, parl_group)
    console = Console(stderr=True)
    try:
        pipeline = build_pipeline()
        chosen: SearchMode | None = mode.value if mode else None
        model_load_ms = pipeline.warm_up(chosen)
        result = pipeline.ask(question, filters, mode=chosen)
    except LLMError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    render = answer_json if as_json else format_answer
    typer.echo(render(result, model_load_ms))
