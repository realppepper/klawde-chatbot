# database.py
import sqlite3
import hashlib
from datetime import datetime

import os
# 프로젝트 루트에 생성되도록 경로 고정
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "chatbot.db")

def get_conn():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT,
            department TEXT,
            gender TEXT,
            age INTEGER
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT,
            created_at TEXT,
            conv_type TEXT DEFAULT 'rag'
        )
    """)
    try:
        c.execute("ALTER TABLE conversations ADD COLUMN conv_type TEXT DEFAULT 'rag'")
    except Exception:
        pass
    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER,
            role TEXT,
            content TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def register_user(username, password, name, department, gender, age):
    try:
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO users (username, password, name, department, gender, age) VALUES (?,?,?,?,?,?)",
                (username, hash_password(password), name, department, gender, age)
            )
        return True
    except sqlite3.IntegrityError:
        return False

def login_user(username, password):
    with get_conn() as conn:
        c = conn.execute("SELECT * FROM users WHERE username=? AND password=?",
                         (username, hash_password(password)))
        return c.fetchone()

def get_conversations(user_id):
    with get_conn() as conn:
        c = conn.execute("""SELECT id, title, created_at FROM conversations
                            WHERE user_id=? AND conv_type='rag'
                            ORDER BY created_at DESC""", (user_id,))
        return c.fetchall()

def create_conversation(user_id, title):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("INSERT INTO conversations (user_id, title, created_at, conv_type) VALUES (?,?,?,?)",
                  (user_id, title, datetime.now().strftime("%Y-%m-%d %H:%M"), "rag"))
        return c.lastrowid

def get_messages(conv_id):
    with get_conn() as conn:
        c = conn.execute("SELECT role, content FROM messages WHERE conversation_id=? ORDER BY id", (conv_id,))
        return [{"role": r[0], "content": r[1]} for r in c.fetchall()]

def save_message(conv_id, role, content):
    with get_conn() as conn:
        conn.execute("INSERT INTO messages (conversation_id, role, content, created_at) VALUES (?,?,?,?)",
                     (conv_id, role, content, datetime.now().strftime("%Y-%m-%d %H:%M")))

def delete_conversation(conv_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM messages WHERE conversation_id=?", (conv_id,))
        conn.execute("DELETE FROM conversations WHERE id=?", (conv_id,))

def delete_all_conversations(user_id):
    with get_conn() as conn:
        conn.execute("""DELETE FROM messages WHERE conversation_id IN
                     (SELECT id FROM conversations WHERE user_id=? AND conv_type='rag')""", (user_id,))
        conn.execute("DELETE FROM conversations WHERE user_id=? AND conv_type='rag'", (user_id,))

def update_user_info(user_id, name, department, gender, age):
    with get_conn() as conn:
        conn.execute("UPDATE users SET name=?, department=?, gender=?, age=? WHERE id=?",
                     (name, department, gender, age, user_id))

def update_password(user_id, new_password):
    with get_conn() as conn:
        conn.execute("UPDATE users SET password=? WHERE id=?", (hash_password(new_password), user_id))