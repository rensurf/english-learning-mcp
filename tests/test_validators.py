import pytest
from validators import (
    validate_phrase_input,
    validate_correction_input,
    validate_search_keyword,
    validate_limit,
    validate_order,
    ValidationError,
    MAX_PHRASE_LENGTH,
    MAX_CONTEXT_LENGTH,
    MAX_FEEDBACK_LENGTH,
    MAX_ERROR_PATTERN_LENGTH,
    MAX_QUERY_LIMIT,
)


class TestValidatePhraseInput:
    """Tests for validate_phrase_input function"""

    def test_valid_phrase(self):
        """Should pass for valid phrase input"""
        # Should not raise any exception
        validate_phrase_input("Hello", "こんにちは", "Greeting")

    def test_valid_phrase_without_context(self):
        """Should pass for valid phrase without context"""
        validate_phrase_input("Hello", "こんにちは", "")

    def test_empty_english_raises_error(self):
        """Should raise ValidationError for empty English phrase"""
        with pytest.raises(ValidationError, match="English phrase cannot be empty"):
            validate_phrase_input("", "こんにちは", "")

    def test_whitespace_only_english_raises_error(self):
        """Should raise ValidationError for whitespace-only English"""
        with pytest.raises(ValidationError, match="English phrase cannot be empty"):
            validate_phrase_input("   ", "こんにちは", "")

    def test_empty_japanese_raises_error(self):
        """Should raise ValidationError for empty Japanese translation"""
        with pytest.raises(ValidationError, match="Japanese translation cannot be empty"):
            validate_phrase_input("Hello", "", "")

    def test_whitespace_only_japanese_raises_error(self):
        """Should raise ValidationError for whitespace-only Japanese"""
        with pytest.raises(ValidationError, match="Japanese translation cannot be empty"):
            validate_phrase_input("Hello", "   ", "")

    def test_english_too_long_raises_error(self):
        """Should raise ValidationError when English exceeds max length"""
        long_english = "a" * (MAX_PHRASE_LENGTH + 1)
        with pytest.raises(ValidationError, match="English phrase is too long"):
            validate_phrase_input(long_english, "日本語", "")

    def test_japanese_too_long_raises_error(self):
        """Should raise ValidationError when Japanese exceeds max length"""
        long_japanese = "あ" * (MAX_PHRASE_LENGTH + 1)
        with pytest.raises(ValidationError, match="Japanese translation is too long"):
            validate_phrase_input("English", long_japanese, "")

    def test_context_too_long_raises_error(self):
        """Should raise ValidationError when context exceeds max length"""
        long_context = "a" * (MAX_CONTEXT_LENGTH + 1)
        with pytest.raises(ValidationError, match="Context is too long"):
            validate_phrase_input("Hello", "こんにちは", long_context)

    def test_max_length_phrases_pass(self):
        """Should pass for phrases at exactly max length"""
        max_english = "a" * MAX_PHRASE_LENGTH
        max_japanese = "あ" * MAX_PHRASE_LENGTH
        max_context = "c" * MAX_CONTEXT_LENGTH
        validate_phrase_input(max_english, max_japanese, max_context)


