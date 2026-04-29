from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, os, json, re
from datetime import datetime
from functools import wraps
 
app = Flask(__name__)
app.secret_key = "buzzz-secret-key-2026"
 
DB_PATH = os.path.join("data", "buzzz.db")
os.makedirs("data", exist_ok=True)

# database setup
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
 
def init_db():
    with get_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                username     TEXT UNIQUE NOT NULL,
                name         TEXT NOT NULL,
                email        TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                avatar       TEXT DEFAULT 'avatar-1',
                created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
            );
 
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id       INTEGER PRIMARY KEY REFERENCES users(id),
                categories    TEXT DEFAULT '[]',
                distance_km   INTEGER DEFAULT 20,
                timing        TEXT DEFAULT 'either',
                price_type    TEXT DEFAULT 'both',
                vibe          TEXT DEFAULT 'social',
                updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
 
init_db()
 