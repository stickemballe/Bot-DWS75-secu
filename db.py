import sqlite3
import time
import os

DB_PATH = os.getenv("DB_PATH", "bot_data.sqlite")

def init_db():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS subscribers (
            chat_id   INTEGER PRIMARY KEY,
            username  TEXT,
            first_seen INTEGER,
            last_seen  INTEGER
        )
    """)
    con.commit()
    cur.close()
    con.close()

def upsert_subscriber(chat_id: int, username: str | None):
    now = int(time.time())
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        INSERT INTO subscribers(chat_id, username, first_seen, last_seen)
        VALUES(?, ?, ?, ?)
        ON CONFLICT(chat_id) DO UPDATE SET
            username=excluded.username,
            last_seen=excluded.last_seen
    """, (chat_id, username, now, now))
    con.commit()
    cur.close()
    con.close()

def get_all_chat_ids() -> list[int]:
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT chat_id FROM subscribers")
    rows = cur.fetchall()
    cur.close()
    con.close()
    return [r[0] for r in rows]
