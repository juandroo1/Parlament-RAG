"""Erkennung von Person und Zeitraum (Task 8.3; Spec 003, AK-17.1, AK-17.3, AK-17.6).

Ohne Datenbank und ohne Netz: Der Katalog kommt aus `tests/fixtures/catalog.json`, einem Export
der lokalen Datenbank (Korpus bis 2026-10-02, 276 Personen, 15 Sessionen).
"""

import datetime as dt
import json
import time
from pathlib import Path

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker

from ingest_fakes import PFAS_DAY, FixtureSource
from parlrag.evals import GoldenItem, load_golden
from parlrag.ingest.pipeline import run_ingest
from parlrag.query import Catalog, Detection, Speaker, detect, load_catalog
from parlrag.query.catalog import build_sessions, session_kind

REPO_ROOT = Path(__file__).resolve().parents[1]
TODAY = dt.date(2026, 11, 24)
D = dt.date


def _load_catalog_fixture() -> Catalog:
    data = json.loads((REPO_ROOT / "tests/fixtures/catalog.json").read_text(encoding="utf-8"))
    sessions = [
        (s["id"], D.fromisoformat(s["first"]), D.fromisoformat(s["last"])) for s in data["sessions"]
    ]
    return Catalog(
        first=D.fromisoformat(data["first"]),
        last=D.fromisoformat(data["last"]),
        sessions=build_sessions(sessions),
        speakers=tuple(Speaker(**speaker) for speaker in data["speakers"]),
    )


CATALOG = _load_catalog_fixture()


def run(question: str) -> Detection:
    return detect(question, CATALOG, TODAY)


def period(question: str) -> tuple[dt.date | None, dt.date | None] | None:
    found = run(question).period
    return None if found is None else (found.date_from, found.date_to)


def speaker(question: str) -> str | None:
    found = run(question).speaker
    return None if found is None else found.name


def candidates(question: str) -> list[str]:
    return [s.name for s in run(question).speaker_candidates]


# --- Katalog -------------------------------------------------------------------------------


def test_catalog_fixture_has_all_sessions_with_kind_and_year() -> None:
    assert (CATALOG.first, CATALOG.last) == (D(2023, 12, 4), D(2026, 10, 2))
    assert len(CATALOG.speakers) == 276
    kinds = [(s.kind, s.year) for s in CATALOG.sessions]
    assert kinds[:5] == [
        ("winter", 2023),
        ("spring", 2024),
        ("special", 2024),
        ("summer", 2024),
        ("autumn", 2024),
    ]
    assert kinds[-1] == ("autumn", 2026)  # 14.9. bis 2.10.2026: Mitte im September
    assert CATALOG.last_session is not None and CATALOG.last_session.id == 5215


def test_session_kind_from_middle_month() -> None:
    assert session_kind(D(2024, 5, 27), D(2024, 6, 14)) == "summer"  # beginnt im Mai
    assert session_kind(D(2024, 2, 26), D(2024, 3, 15)) == "spring"
    assert session_kind(D(2024, 7, 1), D(2024, 7, 3)) is None  # keine übliche Session


@pytest.mark.db
def test_load_catalog_from_database(empty_db: Engine) -> None:
    run_ingest(FixtureSource(), sessionmaker(empty_db), PFAS_DAY, PFAS_DAY, frozenset({"de", "fr"}))
    with empty_db.connect() as connection:
        catalog = load_catalog(connection)
    assert catalog.first == catalog.last == PFAS_DAY
    assert [s.kind for s in catalog.sessions] == ["autumn"]
    assert any(s.name == "Michel Matthias" for s in catalog.speakers)


@pytest.mark.db
def test_load_catalog_without_documents(empty_db: Engine) -> None:
    with empty_db.connect() as connection:
        catalog = load_catalog(connection)
    assert catalog == Catalog(first=None, last=None, sessions=(), speakers=())
    assert detect("Was sagte Funiciello 2022?", catalog, TODAY).speaker is None


