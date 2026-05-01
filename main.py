from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, os, json, re
from functools import wraps
from event_service import get_events, get_event_detail  
from avatar_utils import (
    get_avatar_url,
    generate_random_seed,
    get_avatar_data_for_db,
    AVATAR_STYLES,
    POPULAR_STYLES,
)


app = Flask(__name__)
app.secret_key = "buzzz-secret-key-2026"

DB_PATH = os.path.join("data", "buzzz.db")
os.makedirs("data", exist_ok=True)

# ── DB ──────────────────────────────────────────────────────────────────────
def get_db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    with get_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                avatar_icon TEXT DEFAULT 'music',
                avatar_color TEXT DEFAULT '#e8821a',
                avatar_bg TEXT DEFAULT '#3d1a00',
                bio TEXT DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id INTEGER PRIMARY KEY REFERENCES users(id),
                categories TEXT DEFAULT '[]',
                distance_km INTEGER DEFAULT 20,
                timing TEXT DEFAULT 'either',
                price_type TEXT DEFAULT 'both',
                vibe TEXT DEFAULT 'social',
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT DEFAULT 'local',
                title TEXT NOT NULL,
                description TEXT,
                category TEXT NOT NULL,
                location_name TEXT,
                address TEXT,
                lat REAL,
                lng REAL,
                date_time DATETIME,
                price INTEGER DEFAULT 0,
                is_free INTEGER DEFAULT 0,
                image_url TEXT DEFAULT '',
                event_url TEXT DEFAULT '',
                attendee_count INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS rsvps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES users(id),
                event_id INTEGER REFERENCES events(id),
                status TEXT DEFAULT 'going',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, event_id)
            );
        """)

init_db()

# ── AUTH HELPERS ─────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def w(*a, **kw):
        if "user_id" not in session:
            return redirect(url_for("welcome"))
        return f(*a, **kw)
    return w

def get_prefs():
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM user_preferences WHERE user_id=?",
            (session["user_id"],)
        ).fetchone()
    if not row:
        return {"categories": [], "distance_km": 30, "timing": "either",
                "price_type": "both", "vibe": "social"}
    d = dict(row)
    d["categories"] = json.loads(d.get("categories", "[]"))
    return d

def get_me():
    with get_db() as db:
        u = db.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    return dict(u) if u else {}

# ── 1. WELCOME ───────────────────────────────────────────────────────────────
@app.route("/")
def welcome():
    if "user_id" in session:
        return redirect(url_for("events_page"))
    return render_template("welcome.html")

# ── 2. AUTH ──────────────────────────────────────────────────────────────────
@app.route("/signup")
def signup():
    return render_template("auth.html", mode="signup")

@app.route("/login")
def login():
    return render_template("auth.html", mode="login")

@app.route("/api/signup", methods=["POST"])
def api_signup():
    d = request.get_json()
    name      = d.get("name", "").strip()
    username  = d.get("username", "").strip().lower()
    email     = d.get("email", "").strip().lower()
    password  = d.get("password", "")
    av_icon   = d.get("avatar_icon", "music")
    av_color  = d.get("avatar_color", "#e8821a")
    av_bg     = d.get("avatar_bg", "#3d1a00")

    if not all([name, username, email, password]):
        return jsonify({"error": "All fields required."}), 400
    if len(username) < 3:
        return jsonify({"error": "Username min 3 chars."}), 400
    if not re.match(r"^[a-z0-9_]+$", username):
        return jsonify({"error": "Username: letters/numbers/underscores."}), 400
    if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
        return jsonify({"error": "Invalid email."}), 400
    if len(password) < 6:
        return jsonify({"error": "Password min 6 chars."}), 400

    try:
        with get_db() as db:
            db.execute("""
                INSERT INTO users(name,username,email,password_hash,avatar_icon,avatar_color,avatar_bg)
                VALUES(?,?,?,?,?,?,?)
            """, (name, username, email, generate_password_hash(password),
                  av_icon, av_color, av_bg))
            u = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
            session.update({"user_id": u["id"], "username": u["username"], "name": u["name"]})
        return jsonify({"ok": True, "redirect": "/onboarding"})
    except sqlite3.IntegrityError:
        return jsonify({"error": "Username or email already taken."}), 400

@app.route('/api/signup', methods=['POST'])
def signup():
    """Handle user registration with avatar selection."""
    # Get form data
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    
    # Get avatar data from form (sent by avatar picker)
    avatar_seed = request.form.get('avatar_seed')
    avatar_style = request.form.get('avatar_style', 'adventurer')
    avatar_url = request.form.get('avatar_url')
    
    # If no avatar was selected, generate a default one
    if not avatar_seed:
        avatar_seed = generate_random_seed()
        avatar_url = get_avatar_url(avatar_seed, avatar_style)
    
    # Validate style
    if avatar_style not in AVATAR_STYLES:
        avatar_style = 'adventurer'
        avatar_url = get_avatar_url(avatar_seed, avatar_style)
    
    # Hash password (use your existing password hashing)
    password_hash = generate_password_hash(password)
    
    # Insert user into database
    # Using your existing schema with avatar_icon, avatar_color, avatar_bg
    with get_db() as db:
        db.execute(
            """
            INSERT INTO users (username, email, password_hash, avatar_icon, avatar_color, avatar_bg)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (username, email, password_hash, avatar_style, avatar_seed, avatar_url)
        )
    
    return redirect('/login')

