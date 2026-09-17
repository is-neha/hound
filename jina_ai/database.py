import sqlite3
import datetime

DB_NAME = "hound.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    # Enable Write-Ahead Logging to prevent "database is locked" errors during concurrency
    conn.execute("PRAGMA journal_mode=WAL;")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS opportunities (
            id TEXT PRIMARY KEY,
            title TEXT,
            link TEXT,
            spoken_alert TEXT,
            urgency_score INTEGER,
            is_deadline BOOLEAN,
            expiration_date TEXT,
            last_reminded_date TEXT,
            category TEXT
        )
    ''')
    conn.commit()
    conn.close()
    
    # Auto-clean expired entries
    clean_expired_db()

def clean_expired_db():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        today = datetime.date.today().isoformat()
        cursor.execute("DELETE FROM opportunities WHERE expiration_date < ?", (today,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[DB] Auto-clean failed: {e}")

def insert_opportunity(opp_id, title, link, spoken_alert, urgency, is_deadline, exp_date, category):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO opportunities 
            (id, title, link, spoken_alert, urgency_score, is_deadline, expiration_date, last_reminded_date, category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (opp_id, title, link, spoken_alert, urgency, is_deadline, exp_date, "", category))
        conn.commit()
    except sqlite3.IntegrityError:
        # If it exists, update urgency and spoken alert if it's a deadline approaching
        cursor.execute('''
            UPDATE opportunities 
            SET urgency_score = ?, spoken_alert = ? 
            WHERE id = ? AND is_deadline = 1
        ''', (urgency, spoken_alert, opp_id))
        conn.commit()
    conn.close()

def get_top_urgent_alerts(limit=3):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    today = datetime.date.today().isoformat()
    
    cursor.execute('''
        SELECT id, spoken_alert 
        FROM opportunities 
        WHERE last_reminded_date != ? AND expiration_date >= ?
        ORDER BY urgency_score DESC 
        LIMIT ?
    ''', (today, today, limit))
    
    rows = cursor.fetchall()
    conn.close()
    return rows

def mark_as_reminded(opp_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    today = datetime.date.today().isoformat()
    cursor.execute('UPDATE opportunities SET last_reminded_date = ? WHERE id = ?', (today, opp_id))
    conn.commit()
    conn.close()
