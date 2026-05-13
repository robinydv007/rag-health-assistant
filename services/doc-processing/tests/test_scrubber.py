"""Unit tests for the PII scrubber.

Presidio engines are mocked so these tests run without a spaCy model.
They verify: correct entities list, replacement pattern, and wrapper logic.
"""

from unittest.mock import MagicMock, patch

import src.scrubber as scrubber_module
from presidio_anonymizer.entities import EngineResult
from src.scrubber import _OPERATORS, ENTITIES, scrub


class TestScrubberConfig:
    def test_all_required_entities_declared(self):
        required = {
            "PERSON", "DATE_TIME", "US_SSN", "US_ITIN", "PHONE_NUMBER",
            "EMAIL_ADDRESS", "LOCATION", "MEDICAL_LICENSE", "NPI",
        }
        assert required <= set(ENTITIES)

    def test_replacement_pattern_format(self):
        for entity in ENTITIES:
            config = _OPERATORS[entity]
            assert config.operator_name == "replace"
            assert config.params["new_value"] == f"[REDACTED-{entity}]"


def _mock_engines(analyzer_return=None, anonymizer_return=None):
    """Return patched context with mocked Presidio engines."""
    mock_analyzer = MagicMock()
    mock_analyzer.analyze.return_value = analyzer_return or []

    mock_anonymizer = MagicMock()
    mock_anonymizer.anonymize.return_value = anonymizer_return or EngineResult(
        text="clean text", items=[]
    )

    return (
        patch.object(scrubber_module, "_analyzer", mock_analyzer),
        patch.object(scrubber_module, "_anonymizer", mock_anonymizer),
        mock_analyzer,
        mock_anonymizer,
    )


class TestScrubFunction:
    def test_scrub_calls_analyzer_with_all_entities(self):
        p1, p2, mock_analyzer, mock_anonymizer = _mock_engines()
        with p1, p2:
            scrub("John Smith visited on 2024-01-01")
        call_kwargs = mock_analyzer.analyze.call_args.kwargs
        assert set(call_kwargs["entities"]) == set(ENTITIES)
        assert call_kwargs["language"] == "en"

    def test_scrub_calls_anonymizer_with_operators(self):
        p1, p2, _, mock_anonymizer = _mock_engines()
        with p1, p2:
            result = scrub("Some text")
        assert mock_anonymizer.anonymize.called
        call_kwargs = mock_anonymizer.anonymize.call_args.kwargs
        assert "operators" in call_kwargs
        assert result == "clean text"

    def test_scrub_returns_anonymizer_output(self):
        output = EngineResult(
            text="[REDACTED-PERSON] was admitted on [REDACTED-DATE_TIME]", items=[]
        )
        p1, p2, _, _ = _mock_engines(anonymizer_return=output)
        with p1, p2:
            result = scrub("John Smith was admitted on 2024-01-01")
        assert "[REDACTED-PERSON]" in result
        assert "[REDACTED-DATE_TIME]" in result

    def test_scrub_no_pii_returns_clean_text(self):
        clean = "The patient presented with dyspnea and elevated BNP."
        output = EngineResult(text=clean, items=[])
        p1, p2, _, _ = _mock_engines(anonymizer_return=output)
        with p1, p2:
            result = scrub(clean)
        assert result == clean

    def test_scrub_passes_text_to_anonymizer(self):
        p1, p2, _, mock_anonymizer = _mock_engines()
        input_text = "Unique marker text 12345"
        with p1, p2:
            scrub(input_text)
        call_kwargs = mock_anonymizer.anonymize.call_args.kwargs
        assert call_kwargs["text"] == input_text