# --- Zeitraum -------------------------------------------------------------------------------

YEAR_2024 = (D(2024, 1, 1), D(2024, 12, 31))


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        # Jahr: mit Präposition, nach Person oder Funktion, nach kleingeschriebenem Wort
        ("Was sagte der Bundesrat im Jahr 2024 zur AHV?", YEAR_2024),
        ("Was wurde 2024 zur AHV gesagt?", YEAR_2024),
        ("Was sagte der Bundesrat 2024 zur AHV?", YEAR_2024),
        ("Was hat Funiciello 2024 gesagt?", YEAR_2024),
        ("Qu'a dit le Conseil fédéral en 2024 sur l'AVS ?", YEAR_2024),
        ("2024: Was sagte der Ständerat zum Wolf?", YEAR_2024),
        # Monat
        ("Was sagte der Nationalrat im März 2025 zum Wolf?", (D(2025, 3, 1), D(2025, 3, 31))),
        ("Qu'a dit le Conseil national en août 2025 ?", (D(2025, 8, 1), D(2025, 8, 31))),
        ("Was wurde im Mai 2026 beschlossen?", (D(2026, 5, 1), D(2026, 5, 31))),
        # Session aus dem Katalog
        ("Was sagte Jans in der Herbstsession 2026?", (D(2026, 9, 14), D(2026, 10, 2))),
        ("Sommersession 2024: Wolf", (D(2024, 5, 27), D(2024, 6, 14))),
        (
            "Qu'a dit le Conseil fédéral lors de la session d'été 2025 ?",
            (D(2025, 6, 2), D(2025, 6, 20)),
        ),
        (
            "Qu'a dit le Conseil fédéral lors de la session d’automne 2024 ?",  # noqa: RUF001
            (D(2024, 9, 9), D(2024, 9, 27)),
        ),
        ("Was geschah in der Sondersession 2025?", (D(2025, 5, 5), D(2025, 5, 7))),
        ("Qu'a-t-on dit lors de la session spéciale 2026 ?", (D(2026, 4, 27), D(2026, 4, 30))),
        ("Qu'a-t-on dit lors de la session de printemps 2024 ?", (D(2024, 2, 26), D(2024, 3, 15))),
        ("Was sagte der Rat in der letzten Session?", (D(2026, 9, 14), D(2026, 10, 2))),
        ("Qu'a dit le Conseil lors de la dernière session ?", (D(2026, 9, 14), D(2026, 10, 2))),
        # Session ausserhalb der Daten: Kalendermonat, auch in der Zukunft
        ("Was beschloss der Ständerat in der Herbstsession 2022?", (D(2022, 9, 1), D(2022, 9, 30))),
        ("Was sagte Pfister in der Frühjahrssession 2027?", (D(2027, 3, 1), D(2027, 3, 31))),
        (
            "Qu'a dit le Conseil lors de la session d'hiver 2021 ?",
            (D(2021, 12, 1), D(2021, 12, 31)),
        ),
        # Bereiche
        ("Was sagte Keller-Sutter seit 2025 zur Rechnung?", (D(2025, 1, 1), None)),
        ("Was wurde ab 2025 zum Wolf gesagt?", (D(2025, 1, 1), None)),
        ("Was wurde nach 2024 zum Wolf gesagt?", (D(2025, 1, 1), None)),
        ("Was wurde vor 2025 zum Wolf gesagt?", (None, D(2024, 12, 31))),
        ("Was wurde bis 2024 zum Wolf gesagt?", (None, D(2024, 12, 31))),
        ("Was wurde zwischen 2024 und 2025 zum Wolf gesagt?", (D(2024, 1, 1), D(2025, 12, 31))),
        ("Was wurde von 2024 bis 2025 zum Wolf gesagt?", (D(2024, 1, 1), D(2025, 12, 31))),
        ("Was wurde seit 2024 bis 2025 zum Wolf gesagt?", (D(2024, 1, 1), D(2025, 12, 31))),
        ("Qu'a-t-on dit depuis 2025 sur le loup ?", (D(2025, 1, 1), None)),
        ("Qu'a-t-on dit dès 2025 sur le loup ?", (D(2025, 1, 1), None)),
        ("Qu'a-t-on dit à partir de 2025 sur le loup ?", (D(2025, 1, 1), None)),
        ("Qu'a-t-on dit après 2024 sur le loup ?", (D(2025, 1, 1), None)),
        ("Qu'a-t-on dit avant 2025 sur le loup ?", (None, D(2024, 12, 31))),
        ("Qu'a-t-on dit jusqu'en 2024 sur le loup ?", (None, D(2024, 12, 31))),
        ("Qu'a-t-on dit entre 2024 et 2025 sur le loup ?", (D(2024, 1, 1), D(2025, 12, 31))),
        ("Qu'a-t-on dit de 2024 à 2025 sur le loup ?", (D(2024, 1, 1), D(2025, 12, 31))),
        # Die erste Angabe gilt
        (
            "Was sagte Rösti im März 2025 und in der Herbstsession 2026?",
            (D(2025, 3, 1), D(2025, 3, 31)),
        ),
    ],
)
def test_period_is_detected(question: str, expected: tuple[dt.date | None, dt.date | None]) -> None:
    assert period(question) == expected


