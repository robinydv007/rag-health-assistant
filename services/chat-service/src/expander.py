"""Query expansion wrapper for the Chat Service.

Delegates to shared.utils.query_expander which loads the medical synonym
dictionary at import time.
"""

from shared.utils.query_expander import expand as _expand


def expand_query(question: str) -> tuple[str, list[str]]:
    """Expand *question* with medical synonyms.

    Returns:
        Tuple of (original_question, synonym_terms).
        synonym_terms is a (possibly empty) list of additional search terms.
    """
    return question, _expand(question)