def get_user_avatar(user):
    """
    Get avatar URL from user dict/row.
    Use this when displaying avatars in templates.
    
    Usage in template:
        <img src="{{ get_user_avatar(user) }}" alt="Avatar" />
    """
    # If we have the full URL stored
    if user.get('avatar_bg'):
        return user['avatar_bg']
    
    # Otherwise, generate from seed and style
    seed = user.get('avatar_color', user.get('username', 'default'))
    style = user.get('avatar_icon', 'adventurer')
    
    return get_avatar_url(seed, style)


# Make it available in templates
app.jinja_env.globals['get_user_avatar'] = get_user_avatar


# -------------------------------------------------------------
# STEP 5: API endpoint for style list (optional)
# -------------------------------------------------------------

@app.route('/api/avatar/styles', methods=['GET'])
def get_avatar_styles():
    """Return available avatar styles."""
    return jsonify({
        "styles": AVATAR_STYLES,
        "popular": POPULAR_STYLES
    })

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("welcome"))

# ── 3. ONBOARDING ─────────────────────────────────────────────────────────────
@app.route("/onboarding")
@login_required
def onboarding():
    return render_template("onboarding.html", name=session.get("name", ""))

@app.route("/api/preferences", methods=["POST"])
@login_required
def save_preferences():
    d = request.get_json()
    with get_db() as db:
        db.execute("""
            INSERT INTO user_preferences(user_id,categories,distance_km,timing,price_type,vibe)
            VALUES(?,?,?,?,?,?)
            ON CONFLICT(user_id) DO UPDATE SET
                categories=excluded.categories,
                distance_km=excluded.distance_km,
                timing=excluded.timing,
                price_type=excluded.price_type,
                vibe=excluded.vibe,
                updated_at=CURRENT_TIMESTAMP
        """, (
            session["user_id"],
            json.dumps(d.get("categories", [])),
            int(d.get("distance_km", 20)),
            d.get("timing", "either"),
            d.get("price_type", "both"),
            d.get("vibe", "social"),
        ))
    return jsonify({"ok": True, "redirect": "/events"})

# ── 4. EVENT FEED ─────────────────────────────────────────────────────────────
@app.route("/events")
@login_required
def events_page():
    prefs  = get_prefs()
    me     = get_me()
    events, source = get_events(
        categories  = prefs["categories"] or None,
        distance_km = prefs["distance_km"],
        timing      = prefs["timing"],
        price_type  = prefs["price_type"],
    )
    with get_db() as db:
        rsvped = {r["event_id"] for r in db.execute(
            "SELECT event_id FROM rsvps WHERE user_id=?", (session["user_id"],)
        ).fetchall()}
    for e in events:
        e["rsvped"]         = (int(e["id"]) in rsvped)
        e["is_free_label"]  = "Free" if e.get("is_free") else f"KES {e.get('price', 0):,}"
    return render_template("events.html", events=events, prefs=prefs, source=source, me=me)