@pytest.mark.parametrize(
    "question",
    [
        "Was enthält die Energiestrategie 2050?",  # Titel und Zukunft
        "Welche Kredite beantragte der Bundesrat mit dem Voranschlag 2025?",  # Titel
        "Wie bezeichnete der Bundesrat die Armeebotschaft 2024?",  # Titel
        "Qu'a dit le Conseil fédéral sur le budget 2022 ?",  # Titel
        "Que contient le rapport de politique extérieure 2024 ?",  # Titel
        "Wie soll die Schweiz bis 2050 klimaneutral werden?",  # Ziel in der Zukunft
        "Was sagte der Bundesrat zur Agenda 2030?",
        "Wie viele Schäden verursachte der Hitzesommer 2026?",
        "Was wurde zur 13. AHV-Rente gesagt?",
        "Was sagte der Bundesrat zur Motion 24.3456?",
        "Was wurde seit 2025 bis 2024 gesagt?",  # widersprüchlich
        "Qu'a-t-on dit entre 2025 et 2024 ?",  # widersprüchlich
        "Was sagte der Ständerat im März?",  # Monat ohne Jahr
        "Was wurde in der Herbstsession gesagt?",  # Session ohne Jahr
    ],
)
def test_no_period_is_detected(question: str) -> None:
    assert period(question) is None


# --- Person ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("Was sagte Tamara Funiciello zum Stalking?", "Funiciello Tamara"),
        ("Was sagte Funiciello Tamara zum Stalking?", "Funiciello Tamara"),
        ("Was sagte Funiciello zum Stalking?", "Funiciello Tamara"),  # Nachname + Verb
        ("Stalking laut Funiciello", "Funiciello Tamara"),  # Zuschreibung
        ("Wie begründete Bundesrat Rösti den Netzzuschlag?", "Rösti Albert"),
        ("Was sagte Bundesrätin Keller-Sutter zur Rechnung?", "Keller-Sutter Karin"),
        ("Qu'a dit la conseillère nationale Funiciello ?", "Funiciello Tamara"),
        ("Selon le conseiller fédéral Parmelin, que faut-il faire ?", "Parmelin Guy"),
        ("Comment Celine Amaudruz a-t-elle présenté la motion ?", "Amaudruz Céline"),  # Akzent
        ("Was sagte Michaud Gigon zur Pflege?", "Michaud Gigon Sophie"),  # Doppelname
        ("Was sagte Sophie Michaud Gigon zur Pflege?", "Michaud Gigon Sophie"),
        ("Was sagte Jacqueline de Quattro zur Armee?", "de Quattro Jacqueline"),  # Partikel
        # Funktion entscheidet bei gleichem Nachnamen
        ("Was sagte Bundesrat Pfister zur Armeebotschaft?", "Pfister Martin"),
        ("Was sagte Nationalrat Pfister zur Armeebotschaft?", "Pfister Gerhard"),
        ("Was sagte Ständerat Müller zur Stopfleber?", "Müller Damian"),
        ("Was sagte Nationalrat Müller zum Shoppingtourismus?", "Müller Leo"),
        ("Was sagte Damian Müller zur Stopfleber?", "Müller Damian"),  # Vorname entscheidet
    ],
)
def test_person_is_detected(question: str, expected: str) -> None:
    assert speaker(question) == expected
    assert candidates(question) == []


