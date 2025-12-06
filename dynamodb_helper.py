"""
DynamoDB helper for English Learning MCP
"""
import boto3
import uuid
from datetime import datetime
from typing import List, Dict, Optional
from decimal import Decimal


class DynamoDBHelper:
    def __init__(self, region_name: str = "ap-northeast-1"):
        self.dynamodb = boto3.resource('dynamodb', region_name=region_name)
        self.phrases_table = self.dynamodb.Table('english-phrases')
        self.corrections_table = self.dynamodb.Table('english-corrections')
    
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
        """Save a new phrase"""
        phrase_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        item = {
            'user_id': user_id,
            'phrase_id': phrase_id,
            'english': english,
            'japanese': japanese,
            'context': context,
            'created_at': now,
            'query_count': 0,
            'last_queried_at': None,
            'reviewed_at': now
        }
        
        self.phrases_table.put_item(Item=item)
        return item
    
    def list_phrases(
        self, 
        user_id: str, 
        limit: int = 50, 
        order: str = 'desc'
    ) -> List[Dict]:
        """List phrases ordered by creation date"""
        response = self.phrases_table.query(
            IndexName='UserCreatedIndex',
            KeyConditionExpression='user_id = :uid',
            ExpressionAttributeValues={':uid': user_id},
            ScanIndexForward=(order == 'asc'),
            Limit=limit
        )
        return self._decimal_to_int(response.get('Items', []))
    
    def search_phrases(
        self, 
        user_id: str, 
        keyword: str, 
        limit: int = 20
    ) -> List[Dict]:
        """Search phrases by keyword"""
        response = self.phrases_table.query(
            KeyConditionExpression='user_id = :uid',
            ExpressionAttributeValues={':uid': user_id}
        )
        
        items = response.get('Items', [])
        keyword_lower = keyword.lower()
        
        # Filter by keyword
        matches = []
        for item in items:
            if (keyword_lower in item.get('english', '').lower() or
                keyword_lower in item.get('japanese', '').lower() or
                keyword_lower in item.get('context', '').lower()):
                
                # Increment query_count
                self.phrases_table.update_item(
                    Key={
                        'user_id': item['user_id'],
                        'phrase_id': item['phrase_id']
                    },
                    UpdateExpression='SET query_count = query_count + :inc, last_queried_at = :now',
                    ExpressionAttributeValues={
                        ':inc': 1,
                        ':now': datetime.utcnow().isoformat()
                    }
                )
                
                matches.append(item)
                if len(matches) >= limit:
                    break
        
        return self._decimal_to_int(matches)
    
    def get_review_priority(self, user_id: str, limit: int = 20) -> List[Dict]:
        """Get phrases that need review"""
        response = self.phrases_table.query(
            IndexName='UserReviewIndex',
            KeyConditionExpression='user_id = :uid',
            ExpressionAttributeValues={':uid': user_id},
            ScanIndexForward=True,  # Oldest reviewed_at first (null values come first)
            Limit=limit * 2  # Get more to filter
        )
        
        items = response.get('Items', [])
        
        # Prioritize: never reviewed > old reviewed_at > high query_count
        never_reviewed = [i for i in items if not i.get('reviewed_at')]
        old_reviewed = [i for i in items if i.get('reviewed_at')]
        
        # Sort by query_count for never_reviewed items
        never_reviewed.sort(key=lambda x: x.get('query_count', 0), reverse=True)
        
        result = (never_reviewed + old_reviewed)[:limit]
        return self._decimal_to_int(result)
    
    # Corrections operations
    def save_correction(
        self,
        user_id: str,
        original_text: str,
        corrected_text: str,
        feedback: str,
        error_pattern: str = ""
    ) -> Dict:
        """Save a correction"""
        correction_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        item = {
            'user_id': user_id,
            'correction_id': correction_id,
            'original_text': original_text,
            'corrected_text': corrected_text,
            'feedback': feedback,
            'error_pattern': error_pattern,
            'created_at': now,
            'reviewed_at': now
        }
        
        self.corrections_table.put_item(Item=item)
        return item
    
    def list_corrections(
        self,
        user_id: str,
        limit: int = 50,
        order: str = 'desc'
    ) -> List[Dict]:
        """List corrections ordered by creation date"""
        response = self.corrections_table.query(
            IndexName='UserCreatedIndex',
            KeyConditionExpression='user_id = :uid',
            ExpressionAttributeValues={':uid': user_id},
            ScanIndexForward=(order == 'asc'),
            Limit=limit
        )
        return self._decimal_to_int(response.get('Items', []))
    
    def analyze_weaknesses(self, user_id: str, limit: int = 10) -> Dict:
        """Analyze common error patterns"""
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
        
        return {
            'total_corrections': len(items),
            'common_patterns': [
                {'pattern': p, 'count': c} for p, c in sorted_patterns
            ],
            'recent_corrections': self._decimal_to_int(
                sorted(items, key=lambda x: x['created_at'], reverse=True)[:5]
            )
        }