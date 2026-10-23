
    
  
from flask import Flask, render_template_string, request, redirect, url_for, session
import sqlite3
import os
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# =========================================================
# OCUBED SOCIAL APP
# Save this file as Ocubed.py and run it with Python IDLE.
# =========================================================

app = Flask(__name__)
app.secret_key = os.environ.get("OCUBED_SECRET_KEY", "change-this-secret-before-launch")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "ocubed.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "profile_pictures")
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():
    conn = get_db_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS follows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            follower_id INTEGER NOT NULL,
            followed_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (follower_id, followed_id),
            FOREIGN KEY (follower_id) REFERENCES users(id),
            FOREIGN KEY (followed_id) REFERENCES users(id),
            CHECK (follower_id != followed_id)
        )
    """)

    # Add profile columns to older databases without deleting existing data.
    existing_columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()
    }
    profile_columns = {
        "display_name": "TEXT DEFAULT ''",
        "bio": "TEXT DEFAULT ''",
        "profile_picture": "TEXT DEFAULT ''",
    }
    for name, column_type in profile_columns.items():
        if name not in existing_columns:
            conn.execute(f"ALTER TABLE users ADD COLUMN {name} {column_type}")

    conn.commit()
    conn.close()


create_tables()


# =========================================================
# SHARED PAGE STYLES
# =========================================================

BASE_STYLE = """
<style>
    * { box-sizing: border-box; }
    body {
        margin: 0;
        background: #0d0a16;
        color: #f5f1ff;
        font-family: Arial, "Segoe UI", sans-serif;
        line-height: 1.6;
    }
    /* More CSS continues here */
</style>
"""

if __name__ == "__main__":
    app.run(debug=False, use_reloader=False, port=5001)
