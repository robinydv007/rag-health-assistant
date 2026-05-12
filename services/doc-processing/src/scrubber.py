"""PII/PHI scrubber using Microsoft Presidio.

All entities are replaced with [REDACTED-{ENTITY_TYPE}] tokens.
The replacement pattern is deterministic so downstream systems can detect
redacted spans if needed.
"""

from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
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

_analyzer = AnalyzerEngine()
_anonymizer = AnonymizerEngine()

_OPERATORS: dict[str, OperatorConfig] = {
    entity: OperatorConfig("replace", {"new_value": f"[REDACTED-{entity}]"})
    for entity in ENTITIES
}


def scrub(text: str, language: str = "en") -> str:
    """Return *text* with all PII/PHI entities replaced.

    Args:
        text: Raw document text.
        language: BCP-47 language code for the Presidio NLP engine.

    Returns:
        Scrubbed text with entity placeholders.
    """
    results = _analyzer.analyze(text=text, entities=ENTITIES, language=language)
    anonymized = _anonymizer.anonymize(
        text=text,
        analyzer_results=results,
        operators=_OPERATORS,
    )
    return anonymized.text
