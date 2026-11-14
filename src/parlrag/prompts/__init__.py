"""Prompts als Markdown-Dateien im Paket (CLAUDE.md: jede Änderung braucht einen Eval-Lauf).

`version` ist ein kurzer Hash des Inhalts, damit Evals festhalten können, welcher Prompt lief.
"""

import hashlib
from dataclasses import dataclass
from importlib.resources import files


@dataclass(frozen=True)
class Prompt:
    name: str
    text: str

    @property
    def version(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()[:12]


def load_prompt(name: str) -> Prompt:
    """Lädt `prompts/<name>.md` aus dem installierten Paket (auch im Container)."""
    text = files("parlrag.prompts").joinpath(f"{name}.md").read_text(encoding="utf-8")
    return Prompt(name=name, text=text.strip())
