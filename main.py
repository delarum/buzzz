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
 
 #auth helpers
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("welcome"))
        return f(*args, **kwargs)
    return wrapper
 
# ─────────────────────────────────────────
#  2.1 — WELCOME / LANDING
# ─────────────────────────────────────────
 
@app.route("/")
def welcome():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("welcome.html")
 
# ─────────────────────────────────────────
#  2.2 — REGISTRATION & LOGIN
# ─────────────────────────────────────────
 
@app.route("/signup", methods=["GET"])
def signup():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("auth.html", mode="signup")
 
@app.route("/login", methods=["GET"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("auth.html", mode="login")
 
@app.route("/api/signup", methods=["POST"])
def api_signup():
    data     = request.get_json()
    name     = data.get("name", "").strip()
    username = data.get("username", "").strip().lower()
    email    = data.get("email", "").strip().lower()
    password = data.get("password", "")
    avatar   = data.get("avatar", "avatar-1")
 
    # Validation
    if not all([name, username, email, password]):
        return jsonify({"error": "All fields are required."}), 400
    if len(username) < 3:
        return jsonify({"error": "Username must be at least 3 characters."}), 400
    if not re.match(r"^[a-z0-9_]+$", username):
        return jsonify({"error": "Username: only letters, numbers and underscores."}), 400
    if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
        return jsonify({"error": "Please enter a valid email address."}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400
 
    try:
        with get_db() as db:
            db.execute(
                "INSERT INTO users (name, username, email, password_hash, avatar) VALUES (?,?,?,?,?)",
                (name, username, email, generate_password_hash(password), avatar)
            )
            user = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
            session["user_id"]  = user["id"]
            session["username"] = user["username"]
            session["name"]     = user["name"]
        return jsonify({"ok": True, "redirect": "/onboarding"})
    except sqlite3.IntegrityError as e:
        if "username" in str(e):
            return jsonify({"error": "That username is already taken."}), 400
        if "email" in str(e):
            return jsonify({"error": "That email is already registered."}), 400
        return jsonify({"error": "Registration failed. Please try again."}), 400
 
@app.route("/api/login", methods=["POST"])
def api_login():
    data     = request.get_json()
    username = data.get("username", "").strip().lower()
    password = data.get("password", "")
 
    if not username or not password:
        return jsonify({"error": "Please fill in all fields."}), 400
 
    with get_db() as db:
        user = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
 
    if not user:
        return jsonify({"error": "Username not found."}), 401
    if not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Incorrect password."}), 401
 
    session["user_id"]  = user["id"]
    session["username"] = user["username"]
    session["name"]     = user["name"]
 
    # Check if preferences exist
    with get_db() as db:
        prefs = db.execute("SELECT * FROM user_preferences WHERE user_id=?", (user["id"],)).fetchone()
 
    redirect_to = "/dashboard" if prefs else "/onboarding"
    return jsonify({"ok": True, "redirect": redirect_to})
 
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("welcome"))

# preference quiz and onboarding
 
@app.route("/onboarding")
@login_required
def onboarding():
    return render_template("onboarding.html", name=session.get("name", ""))
 
@app.route("/api/preferences", methods=["POST"])
@login_required
def save_preferences():
    data = request.get_json()
 
    categories  = data.get("categories", [])
    distance_km = int(data.get("distance_km", 20))
    timing      = data.get("timing", "either")
    price_type  = data.get("price_type", "both")
    vibe        = data.get("vibe", "social")
 
    with get_db() as db:
        db.execute("""
            INSERT INTO user_preferences (user_id, categories, distance_km, timing, price_type, vibe)
            VALUES (?,?,?,?,?,?)
            ON CONFLICT(user_id) DO UPDATE SET
                categories=excluded.categories,
                distance_km=excluded.distance_km,
                timing=excluded.timing,
                price_type=excluded.price_type,
                vibe=excluded.vibe,
                updated_at=CURRENT_TIMESTAMP
        """, (session["user_id"], json.dumps(categories), distance_km, timing, price_type, vibe))
 
    return jsonify({"ok": True, "redirect": "/dashboard"})
 
# ─────────────────────────────────────────
#  DASHBOARD (placeholder)
# ─────────────────────────────────────────
 
@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", name=session.get("name", ""))
 
# ─────────────────────────────────────────
#  RUN
# ─────────────────────────────────────────
 
if __name__ == "__main__":
    print("\n  buzzz. is live")
    print("  ─────────────────────────")
    print("  http://localhost:5000\n")
    app.run(debug=True, port=5000)
 