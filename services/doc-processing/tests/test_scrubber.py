"""Unit tests for the PII scrubber.

Presidio's AnalyzerEngine and AnonymizerEngine are mocked so these tests
verify the wrapper logic (correct entities list, replacement pattern)
without requiring a spaCy model to be installed.
"""

from unittest.mock import MagicMock, patch

from presidio_analyzer import RecognizerResult
from presidio_anonymizer.entities import EngineResult

import src.scrubber as scrubber_module
from src.scrubber import ENTITIES, scrub


class TestScrubberConfig:
    def test_all_required_entities_declared(self):
        required = {
            "PERSON", "DATE_TIME", "US_SSN", "US_ITIN", "PHONE_NUMBER",
            "EMAIL_ADDRESS", "LOCATION", "MEDICAL_LICENSE", "NPI",
        }
        assert required <= set(ENTITIES)

    def test_replacement_pattern_format(self):
        from src.scrubber import _OPERATORS
        for entity in ENTITIES:
            config = _OPERATORS[entity]
            assert config.operator_name == "replace"
            assert config.params["new_value"] == f"[REDACTED-{entity}]"


class TestScrubFunction:
    def _mock_engines(self, detected_entities: list[str], text: str) -> tuple:
        """Return (mock_analyzer, mock_anonymizer) primed to simulate detection."""
        mock_analyzer = MagicMock()
        results = [
            RecognizerResult(entity_type=e, start=0, end=5, score=0.9)
            for e in detected_entities
        ]
        mock_analyzer.analyze.return_value = results

        mock_anonymizer = MagicMock()
        scrubbed = text
        for entity in detected_entities:
            scrubbed = scrubbed.replace(scrubbed[:5], f"[REDACTED-{entity}]", 1)
        mock_anonymizer.anonymize.return_value = EngineResult(
            text=f"[REDACTED-{detected_entities[0]}] is a patient" if detected_entities else text,
            items=[],
        )
        return mock_analyzer, mock_anonymizer

    def test_scrub_calls_analyzer_with_all_entities(self):
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = []
        mock_anonymizer = MagicMock()
        mock_anonymizer.anonymize.return_value = EngineResult(text="clean text", items=[])

        with (
            patch.object(scrubber_module, "_analyzer", mock_analyzer),
            patch.object(scrubber_module, "_anonymizer", mock_anonymizer),
        ):
            scrub("John Smith visited on 2024-01-01")

        call_kwargs = mock_analyzer.analyze.call_args.kwargs
        assert set(call_kwargs["entities"]) == set(ENTITIES)
        assert call_kwargs["language"] == "en"

    def test_scrub_calls_anonymizer_with_operators(self):
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = []
        mock_anonymizer = MagicMock()
        mock_anonymizer.anonymize.return_value = EngineResult(text="scrubbed", items=[])

        with (
            patch.object(scrubber_module, "_analyzer", mock_analyzer),
            patch.object(scrubber_module, "_anonymizer", mock_anonymizer),
        ):
            result = scrub("Some text")

        assert mock_anonymizer.anonymize.called
        call_kwargs = mock_anonymizer.anonymize.call_args.kwargs
        assert "operators" in call_kwargs
        assert result == "scrubbed"

    def test_scrub_returns_anonymizer_output(self):
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = []
        mock_anonymizer = MagicMock()
        mock_anonymizer.anonymize.return_value = EngineResult(
            text="[REDACTED-PERSON] was admitted on [REDACTED-DATE_TIME]", items=[]
        )

        with (
            patch.object(scrubber_module, "_analyzer", mock_analyzer),
            patch.object(scrubber_module, "_anonymizer", mock_anonymizer),
        ):
            result = scrub("John Smith was admitted on 2024-01-01")

        assert "[REDACTED-PERSON]" in result
        assert "[REDACTED-DATE_TIME]" in result

    def test_scrub_no_pii_returns_original(self):
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = []
        mock_anonymizer = MagicMock()
        clean = "The patient presented with dyspnea and elevated BNP."
        mock_anonymizer.anonymize.return_value = EngineResult(text=clean, items=[])

        with (
            patch.object(scrubber_module, "_analyzer", mock_analyzer),
            patch.object(scrubber_module, "_anonymizer", mock_anonymizer),
        ):
            result = scrub(clean)

        assert result == clean
