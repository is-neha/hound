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
    cursor.execute("SELECT title, source, link, description, deadline FROM opportunities")
    rows = cursor.fetchall()
    conn.close()
    
    ops = []
    for r in rows:
        ops.append({
            "title": r[0],
            "source": r[1],
            "link": r[2],
            "description": r[3],
            "deadline": r[4]
        })
    return ops

def _sync_json():
    ops = get_all_opportunities()
    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(ops, f, indent=4)
