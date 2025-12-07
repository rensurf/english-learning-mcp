import pytest
from unittest.mock import Mock, patch, MagicMock
from validators import ValidationError


# Mock the MCP handler decorators
@pytest.fixture(autouse=True)
def mock_mcp_handler():
    """Mock the MCP handler to avoid initialization issues"""
    with patch('lambda_function.mcp'):
        yield


@pytest.fixture
def mock_db():
    """Mock DynamoDBHelper"""
    with patch('lambda_function.db') as mock:
        yield mock


@pytest.fixture
def mock_validators():
    """Mock all validator functions"""
    with patch('lambda_function.validate_phrase_input'), \
         patch('lambda_function.validate_correction_input'), \
         patch('lambda_function.validate_search_keyword'), \
         patch('lambda_function.validate_limit') as mock_limit, \
         patch('lambda_function.validate_order') as mock_order:

        # Configure validate_limit and validate_order to return their input
        mock_limit.side_effect = lambda x: x
        mock_order.side_effect = lambda x: x

        yield


# Import after mocking
from lambda_function import (
    save_phrase,
    list_phrases,
    search_phrases,
    get_review_priority,
    save_correction,
    analyze_weaknesses
)


class TestSavePhrase:
    """Tests for save_phrase MCP tool"""

    def test_save_phrase_success(self, mock_db, mock_validators):
        """Should save phrase and return success message"""
        result = save_phrase("Hello", "こんにちは", "Greeting")

        assert "✅" in result
        assert "Hello" in result
        assert "こんにちは" in result
        mock_db.save_phrase.assert_called_once()

    def test_save_phrase_validation_error(self, mock_db):
        """Should return error message when validation fails"""
        with patch('lambda_function.validate_phrase_input', side_effect=ValidationError("English phrase cannot be empty")):
            result = save_phrase("", "こんにちは", "")

            assert "❌" in result
            assert "English phrase cannot be empty" in result
            mock_db.save_phrase.assert_not_called()

    def test_save_phrase_database_error(self, mock_db, mock_validators):
        """Should handle database errors gracefully"""
        mock_db.save_phrase.side_effect = Exception("Database error")

        result = save_phrase("Hello", "こんにちは", "")

        assert "❌" in result
        assert "Failed to save phrase" in result


class TestListPhrases:
    """Tests for list_phrases MCP tool"""

    def test_list_phrases_success(self, mock_db, mock_validators):
        """Should list phrases and return formatted text"""
        mock_db.list_phrases.return_value = [
            {'english': 'Hello', 'japanese': 'こんにちは', 'context': 'Greeting'},
            {'english': 'Goodbye', 'japanese': 'さようなら', 'context': ''}
        ]

        result = list_phrases(limit=50, order='desc')

        assert "Found 2 phrases" in result
        assert "Hello" in result
        assert "こんにちは" in result
        mock_db.list_phrases.assert_called_once()

    def test_list_phrases_empty(self, mock_db, mock_validators):
        """Should handle empty results"""
        mock_db.list_phrases.return_value = []

        result = list_phrases()

        assert "No phrases found" in result

    def test_list_phrases_validation_error(self, mock_db):
        """Should handle validation errors"""
        with patch('lambda_function.validate_limit', side_effect=ValidationError("Limit must be an integer")):
            result = list_phrases(limit="invalid")

            assert "❌" in result
            mock_db.list_phrases.assert_not_called()

    def test_list_phrases_shows_pagination(self, mock_db, mock_validators):
        """Should show pagination message when more than 20 results"""
        # Create 25 mock phrases
        mock_phrases = [
            {'english': f'Phrase {i}', 'japanese': f'日本語 {i}', 'context': ''}
            for i in range(25)
        ]
        mock_db.list_phrases.return_value = mock_phrases

        result = list_phrases()

        assert "Found 25 phrases" in result
        assert "... and 5 more phrases" in result


