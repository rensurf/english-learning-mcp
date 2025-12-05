import os
import time
from datetime import datetime, timedelta
import jwt
from jwt.algorithms import RSAAlgorithm
import requests
import json
import boto3
from dynamodb_helper import DynamoDBHelper


# Configuration
LINE_API_URL = "https://api.line.me/v2/bot/message/push"
LINE_TOKEN_URL = "https://api.line.me/oauth2/v3/token"

# Get SSM client
ssm = boto3.client('ssm', region_name=os.environ.get('AWS_REGION', 'ap-northeast-1'))

# LINE authentication credentials from environment variables
CHANNEL_ID = os.getenv("LINE_CHANNEL_ID")
KID = os.getenv("LINE_KID")
USER_ID = os.getenv("LINE_USER_ID")

# Get PRIVATE_KEY from SSM SecureString
try:
    response = ssm.get_parameter(
        Name='/english-learning-mcp/line-private-key',
        WithDecryption=True
    )
    PRIVATE_KEY_JSON = response['Parameter']['Value']
except Exception as e:
    print(f"❌ Failed to get LINE_PRIVATE_KEY from SSM: {e}")
    PRIVATE_KEY_JSON = None

DEFAULT_USER_ID = os.getenv("DEFAULT_USER_ID", "default_user")

# Initialize DynamoDB helper
db = DynamoDBHelper(region_name=os.environ.get('AWS_REGION', 'ap-northeast-1'))


def generate_channel_access_token():
    """Generate Channel Access Token using JWT"""
    
    if not all([CHANNEL_ID, KID, PRIVATE_KEY_JSON]):
        raise ValueError("LINE environment variables are not set")
    
    # Parse private key
    private_key_dict = json.loads(PRIVATE_KEY_JSON)
    key = RSAAlgorithm.from_jwk(private_key_dict)
    
    # JWT header
    headers = {
        "alg": "RS256",
        "typ": "JWT",
        "kid": KID
    }
    
    # JWT payload
    payload = {
        "iss": CHANNEL_ID,
        "sub": CHANNEL_ID,
        "aud": "https://api.line.me/",
        "exp": int(time.time()) + (60 * 30),  # Expires in 30 minutes
        "token_exp": 60 * 60 * 24 * 30  # Token valid for 30 days
    }
    
    # Generate JWT
    jwt_token = jwt.encode(payload, key, algorithm="RS256", headers=headers)
    
    # Obtain Channel Access Token
    response = requests.post(
        LINE_TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "client_credentials",
            "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            "client_assertion": jwt_token
        }
    )
    
    if response.status_code != 200:
        raise Exception(f"Token acquisition failed: {response.text}")
    
    return response.json()["access_token"]


def get_today_summary():
    """Aggregate today's learning data from DynamoDB"""
    
    # Today's date (JST)
    jst_offset = timedelta(hours=9)
    today = (datetime.utcnow() + jst_offset).strftime("%Y-%m-%d")
    today_start = f"{today}T00:00:00"
    today_end = f"{today}T23:59:59"
    
    # Get all phrases
    all_phrases = db.phrases_table.query(
        KeyConditionExpression='user_id = :uid',
        ExpressionAttributeValues={':uid': DEFAULT_USER_ID}
    ).get('Items', [])
    
    # Filter phrases created today
    today_phrases = [
        p for p in all_phrases
        if p.get('created_at', '').startswith(today)
    ]
    today_phrases.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    today_phrases = today_phrases[:5]  # Latest 5
    
    # Get all corrections
    all_corrections = db.corrections_table.query(
        KeyConditionExpression='user_id = :uid',
        ExpressionAttributeValues={':uid': DEFAULT_USER_ID}
    ).get('Items', [])
    
    # Filter corrections created today
    today_corrections = [
        c for c in all_corrections
        if c.get('created_at', '').startswith(today)
    ]
    today_corrections.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    today_corrections = today_corrections[:3]  # Latest 3
    
    # Phrases needing review (not viewed for 7+ days)
    week_ago = (datetime.utcnow() + jst_offset - timedelta(days=7)).strftime("%Y-%m-%d")
    need_review = [
        p for p in all_phrases
        if not p.get('last_queried_at') or p.get('last_queried_at', '') < week_ago
    ]
    need_review.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    need_review = need_review[:5]  # Max 5
    
    return {
        "date": today,
        "today_phrases": today_phrases,
        "today_corrections": today_corrections,
        "need_review_phrases": need_review,
    }


def format_summary_message(summary):
    """Format summary as LINE message"""
    
    if not summary["today_phrases"] and not summary["today_corrections"]:
        return f"""📚 Today's English Learning Summary

Date: {summary['date']}

No learning records today.
Keep going tomorrow! 💪"""
    
    message = f"""📚 Today's English Learning Summary

Date: {summary["date"]}
"""
    
    # Phrases saved today
    if summary["today_phrases"]:
        message += f"\n📝 Saved Phrases ({len(summary['today_phrases'])}):\n"
        for p in summary["today_phrases"]:
            message += f"\n• {p['english']}\n  → {p['japanese']}\n"
            if p.get('context'):
                message += f"  💡 {p['context']}\n"
    
    # Corrections today
    if summary["today_corrections"]:
        message += f"\n✏️ Corrections ({len(summary['today_corrections'])}):\n"
        for c in summary["today_corrections"]:
            message += f"\n❌ {c['original_text']}\n"
            message += f"✅ {c['corrected_text']}\n"
            if c.get('feedback'):
                message += f"💬 {c['feedback']}\n"
    
    # Phrases needing review
    if summary["need_review_phrases"]:
        message += f"\n⚠️ Need Review ({len(summary['need_review_phrases'])}):\n"
        for p in summary["need_review_phrases"][:3]:  # Max 3
            message += f"• {p['english']}\n"
    
    # Motivation message
    phrase_count = len(summary["today_phrases"])
    correction_count = len(summary["today_corrections"])
    
    if phrase_count >= 5:
        message += "\n\n🎉 Excellent! You learned a lot today!"
    elif correction_count >= 3:
        message += "\n\n👍 Great job! You're growing through corrections!"
    else:
        message += "\n\n💪 Keep going tomorrow!"
    
    return message


def send_line_message(message):
    """Send message to LINE"""
    
    try:
        # Generate Channel Access Token
        access_token = generate_channel_access_token()
        
        # Send message
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }
        
        data = {
            "to": USER_ID,
            "messages": [
                {
                    "type": "text",
                    "text": message
                }
            ]
        }
        
        response = requests.post(LINE_API_URL, headers=headers, json=data)
        
        if response.status_code == 200:
            print(f"✅ LINE message sent successfully: {datetime.utcnow()}")
            return True
        else:
            print(f"❌ LINE message send failed: {response.status_code} - {response.text}")
            return False
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def lambda_handler(event, context):
    """AWS Lambda handler function"""
    
    print(f"🔔 LINE notification Lambda started: {datetime.utcnow()}")
    
    try:
        # Get today's summary
        summary = get_today_summary()
        
        # Create message
        message = format_summary_message(summary)
        
        print("\n📤 Message to send:")
        print("-" * 40)
        print(message)
        print("-" * 40)
        
        # Send to LINE
        success = send_line_message(message)
        
        if success:
            print("\n✅ Process completed")
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'LINE notification sent successfully'})
            }
        else:
            print("\n❌ Process failed")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Failed to send LINE notification'})
            }
    
    except Exception as e:
        print(f"\n❌ Error in lambda_handler: {e}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }