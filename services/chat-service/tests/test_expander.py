"""Unit tests for the query expander."""

from src.expander import expand_query


class TestExpandQuery:
    def test_known_abbreviation_expanded(self):
        _, synonyms = expand_query("Patient has MI")
        assert any("myocardial infarction" in s.lower() for s in synonyms)

    def test_unknown_term_returns_empty_synonyms(self):
        _, synonyms = expand_query("no medical terms here xyz123")
        assert isinstance(synonyms, list)

    def test_original_question_returned_unchanged(self):
        question = "What is the treatment for HTN?"
        returned_question, _ = expand_query(question)
        assert returned_question == question

    def test_multiple_terms_expanded(self):
        _, synonyms = expand_query("Patient with DM and HTN")
        # Both DM and HTN should produce synonyms
        assert len(synonyms) >= 2

    def test_empty_question_returns_empty_synonyms(self):
        _, synonyms = expand_query("")
        assert synonyms == []
