"""Der Schalter PARLRAG_REQUIRE_DB entscheidet, ob fehlende DB-Tests übersprungen werden."""

import pytest

from conftest import REQUIRE_DB_ENV, skip_or_fail


def test_skips_without_requirement(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(REQUIRE_DB_ENV, raising=False)

    with pytest.raises(pytest.skip.Exception):
        skip_or_fail("keine DB")


def test_fails_when_database_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(REQUIRE_DB_ENV, "1")

    with pytest.raises(pytest.fail.Exception, match="keine DB"):
        skip_or_fail("keine DB")
