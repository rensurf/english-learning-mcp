"""
LINE Messaging API Notifier
Script to send daily learning summary to LINE
"""

import os
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
import jwt
from jwt.algorithms import RSAAlgorithm
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
DB_PATH = Path.home() / ".english_learning_mcp" / "learning.db"
LINE_API_URL = "https://api.line.me/v2/bot/message/push"
LINE_TOKEN_URL = "https://api.line.me/oauth2/v3/token"

# LINE authentication credentials
CHANNEL_ID = os.getenv("LINE_CHANNEL_ID")
KID = os.getenv("LINE_KID")
PRIVATE_KEY_JSON = os.getenv("LINE_PRIVATE_KEY")


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


def get_user_id():
    """Get User ID from environment variables"""
    user_id = os.getenv("LINE_USER_ID")
    if not user_id:
        raise ValueError("LINE_USER_ID is not set")
    return user_id


def get_today_summary():
    """Aggregate today's learning data"""

    if not DB_PATH.exists():
        return None

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Today's date
    today = datetime.now().strftime("%Y-%m-%d")

    # Phrases saved today (latest 5)
    cursor.execute("""
        SELECT english, japanese, context
        FROM phrases 
        WHERE date(created_at) = ?
        ORDER BY created_at DESC
        LIMIT 5
    """, (today,))
    today_phrases = cursor.fetchall()

    # Corrections today (latest 3)
    cursor.execute("""
        SELECT original_text, corrected_text, feedback
        FROM corrections 
        WHERE date(created_at) = ?
        ORDER BY created_at DESC
        LIMIT 3
    """, (today,))
    today_corrections = cursor.fetchall()

    # Phrases needing review (not viewed for 1+ week, max 5)
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    cursor.execute("""
        SELECT english, japanese
        FROM phrases 
        WHERE last_queried_at IS NULL OR date(last_queried_at) < ?
        ORDER BY created_at DESC
        LIMIT 5
    """, (week_ago,))
    need_review_phrases = cursor.fetchall()
    
    conn.close()
    
    return {
        "date": today,
        "today_phrases": today_phrases,
        "today_corrections": today_corrections,
        "need_review_phrases": need_review_phrases,
    }


def format_summary_message(summary):
    """Format summary as LINE message"""

    if not summary or (len(summary["today_phrases"]) == 0 and len(summary["today_corrections"]) == 0):
        return f"""📚 Today's English Learning Summary

Date: {datetime.now().strftime("%Y-%m-%d")}

No learning records today.
Keep going tomorrow! 💪"""

    message = f"""📚 Today's English Learning Summary

Date: {summary["date"]}
"""
    
    # Phrases saved today
    if summary["today_phrases"]:
        message += f"\n📝 Saved Phrases ({len(summary['today_phrases'])}):\n"
        for english, japanese, context in summary["today_phrases"]:
            message += f"\n• {english}\n  → {japanese}\n"
            if context:
                message += f"  💡 {context}\n"

    # Corrections today
    if summary["today_corrections"]:
        message += f"\n✏️ Corrections ({len(summary['today_corrections'])}):\n"
        for original, corrected, feedback in summary["today_corrections"]:
            message += f"\n❌ {original}\n"
            message += f"✅ {corrected}\n"
            if feedback:
                message += f"💬 {feedback}\n"

    # Phrases needing review
    if summary["need_review_phrases"]:
        message += f"\n⚠️ Need Review ({len(summary['need_review_phrases'])}):\n"
        for english, japanese in summary["need_review_phrases"][:3]:  # Max 3
            message += f"• {english}\n"

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

        # Get User ID
        user_id = get_user_id()

        # Send message
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }
        
        data = {
            "to": user_id,
            "messages": [
                {
                    "type": "text",
                    "text": message
                }
            ]
        }
        
        response = requests.post(LINE_API_URL, headers=headers, json=data)

        if response.status_code == 200:
            print(f"✅ LINE message sent successfully: {datetime.now()}")
            return True
        else:
            print(f"❌ LINE message send failed: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Main process"""

    print(f"🔔 LINE notification script started: {datetime.now()}")

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
    else:
        print("\n❌ Process failed")


if __name__ == "__main__":
    main()