class TestValidateCorrectionInput:
    """Tests for validate_correction_input function"""

    def test_valid_correction(self):
        """Should pass for valid correction input"""
        validate_correction_input(
            "I goed to school",
            "I went to school",
            "Use 'went' not 'goed'",
            "grammar"
        )

    def test_valid_correction_without_error_pattern(self):
        """Should pass for valid correction without error pattern"""
        validate_correction_input(
            "I goed to school",
            "I went to school",
            "Use 'went' not 'goed'",
            ""
        )

    def test_empty_original_text_raises_error(self):
        """Should raise ValidationError for empty original text"""
        with pytest.raises(ValidationError, match="Original text cannot be empty"):
            validate_correction_input("", "Corrected", "Feedback", "")

    def test_empty_corrected_text_raises_error(self):
        """Should raise ValidationError for empty corrected text"""
        with pytest.raises(ValidationError, match="Corrected text cannot be empty"):
            validate_correction_input("Original", "", "Feedback", "")

    def test_empty_feedback_raises_error(self):
        """Should raise ValidationError for empty feedback"""
        with pytest.raises(ValidationError, match="Feedback cannot be empty"):
            validate_correction_input("Original", "Corrected", "", "")

    def test_original_text_too_long_raises_error(self):
        """Should raise ValidationError when original text exceeds max length"""
        long_text = "a" * (MAX_FEEDBACK_LENGTH + 1)
        with pytest.raises(ValidationError, match="Original text is too long"):
            validate_correction_input(long_text, "Corrected", "Feedback", "")

    def test_corrected_text_too_long_raises_error(self):
        """Should raise ValidationError when corrected text exceeds max length"""
        long_text = "a" * (MAX_FEEDBACK_LENGTH + 1)
        with pytest.raises(ValidationError, match="Corrected text is too long"):
            validate_correction_input("Original", long_text, "Feedback", "")

    def test_feedback_too_long_raises_error(self):
        """Should raise ValidationError when feedback exceeds max length"""
        long_feedback = "a" * (MAX_FEEDBACK_LENGTH + 1)
        with pytest.raises(ValidationError, match="Feedback is too long"):
            validate_correction_input("Original", "Corrected", long_feedback, "")

    def test_error_pattern_too_long_raises_error(self):
        """Should raise ValidationError when error pattern exceeds max length"""
        long_pattern = "a" * (MAX_ERROR_PATTERN_LENGTH + 1)
        with pytest.raises(ValidationError, match="Error pattern is too long"):
            validate_correction_input("Original", "Corrected", "Feedback", long_pattern)


class TestValidateSearchKeyword:
    """Tests for validate_search_keyword function"""

    def test_valid_keyword(self):
        """Should pass for valid keyword"""
        validate_search_keyword("hello")

    def test_empty_keyword_raises_error(self):
        """Should raise ValidationError for empty keyword"""
        with pytest.raises(ValidationError, match="Search keyword cannot be empty"):
            validate_search_keyword("")

    def test_whitespace_only_keyword_raises_error(self):
        """Should raise ValidationError for whitespace-only keyword"""
        with pytest.raises(ValidationError, match="Search keyword cannot be empty"):
            validate_search_keyword("   ")

    def test_keyword_too_long_raises_error(self):
        """Should raise ValidationError when keyword exceeds max length"""
        long_keyword = "a" * 201
        with pytest.raises(ValidationError, match="Search keyword is too long"):
            validate_search_keyword(long_keyword)


class TestValidateLimit:
    """Tests for validate_limit function"""

    def test_valid_limit(self):
        """Should return valid limit unchanged"""
        assert validate_limit(50) == 50

    def test_limit_zero_raises_error(self):
        """Should raise ValidationError for zero limit"""
        with pytest.raises(ValidationError, match="Limit must be at least 1"):
            validate_limit(0)

    def test_limit_above_maximum_returns_maximum(self):
        """Should return maximum limit when above MAX_QUERY_LIMIT"""
        assert validate_limit(MAX_QUERY_LIMIT + 1) == MAX_QUERY_LIMIT
        assert validate_limit(1000) == MAX_QUERY_LIMIT

    def test_limit_at_boundaries(self):
        """Should accept limits at exact boundaries"""
        assert validate_limit(1) == 1
        assert validate_limit(MAX_QUERY_LIMIT) == MAX_QUERY_LIMIT

    def test_non_integer_limit_raises_error(self):
        """Should raise ValidationError for non-integer limit"""
        with pytest.raises(ValidationError, match="Limit must be an integer"):
            validate_limit("50")

    def test_negative_limit_raises_error(self):
        """Should raise ValidationError for negative limit"""
        with pytest.raises(ValidationError, match="Limit must be at least 1"):
            validate_limit(-1)


class TestValidateOrder:
    """Tests for validate_order function"""

    def test_valid_asc_order(self):
        """Should return 'asc' for valid ascending order"""
        assert validate_order('asc') == 'asc'

    def test_valid_desc_order(self):
        """Should return 'desc' for valid descending order"""
        assert validate_order('desc') == 'desc'

    def test_invalid_order_returns_default_desc(self):
        """Should return 'desc' for invalid order values"""
        assert validate_order('invalid') == 'desc'
        assert validate_order('ASC') == 'desc'
        assert validate_order('') == 'desc'
        assert validate_order('random') == 'desc'