@pytest.mark.parametrize(
    "question",
    [
        "Was sagte der Bundesrat zum Wolf?",  # Gremium
        "Qu'a dit le Conseil fédéral sur le loup ?",
        "Was sagte Tamara zum Stalking?",  # nur Vorname
        "Qu'a dit Céline sur la motion ?",  # Vorname von zwei Personen
        "Was sagte der Bundesrat zur Lage der Fischer?",  # Artikel: Nomen
        "Welche Massnahmen gibt es für Fischer?",  # kein Signal
        "Ist der Zuwachs stark gestiegen?",  # klein geschrieben
        "Was sagte Bundesrat Ueli Maurer zur STAF?",  # nicht im Korpus
        "Was wurde im Nationalrat zur Initiative Funiciello gesagt?",  # Titel
        "Was verlangt die Motion Funiciello Tamara?",  # Titel mit Vor- und Nachname
        "Qu'a-t-on dit de l'initiative parlementaire Funiciello ?",
    ],
)
def test_no_person_is_detected(question: str) -> None:
    assert speaker(question) is None
    assert candidates(question) == []


def test_title_mention_is_reported() -> None:
    assert run("Was wurde zur Initiative Funiciello gesagt?").title_mention
    assert not run("Was sagte Funiciello?").title_mention


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("Was sagte Müller zur Stopfleber?", ["Müller Damian", "Müller Leo"]),
        ("Was meinte Graf zur Biodiversität?", ["Graf Maya", "Seiler Graf Priska"]),
        ("Was sagte Pfister zur Armee?", ["Pfister Gerhard", "Pfister Martin"]),
        # zwei verschiedene Personen: kein Filter, beide zur Auswahl
        (
            "Was entgegnete Bundesrat Rösti auf die Frage von Funiciello?",
            ["Funiciello Tamara", "Rösti Albert"],
        ),
    ],
)
def test_ambiguous_names_give_candidates(question: str, expected: list[str]) -> None:
    assert speaker(question) is None
    assert candidates(question) == expected


# --- Goldset -------------------------------------------------------------------------------

