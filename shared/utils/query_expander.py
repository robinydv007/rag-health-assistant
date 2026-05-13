"""Medical query expander using a static synonym dictionary.

Loads shared/data/medical_synonyms.yaml at import time and builds a flat
lookup from every term (abbreviation + all synonyms) to its synonym list.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

_SYNONYMS_PATH = Path(__file__).parent.parent / "data" / "medical_synonyms.yaml"

# Build a single flat lookup: term → list[synonym] (case-insensitive match).
# Entry key is always lowercase; values are the original-case synonyms.
_LOOKUP: dict[str, list[str]] = {}


def _load() -> None:
    with open(_SYNONYMS_PATH, encoding="utf-8") as f:
        raw: dict[str, list[str]] = yaml.safe_load(f)

    for primary, synonyms in raw.items():
        all_terms = [primary] + synonyms
        for term in all_terms:
            key = term.lower()
            # Union all siblings into the expansion set for this key
            other = [t for t in all_terms if t.lower() != key]
            existing = _LOOKUP.get(key, [])
            _LOOKUP[key] = list(dict.fromkeys(existing + other))  # dedup, order-stable


_load()


def expand(query: str) -> list[str]:
    """Return synonym expansion terms for *query*.

    Tokenises the query on word boundaries, looks up each token and
    each consecutive 2-token phrase, and returns a deduplicated list of
    expansion terms to append to the search. The original query is NOT
    included in the return value — callers append it themselves.

    Args:
        query: The raw user question string.

    Returns:
        A list of additional search terms derived from synonyms.
        Empty list if no known medical terms are found.
    """
    tokens = re.findall(r"[\w/]+", query)
    expansions: list[str] = []
    seen: set[str] = set()

    candidates = list(tokens)
    # Also try bigrams (e.g. "ACE inhibitor")
    candidates += [f"{tokens[i]} {tokens[i+1]}" for i in range(len(tokens) - 1)]

    for candidate in candidates:
        key = candidate.lower()
        for synonym in _LOOKUP.get(key, []):
            if synonym not in seen:
                seen.add(synonym)
                expansions.append(synonym)

    return expansions
