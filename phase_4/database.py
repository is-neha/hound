import sqlite3
import json
import os

DB_PATH = "hound.db"
JSON_PATH = "data.json"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS opportunities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            source TEXT,
            link TEXT,
            description TEXT,
            deadline TEXT
        )
    ''')
    try:
        cursor.execute("ALTER TABLE opportunities ADD COLUMN last_reminded_date DATE")
    except sqlite3.OperationalError:
        pass # Column already exists
    conn.commit()
    conn.close()

def mark_as_reminded(opp_id, date_str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE opportunities SET last_reminded_date = ? WHERE id = ?", (date_str, opp_id))
    conn.commit()
    conn.close()

def save_opportunity(title, source, link, description, deadline="Unknown"):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Check if exists
    cursor.execute("SELECT id FROM opportunities WHERE link = ?", (link,))
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO opportunities (title, source, link, description, deadline)
            VALUES (?, ?, ?, ?, ?)
        ''', (title, source, link, description, deadline))
        conn.commit()
    conn.close()
    _sync_json()

def get_all_opportunities():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, source, link, description, deadline, last_reminded_date FROM opportunities")
    rows = cursor.fetchall()
    conn.close()
    
    ops = []
    for r in rows:
        ops.append({
            "id": r[0],
            "title": r[1],
            "source": r[2],
            "link": r[3],
            "description": r[4],
            "deadline": r[5],
            "last_reminded_date": r[6]
        })
    return ops

def _sync_json():
    ops = get_all_opportunities()
    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(ops, f, indent=4)
