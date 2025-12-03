import os
from awslabs.mcp_lambda_handler import MCPLambdaHandler
from dynamodb_helper import DynamoDBHelper


# Initialize
db = DynamoDBHelper(region_name=os.environ.get('AWS_REGION', 'ap-northeast-1'))
DEFAULT_USER_ID = os.environ.get('DEFAULT_USER_ID', 'default_user')

mcp = MCPLambdaHandler(
    name="english-learning-mcp",
    version="1.0.0"
)


@mcp.tool()
def save_phrase(english: str, japanese: str, context: str = "") -> str:
    """Save a new English phrase with Japanese translation.
    
    Args:
        english: English phrase
        japanese: Japanese translation
        context: Usage context or example sentence
    """
    result = db.save_phrase(
        user_id=DEFAULT_USER_ID,
        english=english,
        japanese=japanese,
        context=context
    )
    return f"✅ Phrase saved: {english} = {japanese}"


@mcp.tool()
def list_phrases(limit: int = 50, order: str = 'desc') -> str:
    """List saved phrases.
    
    Args:
        limit: Number of phrases to return (default: 50)
        order: Sort order - 'asc' or 'desc' (default: 'desc')
    """
    phrases = db.list_phrases(
        user_id=DEFAULT_USER_ID,
        limit=limit,
        order=order
    )
    
    if not phrases:
        return "No phrases found."
    
    text = f"Found {len(phrases)} phrases:\n\n"
    for i, p in enumerate(phrases[:20], 1):
        text += f"{i}. {p['english']} = {p['japanese']}\n"
        if p.get('context'):
            text += f"   Context: {p['context']}\n"
        text += "\n"
    
    if len(phrases) > 20:
        text += f"... and {len(phrases) - 20} more phrases"
    
    return text


@mcp.tool()
def search_phrases(keyword: str, limit: int = 20) -> str:
    """Search phrases by keyword.
    
    Args:
        keyword: Search keyword (searches in English, Japanese, and context)
        limit: Maximum number of results (default: 20)
    """
    phrases = db.search_phrases(
        user_id=DEFAULT_USER_ID,
        keyword=keyword,
        limit=limit
    )
    
    if not phrases:
        return f"No phrases found matching '{keyword}'."
    
    text = f"Found {len(phrases)} matches for '{keyword}':\n\n"
    for i, p in enumerate(phrases, 1):
        text += f"{i}. {p['english']} = {p['japanese']}\n"
        if p.get('context'):
            text += f"   Context: {p['context']}\n"
        text += "\n"
    
    return text


@mcp.tool()
def get_review_priority(limit: int = 20) -> str:
    """Get phrases that need review.
    
    Args:
        limit: Number of phrases to return (default: 20)
    """
    phrases = db.get_review_priority(
        user_id=DEFAULT_USER_ID,
        limit=limit
    )
    
    if not phrases:
        return "No phrases need review. Great job!"
    
    text = f"📚 {len(phrases)} phrases need review:\n\n"
    for i, p in enumerate(phrases, 1):
        text += f"{i}. {p['english']} = {p['japanese']}\n"
        text += f"   Queried: {p.get('query_count', 0)} times\n"
        if p.get('context'):
            text += f"   Context: {p['context']}\n"
        text += "\n"
    
    return text


@mcp.tool()
def save_correction(
    original_text: str,
    corrected_text: str,
    feedback: str,
    error_pattern: str = ""
) -> str:
    """Save an English correction.
    
    Args:
        original_text: Original (incorrect) text
        corrected_text: Corrected text
        feedback: Explanation of the correction
        error_pattern: Type of error (e.g., 'grammar', 'tense', 'spelling')
    """
    result = db.save_correction(
        user_id=DEFAULT_USER_ID,
        original_text=original_text,
        corrected_text=corrected_text,
        feedback=feedback,
        error_pattern=error_pattern
    )
    
    text = "✅ Correction saved\n\n"
    text += f"Before: {original_text}\n"
    text += f"After: {corrected_text}\n"
    text += f"Feedback: {feedback}"
    
    if error_pattern:
        text += f"\nError type: {error_pattern}"
    
    return text


@mcp.tool()
def analyze_weaknesses(limit: int = 10) -> str:
    """Analyze common error patterns from corrections.
    
    Args:
        limit: Number of top patterns to return (default: 10)
    """
    analysis = db.analyze_weaknesses(
        user_id=DEFAULT_USER_ID,
        limit=limit
    )
    
    text = "📊 Weakness Analysis\n\n"
    text += f"Total corrections: {analysis['total_corrections']}\n\n"
    
    if analysis['common_patterns']:
        text += "Common error patterns:\n"
        for i, p in enumerate(analysis['common_patterns'], 1):
            text += f"{i}. {p['pattern']}: {p['count']} times\n"
        text += "\n"
    
    if analysis['recent_corrections']:
        text += "Recent corrections:\n"
        for i, c in enumerate(analysis['recent_corrections'][:3], 1):
            text += f"{i}. {c['original_text']} → {c['corrected_text']}\n"
    
    return text


def lambda_handler(event, context):
    """AWS Lambda handler function."""
    return mcp.handle_request(event, context)