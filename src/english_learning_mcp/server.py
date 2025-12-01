from fastmcp import FastMCP
from .database.db import (
    save_phrase_to_db, 
    save_correction_to_db,
    list_phrases_from_db, 
    search_phrases_in_db,
    get_frequent_mistakes,
    get_hard_to_remember_phrases,
    get_needs_review,
    init_db
)

mcp = FastMCP("English Learning MCP")

init_db()

@mcp.tool()
def save_phrase(english: str, japanese: str, context: str = "") -> str:
    """Save an English phrase with its Japanese translation
    
    Args:
        english: English phrase to save
        japanese: Japanese translation
        context: Optional context or example usage
    """
    save_phrase_to_db(english, japanese, context)
    return f"✅ Saved to database: '{english}' = '{japanese}'"

@mcp.tool()
def save_correction(original_text: str, corrected_text: str, feedback: str = "") -> str:
    """Save a correction with feedback
    
    Args:
        original_text: The original text with errors
        corrected_text: The corrected version
        feedback: Optional explanation of the correction
    """
    save_correction_to_db(original_text, corrected_text, feedback)
    return f"✅ Correction saved:\n❌ {original_text}\n✅ {corrected_text}"

@mcp.tool()
def list_phrases(period: str = "all") -> str:
    """List saved phrases from database
    
    Args:
        period: Time period to show - "today", "this_week", or "all" (default)
    """
    phrases = list_phrases_from_db(period)
    
    if not phrases:
        return f"No phrases found for period: {period}"
    
    result = f"📚 Saved phrases ({period}):\n\n"
    for eng, jpn, ctx, created in phrases:
        result += f"• {eng}\n  → {jpn}\n"
        if ctx:
            result += f"  💡 {ctx}\n"
        result += f"  📅 {created}\n\n"
    
    return result

@mcp.tool()
def search_phrases(keyword: str) -> str:
    """Search for phrases by keyword
    
    Args:
        keyword: Keyword to search in English, Japanese, or context
    """
    phrases = search_phrases_in_db(keyword)
    
    if not phrases:
        return f"No phrases found for keyword: '{keyword}'"
    
    result = f"🔍 Search results for '{keyword}':\n\n"
    for eng, jpn, ctx, created in phrases:
        result += f"• {eng}\n  → {jpn}\n"
        if ctx:
            result += f"  💡 {ctx}\n"
        result += f"  📅 {created}\n\n"
    
    return result.strip()

@mcp.tool()
def analyze_weaknesses() -> str:
    """Analyze your learning weaknesses - repeated mistakes and hard-to-remember phrases"""
    
    mistakes = get_frequent_mistakes()
    
    hard_phrases = get_hard_to_remember_phrases()
    
    result = "📊 Weakness Analysis\n\n"
    
    if mistakes:
        result += "🔴 Repeated Mistakes:\n"
        for orig, corr, feedback, count in mistakes:
            result += f"\n❌ {orig}\n✅ {corr}\n"
            if feedback:
                result += f"💡 {feedback}\n"
            result += f"🔢 Repeated {count} times\n"
    else:
        result += "🔴 Repeated Mistakes: None found\n"
    
    result += "\n"
    
    if hard_phrases:
        result += "🟡 Hard to Remember Phrases:\n"
        for eng, jpn, count, last_query in hard_phrases:
            result += f"\n• {eng} → {jpn}\n"
            result += f"🔍 Searched {count} times\n"
            if last_query:
                result += f"📅 Last searched: {last_query}\n"
    else:
        result += "🟡 Hard to Remember Phrases: None found\n"
    
    return result.strip()

@mcp.tool()
def get_review_priority() -> str:
    """Get phrases that need review based on time and usage patterns"""
    
    needs_review = get_needs_review()
    
    if not needs_review:
        return "✅ No phrases need review right now. Great job!"
    
    result = "📝 Priority Review List\n\n"
    result += "These phrases haven't been reviewed recently:\n\n"
    
    for eng, jpn, ctx, created in needs_review:
        result += f"• {eng}\n  → {jpn}\n"
        if ctx:
            result += f"  �� {ctx}\n"
        result += f"  📅 Saved: {created}\n\n"
    
    return result.strip()

if __name__ == "__main__":
    mcp.run()