class TestSearchPhrases:
    """Tests for search_phrases MCP tool"""

    def test_search_phrases_success(self, mock_db, mock_validators):
        """Should search phrases and return matches"""
        mock_db.search_phrases.return_value = [
            {'english': 'Hello world', 'japanese': 'こんにちは世界', 'context': 'Greeting'}
        ]

        result = search_phrases("Hello", limit=20)

        assert "Found 1 matches for 'Hello'" in result
        assert "Hello world" in result
        mock_db.search_phrases.assert_called_once()

    def test_search_phrases_no_results(self, mock_db, mock_validators):
        """Should handle no search results"""
        mock_db.search_phrases.return_value = []

        result = search_phrases("nonexistent")

        assert "No phrases found matching 'nonexistent'" in result

    def test_search_phrases_validation_error(self, mock_db):
        """Should handle validation errors"""
        with patch('lambda_function.validate_search_keyword', side_effect=ValidationError("Search keyword cannot be empty")):
            result = search_phrases("")

            assert "❌" in result
            mock_db.search_phrases.assert_not_called()


class TestGetReviewPriority:
    """Tests for get_review_priority MCP tool"""

    def test_get_review_priority_success(self, mock_db, mock_validators):
        """Should return phrases needing review"""
        mock_db.get_review_priority.return_value = [
            {'english': 'Hello', 'japanese': 'こんにちは', 'query_count': 5, 'context': ''}
        ]

        result = get_review_priority(limit=20)

        assert "📚 1 phrases need review" in result
        assert "Hello" in result
        assert "Queried: 5 times" in result

    def test_get_review_priority_empty(self, mock_db, mock_validators):
        """Should handle no phrases needing review"""
        mock_db.get_review_priority.return_value = []

        result = get_review_priority()

        assert "No phrases need review. Great job!" in result


class TestSaveCorrection:
    """Tests for save_correction MCP tool"""

    def test_save_correction_success(self, mock_db, mock_validators):
        """Should save correction and return formatted message"""
        result = save_correction(
            "I goed to school",
            "I went to school",
            "Use went not goed",
            "grammar"
        )

        assert "✅ Correction saved" in result
        assert "Before: I goed to school" in result
        assert "After: I went to school" in result
        assert "Feedback: Use went not goed" in result
        assert "Error type: grammar" in result
        mock_db.save_correction.assert_called_once()

    def test_save_correction_without_error_pattern(self, mock_db, mock_validators):
        """Should save correction without error pattern"""
        result = save_correction(
            "Original",
            "Corrected",
            "Feedback",
            ""
        )

        assert "✅ Correction saved" in result
        assert "Error type:" not in result

    def test_save_correction_validation_error(self, mock_db):
        """Should handle validation errors"""
        with patch('lambda_function.validate_correction_input', side_effect=ValidationError("Original text cannot be empty")):
            result = save_correction("", "Corrected", "Feedback")

            assert "❌" in result
            mock_db.save_correction.assert_not_called()


class TestAnalyzeWeaknesses:
    """Tests for analyze_weaknesses MCP tool"""

    def test_analyze_weaknesses_success(self, mock_db, mock_validators):
        """Should analyze and return weakness analysis"""
        mock_db.analyze_weaknesses.return_value = {
            'total_corrections': 5,
            'common_patterns': [
                {'pattern': 'grammar', 'count': 3},
                {'pattern': 'spelling', 'count': 2}
            ],
            'recent_corrections': [
                {'original_text': 'I goed', 'corrected_text': 'I went'}
            ]
        }

        result = analyze_weaknesses(limit=10)

        assert "📊 Weakness Analysis" in result
        assert "Total corrections: 5" in result
        assert "grammar: 3 times" in result
        assert "spelling: 2 times" in result
        assert "I goed → I went" in result

    def test_analyze_weaknesses_no_data(self, mock_db, mock_validators):
        """Should handle no corrections data"""
        mock_db.analyze_weaknesses.return_value = {
            'total_corrections': 0,
            'common_patterns': [],
            'recent_corrections': []
        }

        result = analyze_weaknesses()

        assert "Total corrections: 0" in result
