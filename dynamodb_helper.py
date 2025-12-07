import boto3
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict
from decimal import Decimal
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Constants
PHRASES_TABLE_NAME = 'english-phrases'
CORRECTIONS_TABLE_NAME = 'english-corrections'

# DynamoDB limits (data integrity constraints)
DYNAMODB_MAX_ITEM_SIZE = 400_000  # 400KB DynamoDB item size limit


class DynamoDBHelper:
    """Helper class for DynamoDB operations on phrases and corrections tables.

    Provides CRUD operations with input validation, error handling, and logging.
    Supports dependency injection for testability.
    """

    def __init__(
        self,
        region_name: str = "ap-northeast-1",
        dynamodb_resource=None,
        phrases_table_name: str = PHRASES_TABLE_NAME,
        corrections_table_name: str = CORRECTIONS_TABLE_NAME
    ):
        """Initialize DynamoDB helper.

        Args:
            region_name: AWS region name
            dynamodb_resource: Optional DynamoDB resource for dependency injection (for testing)
            phrases_table_name: Name of phrases table
            corrections_table_name: Name of corrections table
        """
        self.dynamodb = dynamodb_resource or boto3.resource('dynamodb', region_name=region_name)
        self.phrases_table = self.dynamodb.Table(phrases_table_name)
        self.corrections_table = self.dynamodb.Table(corrections_table_name)
        logger.info(f"DynamoDBHelper initialized with region: {region_name}")
    
    def _decimal_to_int(self, obj):
        """Convert Decimal to int for JSON serialization"""
        if isinstance(obj, Decimal):
            return int(obj)
        elif isinstance(obj, dict):
            return {k: self._decimal_to_int(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._decimal_to_int(i) for i in obj]
        return obj
    
    # Phrases operations
    def save_phrase(
        self,
        user_id: str,
        english: str,
        japanese: str,
        context: str = ""
    ) -> Dict:
        """Save a new phrase to DynamoDB.

        Note: Caller should validate inputs using validators.py before calling.
        This method only enforces data integrity constraints (DynamoDB limits).

        Args:
            user_id: User identifier
            english: English phrase
            japanese: Japanese translation
            context: Optional usage context or example sentence

        Returns:
            Dict containing the saved item with phrase_id and timestamps

        Raises:
            ValueError: If data integrity constraints are violated
            Exception: If DynamoDB operation fails
        """
        phrase_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        item = {
            'user_id': user_id,
            'phrase_id': phrase_id,
            'english': english.strip(),
            'japanese': japanese.strip(),
            'context': context.strip() if context else "",
            'created_at': now,
            'query_count': 0,
            'last_queried_at': None,
            'reviewed_at': now
        }

        # Data integrity check: DynamoDB item size limit
        item_size = len(str(item))
        if item_size > DYNAMODB_MAX_ITEM_SIZE:
            raise ValueError(f"Item size ({item_size} bytes) exceeds DynamoDB limit")

        try:
            self.phrases_table.put_item(Item=item)
            logger.info(f"Saved phrase: {phrase_id} for user: {user_id}")
            return item
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"DynamoDB error saving phrase: {error_code} - {e}")
            raise Exception(f"Failed to save phrase: {error_code}")
        except Exception as e:
            logger.error(f"Unexpected error saving phrase: {e}")
            raise Exception(f"Failed to save phrase: {str(e)}")
    
    def list_phrases(
        self,
        user_id: str,
        limit: int = 50,
        order: str = 'desc'
    ) -> List[Dict]:
        """List phrases ordered by creation date.

        Note: Caller should validate inputs using validators.py before calling.

        Args:
            user_id: User identifier
            limit: Maximum number of phrases to return
            order: Sort order - 'asc' or 'desc'

        Returns:
            List of phrase dictionaries

        Raises:
            Exception: If DynamoDB operation fails
        """
        try:
            response = self.phrases_table.query(
                IndexName='UserCreatedIndex',
                KeyConditionExpression='user_id = :uid',
                ExpressionAttributeValues={':uid': user_id},
                ScanIndexForward=(order == 'asc'),
                Limit=limit
            )
            items = self._decimal_to_int(response.get('Items', []))
            logger.info(f"Listed {len(items)} phrases for user: {user_id}")
            return items
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"DynamoDB error listing phrases: {error_code} - {e}")
            raise Exception(f"Failed to list phrases: {error_code}")
        except Exception as e:
            logger.error(f"Unexpected error listing phrases: {e}")
            raise Exception(f"Failed to list phrases: {str(e)}")
    
    def search_phrases(
        self,
        user_id: str,
        keyword: str,
        limit: int = 20
    ) -> List[Dict]:
        """Search phrases by keyword.

        Note: Caller should validate inputs using validators.py before calling.
        This performs a table scan which may be expensive for large datasets.
        For production use with large datasets, consider using Amazon OpenSearch.

        Args:
            user_id: User identifier
            keyword: Search keyword (searches English, Japanese, and context fields)
            limit: Maximum number of results

        Returns:
            List of matching phrase dictionaries

        Raises:
            Exception: If DynamoDB operation fails
        """
        keyword_lower = keyword.lower()

        try:
            # Use query (not scan) to limit to user's data
            response = self.phrases_table.query(
                KeyConditionExpression='user_id = :uid',
                ExpressionAttributeValues={':uid': user_id}
            )

            items = response.get('Items', [])

            # Filter by keyword in Python (performance optimization needed for large datasets)
            matches = []
            for item in items:
                if (keyword_lower in item.get('english', '').lower() or
                    keyword_lower in item.get('japanese', '').lower() or
                    keyword_lower in item.get('context', '').lower()):

                    matches.append(item)

                    # Update query statistics asynchronously in production
                    try:
                        self.phrases_table.update_item(
                            Key={
                                'user_id': item['user_id'],
                                'phrase_id': item['phrase_id']
                            },
                            UpdateExpression='SET query_count = query_count + :inc, last_queried_at = :now',
                            ExpressionAttributeValues={
                                ':inc': 1,
                                ':now': datetime.now(timezone.utc).isoformat()
                            }
                        )
                    except ClientError as e:
                        # Log but don't fail search if update fails
                        logger.warning(f"Failed to update query count for {item['phrase_id']}: {e}")

                    if len(matches) >= limit:
                        break

            logger.info(f"Found {len(matches)} matches for keyword '{keyword}' (user: {user_id})")
            return self._decimal_to_int(matches)

        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"DynamoDB error searching phrases: {error_code} - {e}")
            raise Exception(f"Failed to search phrases: {error_code}")
        except Exception as e:
            logger.error(f"Unexpected error searching phrases: {e}")
            raise Exception(f"Failed to search phrases: {str(e)}")
    
    def get_review_priority(self, user_id: str, limit: int = 20) -> List[Dict]:
        """Get phrases that need review, prioritized by staleness.

        Note: Caller should validate inputs using validators.py before calling.
        Prioritization: never reviewed > old reviewed_at > high query_count

        Args:
            user_id: User identifier
            limit: Maximum number of phrases to return

        Returns:
            List of phrase dictionaries sorted by review priority

        Raises:
            Exception: If DynamoDB operation fails
        """
        try:
            response = self.phrases_table.query(
                IndexName='UserReviewIndex',
                KeyConditionExpression='user_id = :uid',
                ExpressionAttributeValues={':uid': user_id},
                ScanIndexForward=True,  # Oldest reviewed_at first (null values come first)
                Limit=limit * 2  # Get more to filter and sort
            )

            items = response.get('Items', [])

            # Prioritize: never reviewed > old reviewed_at > high query_count
            never_reviewed = [i for i in items if not i.get('reviewed_at')]
            old_reviewed = [i for i in items if i.get('reviewed_at')]

            # Sort by query_count for never_reviewed items
            never_reviewed.sort(key=lambda x: x.get('query_count', 0), reverse=True)

            result = (never_reviewed + old_reviewed)[:limit]
            logger.info(f"Retrieved {len(result)} phrases for review (user: {user_id})")
            return self._decimal_to_int(result)

        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"DynamoDB error getting review priority: {error_code} - {e}")
            raise Exception(f"Failed to get review priority: {error_code}")
        except Exception as e:
            logger.error(f"Unexpected error getting review priority: {e}")
            raise Exception(f"Failed to get review priority: {str(e)}")
    
    # Corrections operations
    def save_correction(
        self,
        user_id: str,
        original_text: str,
        corrected_text: str,
        feedback: str,
        error_pattern: str = ""
    ) -> Dict:
        """Save an English correction to DynamoDB.

        Note: Caller should validate inputs using validators.py before calling.
        This method only enforces data integrity constraints (DynamoDB limits).

        Args:
            user_id: User identifier
            original_text: Original (incorrect) text
            corrected_text: Corrected text
            feedback: Explanation of the correction
            error_pattern: Optional error type (e.g., 'grammar', 'tense', 'spelling')

        Returns:
            Dict containing the saved item with correction_id and timestamps

        Raises:
            ValueError: If data integrity constraints are violated
            Exception: If DynamoDB operation fails
        """
        correction_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        item = {
            'user_id': user_id,
            'correction_id': correction_id,
            'original_text': original_text.strip(),
            'corrected_text': corrected_text.strip(),
            'feedback': feedback.strip(),
            'error_pattern': error_pattern.strip() if error_pattern else "",
            'created_at': now,
            'reviewed_at': now
        }

        # Data integrity check: DynamoDB item size limit
        item_size = len(str(item))
        if item_size > DYNAMODB_MAX_ITEM_SIZE:
            raise ValueError(f"Item size ({item_size} bytes) exceeds DynamoDB limit")

        try:
            self.corrections_table.put_item(Item=item)
            logger.info(f"Saved correction: {correction_id} for user: {user_id}")
            return item
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"DynamoDB error saving correction: {error_code} - {e}")
            raise Exception(f"Failed to save correction: {error_code}")
        except Exception as e:
            logger.error(f"Unexpected error saving correction: {e}")
            raise Exception(f"Failed to save correction: {str(e)}")
    
    def list_corrections(
        self,
        user_id: str,
        limit: int = 50,
        order: str = 'desc'
    ) -> List[Dict]:
        """List corrections ordered by creation date.

        Note: Caller should validate inputs using validators.py before calling.

        Args:
            user_id: User identifier
            limit: Maximum number of corrections to return
            order: Sort order - 'asc' or 'desc'

        Returns:
            List of correction dictionaries

        Raises:
            Exception: If DynamoDB operation fails
        """
        try:
            response = self.corrections_table.query(
                IndexName='UserCreatedIndex',
                KeyConditionExpression='user_id = :uid',
                ExpressionAttributeValues={':uid': user_id},
                ScanIndexForward=(order == 'asc'),
                Limit=limit
            )
            items = self._decimal_to_int(response.get('Items', []))
            logger.info(f"Listed {len(items)} corrections for user: {user_id}")
            return items
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"DynamoDB error listing corrections: {error_code} - {e}")
            raise Exception(f"Failed to list corrections: {error_code}")
        except Exception as e:
            logger.error(f"Unexpected error listing corrections: {e}")
            raise Exception(f"Failed to list corrections: {str(e)}")
    
    def analyze_weaknesses(self, user_id: str, limit: int = 10) -> Dict:
        """Analyze common error patterns from corrections.

        Note: Caller should validate inputs using validators.py before calling.

        Args:
            user_id: User identifier
            limit: Maximum number of top patterns to return

        Returns:
            Dict containing:
                - total_corrections: Total number of corrections
                - common_patterns: List of {pattern, count} sorted by frequency
                - recent_corrections: Last 5 corrections

        Raises:
            Exception: If DynamoDB operation fails
        """
        try:
            response = self.corrections_table.query(
                KeyConditionExpression='user_id = :uid',
                ExpressionAttributeValues={':uid': user_id}
            )

            items = response.get('Items', [])

            # Count error patterns
            pattern_counts = {}
            for item in items:
                pattern = item.get('error_pattern', '').strip()
                if pattern:
                    pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1

            # Sort by frequency
            sorted_patterns = sorted(
                pattern_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:limit]

            result = {
                'total_corrections': len(items),
                'common_patterns': [
                    {'pattern': p, 'count': c} for p, c in sorted_patterns
                ],
                'recent_corrections': self._decimal_to_int(
                    sorted(items, key=lambda x: x['created_at'], reverse=True)[:5]
                )
            }

            logger.info(f"Analyzed {len(items)} corrections for user: {user_id}")
            return result

        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"DynamoDB error analyzing weaknesses: {error_code} - {e}")
            raise Exception(f"Failed to analyze weaknesses: {error_code}")
        except Exception as e:
            logger.error(f"Unexpected error analyzing weaknesses: {e}")
            raise Exception(f"Failed to analyze weaknesses: {str(e)}")