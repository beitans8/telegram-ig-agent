import os
import sqlite3
from datetime import datetime, timezone, timedelta
import requests

DB_PATH = "/app/usage.db"
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT,
        provider TEXT,
        units INTEGER,
        cost REAL
    )
    """)
    conn.commit()
    return conn

def log_usage(provider, units, cost):
    conn = get_conn()
    conn.execute(
        "INSERT INTO usage (ts, provider, units, cost) VALUES (?, ?, ?, ?)",
        (datetime.now(timezone.utc).isoformat(), provider, units, cost)
    )
    conn.commit()
    conn.close()

def send_daily_report():
    conn = get_conn()
    since = datetime.now(timezone.utc) - timedelta(days=1)
    rows = conn.execute(
        "SELECT provider, SUM(units), SUM(cost) FROM usage WHERE ts >= ? GROUP BY provider",
        (since.isoformat(),)
    ).fetchall()

    total = 0
    text = "📊 Daily Usage Report\n\n"
    for provider, units, cost in rows:
        cost = cost or 0
        units = units or 0
        total += cost
        text += f"{provider}: {units} units | ${cost:.4f}\n"

    text += f"\nTotal: ${total:.4f}"

    if BOT_TOKEN and ADMIN_CHAT_ID:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": ADMIN_CHAT_ID, "text": text}
        )

    conn.close()
