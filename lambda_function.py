import json
import os
from typing import Any, Dict, List
from dynamodb_helper import DynamoDBHelper


# Initialize DynamoDB helper
db = DynamoDBHelper(region_name=os.environ.get('AWS_REGION', 'ap-northeast-1'))
DEFAULT_USER_ID = os.environ.get('DEFAULT_USER_ID', 'default_user')


def create_response(status_code: int, body: Dict) -> Dict:
    """Create Lambda response"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        },
        'body': json.dumps(body, ensure_ascii=False)
    }


def handle_tool_call(tool_name: str, arguments: Dict) -> Dict:
    """Handle MCP tool calls"""
    user_id = arguments.get('user_id', DEFAULT_USER_ID)
    
    try:
        if tool_name == 'save_phrase':
            result = db.save_phrase(
                user_id=user_id,
                english=arguments['english'],
                japanese=arguments['japanese'],
                context=arguments.get('context', '')
            )
            return {
                'success': True,
                'message': f"Phrase saved: {arguments['english']}",
                'data': result
            }
        
        elif tool_name == 'list_phrases':
            phrases = db.list_phrases(
                user_id=user_id,
                limit=arguments.get('limit', 50),
                order=arguments.get('order', 'desc')
            )
            return {
                'success': True,
                'count': len(phrases),
                'phrases': phrases
            }
        
        elif tool_name == 'search_phrases':
            phrases = db.search_phrases(
                user_id=user_id,
                keyword=arguments['keyword'],
                limit=arguments.get('limit', 20)
            )
            return {
                'success': True,
                'count': len(phrases),
                'keyword': arguments['keyword'],
                'phrases': phrases
            }
        
        elif tool_name == 'get_review_priority':
            phrases = db.get_review_priority(
                user_id=user_id,
                limit=arguments.get('limit', 20)
            )
            return {
                'success': True,
                'count': len(phrases),
                'phrases': phrases
            }
        
        elif tool_name == 'save_correction':
            result = db.save_correction(
                user_id=user_id,
                original_text=arguments['original_text'],
                corrected_text=arguments['corrected_text'],
                feedback=arguments['feedback'],
                error_pattern=arguments.get('error_pattern', '')
            )
            return {
                'success': True,
                'message': 'Correction saved',
                'data': result
            }
        
        elif tool_name == 'analyze_weaknesses':
            analysis = db.analyze_weaknesses(
                user_id=user_id,
                limit=arguments.get('limit', 10)
            )
            return {
                'success': True,
                'analysis': analysis
            }
        
        else:
            return {
                'success': False,
                'error': f'Unknown tool: {tool_name}'
            }
    
    except KeyError as e:
        return {
            'success': False,
            'error': f'Missing required argument: {str(e)}'
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Error executing tool: {str(e)}'
        }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict:
    """
    Lambda handler for MCP requests
    
    Expected event format:
    {
        "method": "tools/call",
        "params": {
            "name": "save_phrase",
            "arguments": {
                "english": "break the ice",
                "japanese": "打ち解ける",
                "context": "..."
            }
        }
    }
    """
    # Handle OPTIONS for CORS
    if event.get('requestContext', {}).get('http', {}).get('method') == 'OPTIONS':
        return create_response(200, {'message': 'OK'})
    
    try:
        # Parse body if it's a string
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', event)
        
        method = body.get('method')
        params = body.get('params', {})
        
        if method == 'tools/list':
            # Return available tools
            tools = [
                {
                    'name': 'save_phrase',
                    'description': 'Save a new English phrase with Japanese translation',
                    'inputSchema': {
                        'type': 'object',
                        'properties': {
                            'english': {'type': 'string', 'description': 'English phrase'},
                            'japanese': {'type': 'string', 'description': 'Japanese translation'},
                            'context': {'type': 'string', 'description': 'Usage context'}
                        },
                        'required': ['english', 'japanese']
                    }
                },
                {
                    'name': 'list_phrases',
                    'description': 'List saved phrases',
                    'inputSchema': {
                        'type': 'object',
                        'properties': {
                            'limit': {'type': 'number', 'description': 'Number of phrases to return'},
                            'order': {'type': 'string', 'enum': ['asc', 'desc'], 'description': 'Sort order'}
                        }
                    }
                },
                {
                    'name': 'search_phrases',
                    'description': 'Search phrases by keyword',
                    'inputSchema': {
                        'type': 'object',
                        'properties': {
                            'keyword': {'type': 'string', 'description': 'Search keyword'},
                            'limit': {'type': 'number', 'description': 'Number of results'}
                        },
                        'required': ['keyword']
                    }
                },
                {
                    'name': 'get_review_priority',
                    'description': 'Get phrases that need review',
                    'inputSchema': {
                        'type': 'object',
                        'properties': {
                            'limit': {'type': 'number', 'description': 'Number of phrases to return'}
                        }
                    }
                },
                {
                    'name': 'save_correction',
                    'description': 'Save an English correction',
                    'inputSchema': {
                        'type': 'object',
                        'properties': {
                            'original_text': {'type': 'string', 'description': 'Original text'},
                            'corrected_text': {'type': 'string', 'description': 'Corrected text'},
                            'feedback': {'type': 'string', 'description': 'Feedback'},
                            'error_pattern': {'type': 'string', 'description': 'Error pattern/type'}
                        },
                        'required': ['original_text', 'corrected_text', 'feedback']
                    }
                },
                {
                    'name': 'analyze_weaknesses',
                    'description': 'Analyze common error patterns',
                    'inputSchema': {
                        'type': 'object',
                        'properties': {
                            'limit': {'type': 'number', 'description': 'Number of patterns to return'}
                        }
                    }
                }
            ]
            return create_response(200, {'tools': tools})
        
        elif method == 'tools/call':
            # Handle tool call
            tool_name = params.get('name')
            arguments = params.get('arguments', {})
            
            result = handle_tool_call(tool_name, arguments)
            return create_response(200, result)
        
        else:
            return create_response(400, {
                'success': False,
                'error': f'Unknown method: {method}'
            })
    
    except json.JSONDecodeError as e:
        return create_response(400, {
            'success': False,
            'error': f'Invalid JSON: {str(e)}'
        })
    except Exception as e:
        return create_response(500, {
            'success': False,
            'error': f'Internal error: {str(e)}'
        })