# Erwartete Erkennung pro Goldset-Frage; alle anderen Fragen ergeben keine Erkennung.
P, K, Z, T = "speaker", "candidates", "period", "title"
GOLDEN_EXPECTED: dict[str, dict[str, object]] = {
    "q01": {P: "Rösti Albert"},
    "q03": {P: "Rösti Albert"},
    "q04": {P: "Rösti Albert"},
    "q05": {P: "Pfister Martin"},
    "q07": {T: True},
    "q08": {T: True},
    "q10": {P: "Baume-Schneider Elisabeth"},
    "q11": {P: "Jans Beat"},
    "q12": {P: "Parmelin Guy"},
    "q13": {P: "Parmelin Guy"},
    "q14": {P: "Baume-Schneider Elisabeth"},
    "q16": {T: True},
    "q19": {P: "Cassis Ignazio"},
    "q20": {P: "Jans Beat"},
    "q23": {P: "Caroni Andrea"},
    "q24": {P: "Baume-Schneider Elisabeth"},
    "q25": {P: "Parmelin Guy"},
    "q29": {Z: (D(2026, 12, 1), D(2026, 12, 31))},  # Wintersession 2026, nach den Daten
    "q37": {P: "Jans Beat"},
    "q42": {P: "Cassis Ignazio"},
    "q43": {P: "Parmelin Guy"},
    "q44": {P: "Parmelin Guy"},
    "q48": {P: "Keller-Sutter Karin"},
    "q49": {P: "Jans Beat"},
    "q50": {P: "Jans Beat"},
    "q51": {P: "Baume-Schneider Elisabeth"},
    "q52": {P: "Rösti Albert"},
    "q54": {P: "Rösti Albert"},
    "q55": {P: "Baume-Schneider Elisabeth"},
    "q56": {P: "Parmelin Guy"},
    "q57": {P: "Rösti Albert"},
    "q61": {Z: (D(2026, 1, 1), D(2026, 12, 31))},  # «für das Jahr 2026», kantonal
    "q62": {Z: (D(2026, 12, 1), D(2026, 12, 31))},
    "q64": {Z: (D(2026, 1, 1), D(2026, 12, 31))},
    "q65": {P: "Jans Beat"},
    "q66": {P: "Funiciello Tamara", Z: (D(2025, 1, 1), D(2025, 12, 31))},
    "q67": {P: "Jans Beat", Z: (D(2026, 9, 14), D(2026, 10, 2))},
    "q68": {P: "Parmelin Guy", Z: (D(2025, 3, 1), D(2025, 3, 31))},
    "q69": {P: "Keller-Sutter Karin", Z: (D(2025, 1, 1), None)},
    "q70": {Z: YEAR_2024},
    "q71": {Z: (D(2025, 6, 2), D(2025, 6, 20))},
    "q72": {Z: (D(2024, 12, 1), D(2024, 12, 31))},  # «Armeebotschaft 2024» ist ein Titel
    "q73": {K: ["Müller Damian", "Müller Leo"]},
    "q74": {T: True},  # «Initiative Funiciello»: keine Person
    "q75": {P: "Funiciello Tamara"},
    "q76": {P: "Amaudruz Céline"},
    "q77": {P: "Funiciello Tamara", Z: (D(2022, 1, 1), D(2022, 12, 31))},
    "q78": {Z: (D(2022, 3, 1), D(2022, 3, 31))},
    "q79": {Z: (D(2021, 12, 1), D(2021, 12, 31))},  # «budget 2022» ist ein Titel
    "q80": {P: "Pfister Martin", Z: (D(2027, 3, 1), D(2027, 3, 31))},
}

GOLDEN = load_golden(REPO_ROOT / "evals/datasets/golden.jsonl")


@pytest.mark.parametrize("item", GOLDEN, ids=lambda item: item.id)
def test_detection_on_goldset(item: GoldenItem) -> None:
    expected = GOLDEN_EXPECTED.get(item.id, {})
    found = run(item.question)
    assert (found.speaker.name if found.speaker else None) == expected.get(P)
    assert [s.name for s in found.speaker_candidates] == expected.get(K, [])
    got = None if found.period is None else (found.period.date_from, found.period.date_to)
    assert got == expected.get(Z)
    assert found.title_mention == expected.get(T, False)


def test_every_person_time_question_is_detected() -> None:
    """AK-17.1: Jede Frage mit Tag `person-zeit` ergibt eine Person, Kandidaten, einen
    Zeitraum oder einen Titel."""
    for item in GOLDEN:
        if item.has("person-zeit"):
            assert item.id in GOLDEN_EXPECTED, item.id


# --- Latenz ----------------------------------------------------------------------------------


def test_detection_is_fast() -> None:
    """Plan: unter 50 ms pro Frage; 100 Fragen gegen 276 Personen deutlich unter 1 s."""
    questions = [item.question for item in GOLDEN]
    run(questions[0])  # Index aufbauen
    start = time.perf_counter()
    for k in range(100):
        run(questions[k % len(questions)])
    assert time.perf_counter() - start < 1.0
