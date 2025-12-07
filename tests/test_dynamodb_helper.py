import pytest
from moto import mock_aws
import boto3
from datetime import datetime, timezone
from dynamodb_helper import DynamoDBHelper, DYNAMODB_MAX_ITEM_SIZE


@pytest.fixture
def dynamodb_tables():
    """Create mock DynamoDB tables for testing"""
    with mock_aws():
        # Create DynamoDB resource
        dynamodb = boto3.resource('dynamodb', region_name='ap-northeast-1')

        # Create phrases table
        phrases_table = dynamodb.create_table(
            TableName='english-phrases',
            KeySchema=[
                {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                {'AttributeName': 'phrase_id', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
                {'AttributeName': 'phrase_id', 'AttributeType': 'S'},
                {'AttributeName': 'created_at', 'AttributeType': 'S'},
                {'AttributeName': 'reviewed_at', 'AttributeType': 'S'},
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'UserCreatedIndex',
                    'KeySchema': [
                        {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                        {'AttributeName': 'created_at', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                },
                {
                    'IndexName': 'UserReviewIndex',
                    'KeySchema': [
                        {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                        {'AttributeName': 'reviewed_at', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )

        # Create corrections table
        corrections_table = dynamodb.create_table(
            TableName='english-corrections',
            KeySchema=[
                {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                {'AttributeName': 'correction_id', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
                {'AttributeName': 'correction_id', 'AttributeType': 'S'},
                {'AttributeName': 'created_at', 'AttributeType': 'S'},
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'UserCreatedIndex',
                    'KeySchema': [
                        {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                        {'AttributeName': 'created_at', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )

        yield dynamodb


@pytest.fixture
def db_helper(dynamodb_tables):
    """Create DynamoDBHelper instance with mocked DynamoDB"""
    return DynamoDBHelper(
        region_name='ap-northeast-1',
        dynamodb_resource=dynamodb_tables
    )


class TestSavePhrase:
    """Tests for save_phrase method"""

    def test_save_valid_phrase(self, db_helper):
        """Should successfully save a valid phrase"""
        result = db_helper.save_phrase(
            user_id='test_user',
            english='Hello',
            japanese='こんにちは',
            context='Greeting'
        )

        assert result['user_id'] == 'test_user'
        assert result['english'] == 'Hello'
        assert result['japanese'] == 'こんにちは'
        assert result['context'] == 'Greeting'
        assert 'phrase_id' in result
        assert 'created_at' in result
        assert result['query_count'] == 0

    def test_save_phrase_without_context(self, db_helper):
        """Should save phrase with empty context"""
        result = db_helper.save_phrase(
            user_id='test_user',
            english='Hello',
            japanese='こんにちは',
            context=''
        )

        assert result['context'] == ''

    def test_save_phrase_strips_whitespace(self, db_helper):
        """Should strip whitespace from inputs"""
        result = db_helper.save_phrase(
            user_id='test_user',
            english='  Hello  ',
            japanese='  こんにちは  ',
            context='  Greeting  '
        )

        assert result['english'] == 'Hello'
        assert result['japanese'] == 'こんにちは'
        assert result['context'] == 'Greeting'

    def test_save_phrase_enforces_item_size_limit(self, db_helper):
        """Should raise error when item exceeds DynamoDB limit"""
        # Create a phrase that would exceed 400KB when serialized
        huge_text = 'a' * (DYNAMODB_MAX_ITEM_SIZE + 1000)

        with pytest.raises(ValueError, match="Item size .* exceeds DynamoDB limit"):
            db_helper.save_phrase(
                user_id='test_user',
                english=huge_text,
                japanese='日本語',
                context=''
            )


class TestListPhrases:
    """Tests for list_phrases method"""

    def test_list_empty_phrases(self, db_helper):
        """Should return empty list when no phrases exist"""
        phrases = db_helper.list_phrases(user_id='test_user')
        assert phrases == []

    def test_list_phrases_returns_saved_phrases(self, db_helper):
        """Should return saved phrases"""
        # Save some phrases
        db_helper.save_phrase('test_user', 'Hello', 'こんにちは', '')
        db_helper.save_phrase('test_user', 'Goodbye', 'さようなら', '')

        phrases = db_helper.list_phrases(user_id='test_user')

        assert len(phrases) == 2
        assert any(p['english'] == 'Hello' for p in phrases)
        assert any(p['english'] == 'Goodbye' for p in phrases)

    def test_list_phrases_respects_limit(self, db_helper):
        """Should respect limit parameter"""
        # Save 5 phrases
        for i in range(5):
            db_helper.save_phrase('test_user', f'Phrase {i}', f'日本語 {i}', '')

        phrases = db_helper.list_phrases(user_id='test_user', limit=3)
        assert len(phrases) <= 3


class TestSearchPhrases:
    """Tests for search_phrases method"""

    def test_search_finds_matching_english(self, db_helper):
        """Should find phrases matching English text"""
        db_helper.save_phrase('test_user', 'Hello world', 'こんにちは世界', '')
        db_helper.save_phrase('test_user', 'Goodbye', 'さようなら', '')

        results = db_helper.search_phrases(user_id='test_user', keyword='Hello')

        assert len(results) == 1
        assert results[0]['english'] == 'Hello world'

    def test_search_finds_matching_japanese(self, db_helper):
        """Should find phrases matching Japanese text"""
        db_helper.save_phrase('test_user', 'Hello', 'こんにちは', '')
        db_helper.save_phrase('test_user', 'Goodbye', 'さようなら', '')

        results = db_helper.search_phrases(user_id='test_user', keyword='こんにちは')

        assert len(results) == 1
        assert results[0]['japanese'] == 'こんにちは'

    def test_search_is_case_insensitive(self, db_helper):
        """Should perform case-insensitive search"""
        db_helper.save_phrase('test_user', 'Hello World', 'こんにちは', '')

        results = db_helper.search_phrases(user_id='test_user', keyword='hello')
        assert len(results) == 1

    def test_search_respects_limit(self, db_helper):
        """Should respect limit parameter"""
        for i in range(5):
            db_helper.save_phrase('test_user', f'Hello {i}', '日本語', '')

        results = db_helper.search_phrases(user_id='test_user', keyword='Hello', limit=3)
        assert len(results) <= 3


class TestSaveCorrection:
    """Tests for save_correction method"""

    def test_save_valid_correction(self, db_helper):
        """Should successfully save a valid correction"""
        result = db_helper.save_correction(
            user_id='test_user',
            original_text='I goed to school',
            corrected_text='I went to school',
            feedback='Use went not goed',
            error_pattern='grammar'
        )

        assert result['user_id'] == 'test_user'
        assert result['original_text'] == 'I goed to school'
        assert result['corrected_text'] == 'I went to school'
        assert result['feedback'] == 'Use went not goed'
        assert result['error_pattern'] == 'grammar'
        assert 'correction_id' in result
        assert 'created_at' in result

    def test_save_correction_without_error_pattern(self, db_helper):
        """Should save correction with empty error pattern"""
        result = db_helper.save_correction(
            user_id='test_user',
            original_text='Original',
            corrected_text='Corrected',
            feedback='Feedback',
            error_pattern=''
        )

        assert result['error_pattern'] == ''

    def test_save_correction_enforces_item_size_limit(self, db_helper):
        """Should raise error when correction exceeds DynamoDB limit"""
        huge_text = 'a' * (DYNAMODB_MAX_ITEM_SIZE + 1000)

        with pytest.raises(ValueError, match="Item size .* exceeds DynamoDB limit"):
            db_helper.save_correction(
                user_id='test_user',
                original_text=huge_text,
                corrected_text='Corrected',
                feedback='Feedback',
                error_pattern=''
            )


class TestAnalyzeWeaknesses:
    """Tests for analyze_weaknesses method"""

    def test_analyze_with_no_corrections(self, db_helper):
        """Should return zero totals when no corrections exist"""
        analysis = db_helper.analyze_weaknesses(user_id='test_user')

        assert analysis['total_corrections'] == 0
        assert analysis['common_patterns'] == []
        assert analysis['recent_corrections'] == []

    def test_analyze_counts_error_patterns(self, db_helper):
        """Should count and sort error patterns"""
        db_helper.save_correction('test_user', 'orig1', 'corr1', 'fb1', 'grammar')
        db_helper.save_correction('test_user', 'orig2', 'corr2', 'fb2', 'grammar')
        db_helper.save_correction('test_user', 'orig3', 'corr3', 'fb3', 'spelling')

        analysis = db_helper.analyze_weaknesses(user_id='test_user')

        assert analysis['total_corrections'] == 3
        assert len(analysis['common_patterns']) == 2
        assert analysis['common_patterns'][0]['pattern'] == 'grammar'
        assert analysis['common_patterns'][0]['count'] == 2

    def test_analyze_returns_recent_corrections(self, db_helper):
        """Should return recent corrections"""
        for i in range(3):
            db_helper.save_correction(
                'test_user',
                f'original{i}',
                f'corrected{i}',
                f'feedback{i}',
                'grammar'
            )

        analysis = db_helper.analyze_weaknesses(user_id='test_user')

        assert len(analysis['recent_corrections']) <= 5
