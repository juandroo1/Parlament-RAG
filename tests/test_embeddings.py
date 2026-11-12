"""Embedding-Interface und bge-m3-Implementierung (Task 2.2).

Die normalen Tests nutzen ein nachgebautes Modell und laden nichts herunter. Die Tests mit
dem echten Modell (Marker `model`) laufen nur mit `PARLRAG_RUN_MODEL_TESTS=1`.
"""

import os
import subprocess
import sys
import threading
from typing import Any

import numpy as np
import pytest

from parlrag.config import Settings
from parlrag.embeddings import BgeM3Embedder, Embedder, EmbeddingError, get_embedder


class FakeModel:
    """Verhält sich wie `SentenceTransformer.encode`, zählt Aufrufe und Argumente."""

    def __init__(self, dimensions: int = 1024) -> None:
        self.dimensions = dimensions
        self.calls: list[dict[str, Any]] = []

    def encode(self, sentences: list[str], **kwargs: Any) -> np.ndarray[Any, Any]:
        self.calls.append({"sentences": sentences, **kwargs})
        rng = np.random.default_rng(len(sentences))
        vectors = rng.normal(size=(len(sentences), self.dimensions))
        return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)


class Loader:
    def __init__(self, model: FakeModel) -> None:
        self.model = model
        self.loads = 0

    def __call__(self) -> FakeModel:
        self.loads += 1
        return self.model


def make_embedder(model: FakeModel | None = None, **kwargs: Any) -> tuple[BgeM3Embedder, Loader]:
    loader = Loader(model or FakeModel())
    token_loads: list[int] = []

    def token_counter_loader() -> Any:
        token_loads.append(1)
        return lambda text: len(text.split())

    embedder = BgeM3Embedder(
        model_loader=loader, token_counter_loader=token_counter_loader, **kwargs
    )
    embedder.token_loads = token_loads  # type: ignore[attr-defined]
    return embedder, loader


def test_model_is_loaded_lazily_and_once() -> None:
    embedder, loader = make_embedder()
    assert loader.loads == 0
    assert not embedder.model_loaded

    embedder.embed_documents(["Erster Text"])
    embedder.embed_documents(["Zweiter Text"])
    embedder.embed_query("Frage")

    assert loader.loads == 1
    assert embedder.model_loaded


def test_concurrent_first_use_loads_the_model_once() -> None:
    embedder, loader = make_embedder()
    threads = [threading.Thread(target=embedder.embed_query, args=("Frage",)) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert loader.loads == 1


def test_batches_are_normalized_float32_with_expected_shape() -> None:
    model = FakeModel()
    embedder, _ = make_embedder(model, batch_size=32)

    vectors = embedder.embed_documents(["a", "b", "c"])

    assert vectors.shape == (3, 1024)
    assert vectors.dtype == np.float32
    np.testing.assert_allclose(np.linalg.norm(vectors, axis=1), 1.0, rtol=1e-5)
    (call,) = model.calls
    assert call["sentences"] == ["a", "b", "c"]
    assert call["batch_size"] == 32
    assert call["normalize_embeddings"] is True


def test_query_returns_single_vector() -> None:
    embedder, _ = make_embedder()
    assert embedder.embed_query("Was sagte der Ständerat zu PFAS?").shape == (1024,)


def test_empty_input_does_not_load_the_model() -> None:
    embedder, loader = make_embedder()
    vectors = embedder.embed_documents([])
    assert vectors.shape == (0, 1024)
    assert loader.loads == 0


def test_wrong_dimension_is_rejected() -> None:
    embedder, _ = make_embedder(FakeModel(dimensions=768))
    with pytest.raises(EmbeddingError, match="768"):
        embedder.embed_documents(["Text"])


def test_count_tokens_loads_only_the_tokenizer() -> None:
    embedder, loader = make_embedder()

    assert embedder.count_tokens("drei Wörter hier") == 3
    assert embedder.count_tokens("noch zwei") == 2

    assert loader.loads == 0
    assert embedder.token_loads == [1]  # type: ignore[attr-defined]


def test_get_embedder_uses_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POSTGRES_PASSWORD", "x")
    monkeypatch.setenv("EMBEDDING_BATCH_SIZE", "8")
    embedder = get_embedder(Settings(_env_file=None))

    assert isinstance(embedder, BgeM3Embedder)
    assert embedder.model_name == "BAAI/bge-m3"
    assert embedder.dimensions == 1024
    assert embedder.batch_size == 8
    assert not embedder.model_loaded


def test_embedder_satisfies_interface() -> None:
    embedder: Embedder = make_embedder()[0]
    assert embedder.dimensions == 1024


def test_importing_app_and_cli_does_not_import_torch() -> None:
    code = (
        "import sys, parlrag.api.main, parlrag.cli, parlrag.embeddings; "
        "print(sorted(m for m in ('torch', 'sentence_transformers', 'transformers') "
        "if m in sys.modules))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True, timeout=120
    )
    assert result.stdout.strip() == "[]"


# --- Echtes Modell (nur auf Abruf) ---------------------------------------------------

requires_model = pytest.mark.skipif(
    os.environ.get("PARLRAG_RUN_MODEL_TESTS") != "1",
    reason="lädt bge-m3 (rund 2,3 GB); mit PARLRAG_RUN_MODEL_TESTS=1 aktivieren",
)


@pytest.fixture(scope="module")
def real_embedder() -> BgeM3Embedder:
    return BgeM3Embedder()


@pytest.mark.model
@requires_model
def test_real_model_matches_meaning_across_languages(real_embedder: BgeM3Embedder) -> None:
    german, french, other = real_embedder.embed_documents(
        [
            "Der Bund soll mehr Geld in den Ausbau der Bahninfrastruktur investieren.",
            "La Confédération doit investir davantage dans l'extension de l'infrastructure "
            "ferroviaire.",
            "Die Landwirtschaft leidet unter der Trockenheit im Sommer.",
        ]
    )
    same_meaning = float(german @ french)
    different_topic = float(german @ other)
    assert same_meaning > different_topic + 0.15
    assert same_meaning > 0.7


@pytest.mark.model
@requires_model
def test_real_tokenizer_counts_tokens(real_embedder: BgeM3Embedder) -> None:
    count = real_embedder.count_tokens("Die Kantone fordern Massnahmen gegen PFAS.")
    assert 5 <= count <= 20
