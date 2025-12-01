import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

DB_PATH = Path.home() / ".english_learning_mcp" / "learning.db"

def init_db():
    """Initialize database and tables"""
    DB_PATH.parent.mkdir(exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS phrases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            english TEXT NOT NULL,
            japanese TEXT NOT NULL,
            context TEXT,
            query_count INTEGER DEFAULT 0,
            last_queried_at TIMESTAMP,
            reviewed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS corrections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_text TEXT NOT NULL,
            corrected_text TEXT NOT NULL,
            feedback TEXT,
            error_pattern TEXT,
            reviewed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    try:
        cursor.execute("ALTER TABLE phrases ADD COLUMN query_count INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute("ALTER TABLE phrases ADD COLUMN last_queried_at TIMESTAMP")
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute("ALTER TABLE phrases ADD COLUMN reviewed_at TIMESTAMP")
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute("ALTER TABLE corrections ADD COLUMN error_pattern TEXT")
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute("ALTER TABLE corrections ADD COLUMN reviewed_at TIMESTAMP")
    except sqlite3.OperationalError:
        pass
    
    conn.commit()
    conn.close()

def save_phrase_to_db(english: str, japanese: str, context: str = ""):
    """Save phrase to database"""
    init_db()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO phrases (english, japanese, context) VALUES (?, ?, ?)",
        (english, japanese, context)
    )
    
    conn.commit()
    conn.close()

def save_correction_to_db(original_text: str, corrected_text: str, feedback: str = ""):
    """Save correction content to database"""
    init_db()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO corrections (original_text, corrected_text, feedback) VALUES (?, ?, ?)",
        (original_text, corrected_text, feedback)
    )
    
    conn.commit()
    conn.close()

def list_phrases_from_db(period: str = "all"):
    """List saved phrases from database"""
    init_db()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if period == "today":
        cursor.execute("""
            SELECT english, japanese, context, created_at 
            FROM phrases 
            WHERE DATE(created_at) = DATE('now')
            ORDER BY created_at DESC
        """)
    elif period == "this_week":
        cursor.execute("""
            SELECT english, japanese, context, created_at 
            FROM phrases 
            WHERE created_at >= DATE('now', '-7 days')
            ORDER BY created_at DESC
        """)
    else:
        cursor.execute("""
            SELECT english, japanese, context, created_at 
            FROM phrases 
            ORDER BY created_at DESC
        """)
    
    results = cursor.fetchall()
    conn.close()
    
    return results

def search_phrases_in_db(keyword: str):
    """Search phrases by keyword and record search count"""
    init_db()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, english, japanese, context, created_at 
        FROM phrases 
        WHERE english LIKE ? OR japanese LIKE ? OR context LIKE ?
        ORDER BY created_at DESC
    """, (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"))
    
    results = cursor.fetchall()
    
    for phrase_id, *_ in results:
        cursor.execute("""
            UPDATE phrases 
            SET query_count = query_count + 1, last_queried_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (phrase_id,))
    
    conn.commit()
    conn.close()
    
    return [(eng, jpn, ctx, created) for _, eng, jpn, ctx, created in results]

def get_frequent_mistakes():
    """Analyze frequently made mistake patterns"""
    init_db()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT original_text, corrected_text, feedback, COUNT(*) as count
        FROM corrections
        GROUP BY LOWER(TRIM(original_text))
        HAVING count > 1
        ORDER BY count DESC
        LIMIT 10
    """)
    
    results = cursor.fetchall()
    conn.close()
    
    return results

def get_hard_to_remember_phrases():
    """Analyze hard-to-remember phrases based on search frequency"""
    init_db()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT english, japanese, query_count, last_queried_at
        FROM phrases
        WHERE query_count > 1
        ORDER BY query_count DESC
        LIMIT 10
    """)
    
    results = cursor.fetchall()
    conn.close()
    
    return results

def get_needs_review():
    """Get phrases that need review (old but not reviewed recently)"""
    init_db()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT english, japanese, context, created_at
        FROM phrases
        WHERE (reviewed_at IS NULL OR reviewed_at < DATE('now', '-7 days'))
        AND created_at < DATE('now', '-3 days')
        ORDER BY created_at ASC
        LIMIT 10
    """)
    
    results = cursor.fetchall()
    conn.close()
    
    return results
