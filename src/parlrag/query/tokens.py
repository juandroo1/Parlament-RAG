"""Zerlegung der Frage in Wörter für die Erkennung (Spec 003, plan.md Abschnitte 4 und 5).

Verglichen wird in einer normalisierten Form: ohne Akzente, kleingeschrieben («Rösti» → «rosti»).
Bindestrich-Namen bleiben ein Wort («Keller-Sutter»), Apostrophe trennen («d'après» → «d», «apres»).
"""

import re
import unicodedata
from dataclasses import dataclass

WORD = re.compile(r"[^\W\d_]+(?:-[^\W\d_]+)*|\d+")


def normalize(word: str) -> str:
    decomposed = unicodedata.normalize("NFKD", word)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold()


@dataclass(frozen=True)
class Token:
    text: str  # wie in der Frage
    norm: str  # ohne Akzente, kleingeschrieben
    start: int  # Position im Text
    end: int

    @property
    def capitalized(self) -> bool:
        return self.text[:1].isupper()

    @property
    def is_number(self) -> bool:
        return self.text.isdigit()


def tokenize(text: str) -> list[Token]:
    return [
        Token(match.group(), normalize(match.group()), match.start(), match.end())
        for match in WORD.finditer(text)
    ]


# Funktionen vor einem Namen («Bundesrat Rösti», «conseillère nationale Funiciello»). Allein
# meinen «Bundesrat» oder «Nationalrat» das Gremium bzw. den Rat, nicht eine Person.
FUNCTION_WORDS = frozenset(
    {
        "bundesrat",
        "bundesratin",
        "bundesprasident",
        "bundesprasidentin",
        "vizeprasident",
        "vizeprasidentin",
        "nationalrat",
        "nationalratin",
        "standerat",
        "standeratin",
        "bundeskanzler",
        "bundeskanzlerin",
        "conseiller",
        "conseillere",
        "federal",
        "federale",
        "national",
        "nationale",
        "etats",
        "confederation",
        "president",
        "presidente",
        "chancelier",
        "chanceliere",
    }
)