# ── 5. EVENT DETAIL ───────────────────────────────────────────────────────────
# FIX 2: This entire route was missing — templates linked to /events/<id> but
#         the route did not exist, causing a 404 on every event card click.
@app.route("/events/<int:event_id>")
@login_required
def event_detail(event_id):
    event = get_event_detail(event_id)
    if not event:
        return "Event not found", 404

    with get_db() as db:
        # FIX 3: total_rsvps — referenced in template but never fetched
        rsvp = db.execute(
            "SELECT * FROM rsvps WHERE user_id=? AND event_id=?",
            (session["user_id"], event_id)
        ).fetchone()

        total_rsvps = db.execute(
            "SELECT COUNT(*) as cnt FROM rsvps WHERE event_id=?", (event_id,)
        ).fetchone()["cnt"]

        # FIX 4: friends_going — referenced in template but never fetched
        # Pulls avatar fields so the template can colour each friend's avatar
        friends_going = db.execute("""
            SELECT u.name, u.username, u.avatar_icon, u.avatar_color, u.avatar_bg
            FROM rsvps r
            JOIN users u ON r.user_id = u.id
            WHERE r.event_id = ? AND r.user_id != ?
            LIMIT 8
        """, (event_id, session["user_id"])).fetchall()

        # Related events — same category, upcoming, excluding current
        related = db.execute("""
            SELECT * FROM events
            WHERE category=? AND id!=? AND date_time >= datetime('now')
            ORDER BY date_time ASC LIMIT 4
        """, (event["category"], event_id)).fetchall()

    event["rsvped"]        = bool(rsvp)
    event["total_rsvps"]   = total_rsvps
    event["friends_going"] = [dict(f) for f in friends_going]
    event["is_free_label"] = "Free" if event.get("is_free") else f"KES {event.get('price', 0):,}"

    return render_template(
        "event_detail.html",
        event   = event,
        related = [dict(r) for r in related],
        me      = get_me(),
    )

# ── 6. RSVP API ───────────────────────────────────────────────────────────────
# FIX 5: This route was missing — event_detail.html calls /api/rsvp/<id>
#         but the endpoint did not exist, so the RSVP button silently failed.
@app.route("/api/rsvp/<int:event_id>", methods=["POST"])
@login_required
def rsvp(event_id):
    action = request.get_json().get("action", "going")
    with get_db() as db:
        if action == "cancel":
            db.execute(
                "DELETE FROM rsvps WHERE user_id=? AND event_id=?",
                (session["user_id"], event_id)
            )
        else:
            db.execute("""
                INSERT INTO rsvps (user_id, event_id, status) VALUES (?,?,?)
                ON CONFLICT(user_id, event_id) DO UPDATE SET status=excluded.status
            """, (session["user_id"], event_id, action))
        count = db.execute(
            "SELECT COUNT(*) FROM rsvps WHERE event_id=?", (event_id,)
        ).fetchone()[0]
    return jsonify({"ok": True, "status": action, "count": count})

# ── 7. PROFILE (stub) ─────────────────────────────────────────────────────────
# FIX 6: Both templates link to /profile but the route did not exist —
#         clicking the avatar in the nav caused a 404.
@app.route("/profile")
@login_required
def profile():
    me = get_me()
    with get_db() as db:
        attended = db.execute(
            "SELECT COUNT(*) FROM rsvps WHERE user_id=?", (session["user_id"],)
        ).fetchone()[0]
        rsvped_events = db.execute("""
            SELECT e.* FROM rsvps r
            JOIN events e ON r.event_id = e.id
            WHERE r.user_id = ?
            ORDER BY e.date_time DESC LIMIT 20
        """, (session["user_id"],)).fetchall()
    return render_template(
        "profile.html",
        me             = me,
        attended       = attended,
        rsvped_events  = [dict(e) for e in rsvped_events],
    )

# ── 8. DASHBOARD → redirect ───────────────────────────────────────────────────
@app.route("/dashboard")
@login_required
def dashboard():
    return redirect(url_for("events_page"))

# ── RUN ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from seed import seed
    seed()
    print("\n  buzzz. is live")
    print("  http://localhost:5000\n")
    app.run(debug=True, port=5000)