"""PII/PHI scrubber using Microsoft Presidio.

All entities are replaced with [REDACTED-{ENTITY_TYPE}] tokens.
Presidio engines are initialized lazily on first call so that importing
this module does not require a spaCy model to be installed.
"""

from __future__ import annotations

from presidio_anonymizer.entities import OperatorConfig

ENTITIES = [
    "PERSON",
    "DATE_TIME",
    "US_SSN",
    "US_ITIN",
    "PHONE_NUMBER",
    "EMAIL_ADDRESS",
    "LOCATION",
    "MEDICAL_LICENSE",
    "NPI",
]

_OPERATORS: dict[str, OperatorConfig] = {
    entity: OperatorConfig("replace", {"new_value": f"[REDACTED-{entity}]"})
    for entity in ENTITIES
}

_analyzer = None
_anonymizer = None


def _get_engines():
    global _analyzer, _anonymizer
    if _analyzer is None:
        from presidio_analyzer import AnalyzerEngine
        from presidio_anonymizer import AnonymizerEngine
        _analyzer = AnalyzerEngine()
        _anonymizer = AnonymizerEngine()
    return _analyzer, _anonymizer


def scrub(text: str, language: str = "en") -> str:
    """Return *text* with all PII/PHI entities replaced.

    Args:
        text: Raw document text.
        language: BCP-47 language code for the Presidio NLP engine.

    Returns:
        Scrubbed text with entity placeholders.
    """
    analyzer, anonymizer = _get_engines()
    results = analyzer.analyze(text=text, entities=ENTITIES, language=language)
    anonymized = anonymizer.anonymize(
        text=text,
        analyzer_results=results,
        operators=_OPERATORS,
    )
    return anonymized.text
