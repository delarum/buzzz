from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import json
import sqlite3, os, re
from functools import wraps
from event_service import get_events, get_event_detail
from avatar_utils import (
    get_avatar_url,
    generate_random_seed,
    AVATAR_STYLES,
    POPULAR_STYLES,
)

app = Flask(__name__)
app.secret_key = "buzzz-secret-key-2026"
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = False
app.config["PERMANENT_SESSION_LIFETIME"] = 86400  

DB_PATH = os.path.join("data", "buzzz.db")
os.makedirs("data", exist_ok=True)

# ── DB ─────────────────────────────────────────────
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
                avatar_icon TEXT DEFAULT 'adventurer',
                avatar_color TEXT DEFAULT '',
                avatar_bg TEXT DEFAULT '',
                bio TEXT DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS friend_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_id INTEGER NOT NULL,
                to_id INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (from_id) REFERENCES users(id),
                FOREIGN KEY (to_id)   REFERENCES users(id),
                UNIQUE(from_id, to_id)
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_id INTEGER NOT NULL,
                to_id   INTEGER NOT NULL,
                body    TEXT NOT NULL,
                seen    INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (from_id) REFERENCES users(id),
                FOREIGN KEY (to_id)   REFERENCES users(id)
            );
                         
             CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT DEFAULT 'local',
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    category TEXT DEFAULT 'general',
    location_name TEXT DEFAULT '',
    address TEXT DEFAULT '',
    lat REAL DEFAULT -1.2864,
    lng REAL DEFAULT 36.8172,
    date_time TEXT NOT NULL,
    price INTEGER DEFAULT 0,
    is_free INTEGER DEFAULT 0,
    attendee_count INTEGER DEFAULT 0,
    image_url TEXT DEFAULT '',
    event_url TEXT DEFAULT '',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);            

             CREATE TABLE IF NOT EXISTS rsvps (
             id INTEGER PRIMARY KEY AUTOINCREMENT,
             user_id INTEGER NOT NULL,
             event_id INTEGER NOT NULL,
             event_title TEXT NOT NULL DEFAULT '',
             event_category TEXT NOT NULL DEFAULT 'general',
             event_date TEXT NOT NULL DEFAULT '',
              
             created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
             FOREIGN KEY (user_id) REFERENCES users(id),
             UNIQUE(user_id, event_id)
        );                
""")
        # Migrate existing users table
        existing = {row[1] for row in db.execute("PRAGMA table_info(users)").fetchall()}
        migrations = [
            ("avatar_icon",  "TEXT DEFAULT 'adventurer'"),
            ("avatar_color", "TEXT DEFAULT ''"),
            ("avatar_bg",    "TEXT DEFAULT ''"),
            ("bio",          "TEXT DEFAULT ''"),
        ]
        for col, definition in migrations:
            if col not in existing:
                db.execute(f"ALTER TABLE users ADD COLUMN {col} {definition}")
                print(f"[DB] Added missing column: {col}")

init_db()

# ── AUTH HELPERS ──────────────────────────────────
def login_required(f):
    @wraps(f)
    def w(*a, **kw):
        if "user_id" not in session:
            return redirect(url_for("welcome"))
        return f(*a, **kw)
    return w

def current_user():
    if "user_id" not in session:
        return None
    with get_db() as db:
        row = db.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
        return dict(row) if row else None

# ── AVATAR HELPERS ────────────────────────────────
def get_user_avatar(user):
    if user is None:
        return get_avatar_url("default", "adventurer")
    if not isinstance(user, dict):
        user = dict(user)
    if user.get("avatar_bg"):
        return user["avatar_bg"]
    seed  = user.get("avatar_color") or user.get("username", "default")
    style = user.get("avatar_icon", "adventurer")
    return get_avatar_url(seed, style)
app.jinja_env.globals["get_user_avatar"] = get_user_avatar

# ── ROUTES ────────────────────────────────────────
@app.route("/")
def welcome():
    if "user_id" in session:
        return redirect(url_for("events_page"))
    return render_template("welcome.html")

@app.route("/signup")
def signup():
    return render_template("auth.html", mode="signup")

@app.route("/login")
def login():
    return render_template("auth.html", mode="login")

# ── SIGNUP API ────────────────────────────────────
@app.route("/api/signup", methods=["POST"])
def api_signup():
    d = request.get_json()
    if not d:
        return jsonify({"error": "Invalid request."}), 400

    name     = d.get("name", "").strip()
    username = d.get("username", "").strip().lower()
    email    = d.get("email", "").strip().lower()
    password = d.get("password", "")

    avatar_seed  = d.get("avatar_seed", "").strip()
    avatar_style = d.get("avatar_style", "adventurer").strip()

    if not avatar_seed:
        avatar_seed = generate_random_seed()
    if avatar_style not in AVATAR_STYLES:
        avatar_style = "adventurer"

    avatar_url = get_avatar_url(avatar_seed, avatar_style)

    if not all([name, username, email, password]):
        return jsonify({"error": "All fields required."}), 400
    if len(username) < 3:
        return jsonify({"error": "Username must be at least 3 characters."}), 400
    if not re.match(r"^[a-z0-9_]+$", username):
        return jsonify({"error": "Username may only contain letters, numbers and underscores."}), 400
    if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
        return jsonify({"error": "Please enter a valid email address."}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400

    try:
        with get_db() as db:
            db.execute("""
                INSERT INTO users
                  (name, username, email, password_hash, avatar_icon, avatar_color, avatar_bg)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (name, username, email, generate_password_hash(password),
                  avatar_style, avatar_seed, avatar_url))

            u = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
            session.permanent = True
            session.update({"user_id": u["id"], "username": u["username"], "name": u["name"]})

        return jsonify({"ok": True, "redirect": "/onboarding"})
    except sqlite3.IntegrityError:
        return jsonify({"error": "Username or email already exists."}), 400

# ── LOGIN API ─────────────────────────────────────
@app.route("/api/login", methods=["POST"])
def api_login():
    d = request.get_json()
    if not d:
        return jsonify({"error": "Invalid request."}), 400

    username = d.get("username", "").strip().lower()
    password = d.get("password", "")

    if not username or not password:
        return jsonify({"error": "Username and password are required."}), 400

    with get_db() as db:
        u = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()

    if not u or not check_password_hash(u["password_hash"], password):
        return jsonify({"error": "Invalid username or password."}), 401
    
    session.permanent = True
    session.update({"user_id": u["id"], "username": u["username"], "name": u["name"]})
    return jsonify({"ok": True, "redirect": "/events"})

# ── AVATAR STYLES API ─────────────────────────────
@app.route("/api/avatar/styles")
def get_avatar_styles():
    return jsonify({"styles": AVATAR_STYLES, "popular": POPULAR_STYLES})

# ── ONBOARDING ────────────────────────────────────
@app.route("/onboarding")
@login_required
def onboarding():
    return render_template("onboarding.html")

@app.route("/api/preferences", methods=["POST"])
@login_required
def save_preferences():
    d = request.get_json()
    if not d:
        return jsonify({"error": "Invalid request."}), 400

    uid = session["user_id"]

    with get_db() as db:
        # Add prefs columns if they don't exist yet
        existing = {row[1] for row in db.execute("PRAGMA table_info(users)").fetchall()}
        migrations = [
            ("pref_categories", "TEXT DEFAULT ''"),
            ("pref_distance_km","INTEGER DEFAULT 20"),
            ("pref_timing",     "TEXT DEFAULT 'either'"),
            ("pref_price_type", "TEXT DEFAULT 'both'"),
            ("pref_vibe",       "TEXT DEFAULT 'social'"),
        ]
        for col, definition in migrations:
            if col not in existing:
                db.execute(f"ALTER TABLE users ADD COLUMN {col} {definition}")

        import json
        db.execute("""
            UPDATE users SET
                pref_categories  = ?,
                pref_distance_km = ?,
                pref_timing      = ?,
                pref_price_type  = ?,
                pref_vibe        = ?
            WHERE id = ?
        """, (
            json.dumps(d.get("categories", [])),
            int(d.get("distance_km", 20)),
            d.get("timing", "either"),
            d.get("price_type", "both"),
            d.get("vibe", "social"),
            uid,
        ))

    return jsonify({"ok": True, "redirect": "/events"})

# ── EVENTS ────────────────────────────────────────
@app.route("/events")
@login_required
def events_page():
    uid = session["user_id"]
    with get_db() as db:
        me = db.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
        me = dict(me) if me else {}
        row = db.execute(
            "SELECT COUNT(*) as cnt FROM messages WHERE to_id=? AND seen=0", (uid,)
        ).fetchone()
        unread_total = row["cnt"] if row else 0

    # Load saved preferences
    cats     = json.loads(me.get("pref_categories") or "[]")
    distance = int(me.get("pref_distance_km") or 30)
    timing   = me.get("pref_timing") or "either"
    price    = me.get("pref_price_type") or "both"

    events, source = get_events()

    # Add is_free_label and rsvped flag to each event
    # Add is_free_label, rsvped flag, and friends going to each event
    with get_db() as db:
        rsvp_rows = db.execute("SELECT event_id FROM rsvps WHERE user_id=?", (uid,)).fetchall()
        rsvped_ids = {r["event_id"] for r in rsvp_rows}

        # Get all friends
        friend_rows = db.execute("""
            SELECT u.id, u.name, u.avatar_icon, u.avatar_color, u.avatar_bg
            FROM users u
            JOIN friend_requests fr ON (
                (fr.from_id=? AND fr.to_id=u.id) OR
                (fr.to_id=? AND fr.from_id=u.id)
            )
            WHERE fr.status='accepted' AND u.id != ?
        """, (uid, uid, uid)).fetchall()
        friends = [dict(f) for f in friend_rows]
        friend_ids = [f["id"] for f in friends]

        # For each event, find which friends are going
        friends_at = {}
        if friend_ids:
            placeholders = ",".join("?" * len(friend_ids))
            att_rows = db.execute(f"""
                SELECT r.event_id, u.id, u.name,
                       u.avatar_icon, u.avatar_color, u.avatar_bg
                FROM rsvps r
                JOIN users u ON u.id = r.user_id
                WHERE r.user_id IN ({placeholders})
            """, friend_ids).fetchall()
            for r in att_rows:
                friends_at.setdefault(r["event_id"], []).append({
                    "id": r["id"],
                    "name": r["name"],
                    "avatar_url": get_user_avatar(dict(r)),
                })

    for e in events:
        e["is_free_label"] = "Free" if e.get("is_free") else f"KES {e.get('price', 0):,}"
        e["rsvped"] = e.get("id") in rsvped_ids
        e["friends_going"] = friends_at.get(e.get("id"), [])

    prefs = {
        "categories": cats,
        "distance_km": distance,
        "timing": timing,
        "price_type": price,
    }    

    return render_template("events.html", events=events, prefs=prefs,
                           source=source, me=me, unread_total=unread_total)

# ══════════════════════════════════════════════════
# FRIENDS
# ══════════════════════════════════════════════════

def _friend_status(db, me_id, other_id):
    """Return relationship status between two users."""
    row = db.execute("""
        SELECT status, from_id FROM friend_requests
        WHERE (from_id=? AND to_id=?) OR (from_id=? AND to_id=?)
    """, (me_id, other_id, other_id, me_id)).fetchone()
    if not row:
        return "none"
    if row["status"] == "accepted":
        return "friends"
    if row["status"] == "pending":
        return "sent" if row["from_id"] == me_id else "received"
    return "none"

@app.route("/friends")
@login_required
def friends_page():
    me = current_user()
    uid = session["user_id"]
    q   = request.args.get("q", "").strip()

    with get_db() as db:
        # Accepted friends
        friends = db.execute("""
            SELECT u.* FROM users u
            JOIN friend_requests fr ON (
                (fr.from_id=? AND fr.to_id=u.id) OR
                (fr.to_id=?   AND fr.from_id=u.id)
            )
            WHERE fr.status='accepted' AND u.id != ?
        """, (uid, uid, uid)).fetchall()

        # Pending requests sent TO me
        incoming = db.execute("""
            SELECT u.*, fr.id AS req_id FROM users u
            JOIN friend_requests fr ON fr.from_id=u.id
            WHERE fr.to_id=? AND fr.status='pending'
        """, (uid,)).fetchall()

        # Search results
        results = []
        if q:
            results = db.execute("""
                SELECT * FROM users
                WHERE (username LIKE ? OR name LIKE ?) AND id != ?
                LIMIT 20
            """, (f"%{q}%", f"%{q}%", uid)).fetchall()
            results = [dict(r) | {"rel": _friend_status(db, uid, r["id"])} for r in results]

        # Unread message count per friend
        unread = {row["from_id"]: row["cnt"] for row in db.execute("""
            SELECT from_id, COUNT(*) as cnt FROM messages
            WHERE to_id=? AND seen=0 GROUP BY from_id
        """, (uid,)).fetchall()}

        # Events each friend is attending
        friend_events = {}
        for f in friends:
            ev = db.execute("""
                SELECT event_title, event_date FROM rsvps
                WHERE user_id=?
                ORDER BY event_date DESC LIMIT 1
            """, (f["id"],)).fetchone()
            if ev:
                friend_events[f["id"]] = dict(ev)

    return render_template("friends.html",
        me=me, friends=friends, incoming=incoming,
        results=results, q=q, unread=unread,
        friend_events=friend_events,
        get_user_avatar=get_user_avatar)

@app.route("/friends/add/<username>", methods=["POST"])
@login_required
def friend_add(username):
    uid = session["user_id"]
    with get_db() as db:
        target = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if not target or target["id"] == uid:
            return jsonify({"error": "User not found."}), 404
        try:
            db.execute(
                "INSERT INTO friend_requests (from_id, to_id) VALUES (?,?)",
                (uid, target["id"])
            )
            return jsonify({"ok": True, "status": "sent"})
        except sqlite3.IntegrityError:
            return jsonify({"error": "Request already exists."}), 409

@app.route("/friends/accept/<int:req_id>", methods=["POST"])
@login_required
def friend_accept(req_id):
    uid = session["user_id"]
    with get_db() as db:
        db.execute("""
            UPDATE friend_requests SET status='accepted'
            WHERE id=? AND to_id=? AND status='pending'
        """, (req_id, uid))
    return jsonify({"ok": True})

@app.route("/friends/decline/<int:req_id>", methods=["POST"])
@login_required
def friend_decline(req_id):
    uid = session["user_id"]
    with get_db() as db:
        db.execute("""
            DELETE FROM friend_requests
            WHERE id=? AND to_id=? AND status='pending'
        """, (req_id, uid))
    return jsonify({"ok": True})

@app.route("/friends/remove/<username>", methods=["POST"])
@login_required
def friend_remove(username):
    uid = session["user_id"]
    with get_db() as db:
        target = db.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
        if target:
            db.execute("""
                DELETE FROM friend_requests
                WHERE (from_id=? AND to_id=?) OR (from_id=? AND to_id=?)
            """, (uid, target["id"], target["id"], uid))
    return jsonify({"ok": True})

# ── Friend profile ────────────────────────────────
@app.route("/profile/<username>")
@login_required
def profile(username):
    uid = session["user_id"]
    with get_db() as db:
        user = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if not user:
            return "User not found", 404
        user = dict(user)
        rel = _friend_status(db, uid, user["id"])
        req_row = db.execute("""
            SELECT id FROM friend_requests
            WHERE from_id=? AND to_id=? AND status='pending'
        """, (user["id"], uid)).fetchone()
        req_id = req_row["id"] if req_row else None
    return render_template("profile.html", user=user, rel=rel, req_id=req_id,
                           get_user_avatar=get_user_avatar)

# ══════════════════════════════════════════════════
# MESSAGES
# ══════════════════════════════════════════════════

def _are_friends(db, a, b):
    row = db.execute("""
        SELECT 1 FROM friend_requests
        WHERE ((from_id=? AND to_id=?) OR (from_id=? AND to_id=?))
        AND status='accepted'
    """, (a, b, b, a)).fetchone()
    return row is not None

@app.route("/messages/<username>", methods=["GET"])
@login_required
def messages_thread(username):
    uid = session["user_id"]
    with get_db() as db:
        other = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if not other:
            return "User not found", 404
        other = dict(other)
        if not _are_friends(db, uid, other["id"]):
            return "You must be friends to message.", 403

        # Mark incoming as seen
        db.execute("""
            UPDATE messages SET seen=1
            WHERE from_id=? AND to_id=? AND seen=0
        """, (other["id"], uid))

        thread = [dict(r) for r in db.execute("""
            SELECT m.*, u.username, u.name,
                   u.avatar_icon, u.avatar_color, u.avatar_bg
            FROM messages m
            JOIN users u ON u.id = m.from_id
            WHERE (m.from_id=? AND m.to_id=?) OR (m.from_id=? AND m.to_id=?)
            ORDER BY m.created_at ASC
        """, (uid, other["id"], other["id"], uid)).fetchall()]

    me = current_user()
    return render_template("messages.html", me=me, other=other,
                           thread=thread, get_user_avatar=get_user_avatar)

@app.route("/messages/<username>", methods=["POST"])
@login_required
def messages_send(username):
    uid  = session["user_id"]
    body = (request.get_json() or {}).get("body", "").strip()
    if not body:
        return jsonify({"error": "Empty message."}), 400

    with get_db() as db:
        other = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if not other:
            return jsonify({"error": "User not found."}), 404
        if not _are_friends(db, uid, other["id"]):
            return jsonify({"error": "Not friends."}), 403

        db.execute(
            "INSERT INTO messages (from_id, to_id, body) VALUES (?,?,?)",
            (uid, other["id"], body)
        )
        return jsonify({"ok": True})

@app.route("/api/messages/<username>/poll")
@login_required
def messages_poll(username):
    """Long-poll endpoint — returns messages newer than ?after=<id>"""
    uid   = session["user_id"]
    after = int(request.args.get("after", 0))
    with get_db() as db:
        other = db.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
        if not other:
            return jsonify([])
        db.execute("""
            UPDATE messages SET seen=1
            WHERE from_id=? AND to_id=? AND seen=0
        """, (other["id"], uid))
        rows = db.execute("""
            SELECT m.id, m.body, m.created_at, m.from_id,
                   u.username, u.name,
                   u.avatar_icon, u.avatar_color, u.avatar_bg
            FROM messages m
            JOIN users u ON u.id = m.from_id
            WHERE ((m.from_id=? AND m.to_id=?) OR (m.from_id=? AND m.to_id=?))
              AND m.id > ?
            ORDER BY m.created_at ASC
        """, (uid, other["id"], other["id"], uid, after)).fetchall()

    return jsonify([{
        "id"        : r["id"],
        "body"      : r["body"],
        "created_at": r["created_at"],
        "from_id"   : r["from_id"],
        "username"  : r["username"],
        "name"      : r["name"],
        "avatar_url": get_user_avatar(dict(r)),
        "is_me"     : r["from_id"] == uid,
    } for r in rows])

# ══════════════════════════════════════════════════
# STATS  —  add this block to main.py before logout
# ══════════════════════════════════════════════════

# Also add this table to init_db() inside the executescript:
#
#   CREATE TABLE IF NOT EXISTS rsvps (
#       id         INTEGER PRIMARY KEY AUTOINCREMENT,
#       user_id    INTEGER NOT NULL,
#       event_id   INTEGER NOT NULL,
#       event_title   TEXT NOT NULL DEFAULT '',
#       event_category TEXT NOT NULL DEFAULT 'general',
#       event_date    TEXT NOT NULL DEFAULT '',
#       created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
#       FOREIGN KEY (user_id) REFERENCES users(id),
#       UNIQUE(user_id, event_id)
#   );

import json
from datetime import datetime, timedelta

def _get_stats(db, uid):
    """Compute all stats for a given user id. Returns a dict."""

    # ── Total attended ──────────────────────────────
    total = db.execute(
        "SELECT COUNT(*) FROM rsvps WHERE user_id=?", (uid,)
    ).fetchone()[0]

    # ── Favourite category ──────────────────────────
    fav_row = db.execute("""
        SELECT event_category, COUNT(*) AS cnt
        FROM rsvps WHERE user_id=?
        GROUP BY event_category ORDER BY cnt DESC LIMIT 1
    """, (uid,)).fetchone()
    fav_category = fav_row["event_category"] if fav_row else "—"
    fav_count    = fav_row["cnt"]            if fav_row else 0

    # ── This month ──────────────────────────────────
    month_start = datetime.now().replace(day=1).strftime("%Y-%m-%d")
    this_month  = db.execute("""
        SELECT COUNT(*) FROM rsvps
        WHERE user_id=? AND event_date >= ?
    """, (uid, month_start)).fetchone()[0]

    # ── Streak (consecutive weeks with ≥1 event) ───
    rows = db.execute("""
        SELECT event_date FROM rsvps
        WHERE user_id=? AND event_date != ''
        ORDER BY event_date DESC
    """, (uid,)).fetchall()

    streak = 0
    if rows:
        seen_weeks = set()
        for r in rows:
            try:
                d = datetime.strptime(r["event_date"][:10], "%Y-%m-%d")
                # ISO week key: year-week
                wk = d.strftime("%G-%V")
                seen_weeks.add(wk)
            except Exception:
                pass

        # Walk back from current week
        today = datetime.now()
        check = today
        while True:
            wk = check.strftime("%G-%V")
            if wk in seen_weeks:
                streak += 1
                check -= timedelta(weeks=1)
            else:
                break

    # ── Category breakdown ──────────────────────────
    cat_rows = db.execute("""
        SELECT event_category, COUNT(*) AS cnt
        FROM rsvps WHERE user_id=?
        GROUP BY event_category ORDER BY cnt DESC
    """, (uid,)).fetchall()
    categories = [{"name": r["event_category"], "count": r["cnt"]} for r in cat_rows]

    # ── Monthly trend (last 6 months) ──────────────
    monthly = []
    for i in range(5, -1, -1):
        d     = datetime.now() - timedelta(days=30 * i)
        mo    = d.strftime("%Y-%m")
        label = d.strftime("%b")
        cnt   = db.execute("""
            SELECT COUNT(*) FROM rsvps
            WHERE user_id=? AND event_date LIKE ?
        """, (uid, f"{mo}%")).fetchone()[0]
        monthly.append({"label": label, "count": cnt})

    # ── Friends overlap ─────────────────────────────
    friends = db.execute("""
        SELECT u.id, u.name, u.username,
               u.avatar_icon, u.avatar_color, u.avatar_bg
        FROM users u
        JOIN friend_requests fr ON (
            (fr.from_id=? AND fr.to_id=u.id) OR
            (fr.to_id=?   AND fr.from_id=u.id)
        )
        WHERE fr.status='accepted' AND u.id != ?
    """, (uid, uid, uid)).fetchall()

    friend_overlap = []
    for f in friends:
        shared = db.execute("""
            SELECT COUNT(*) FROM rsvps r1
            JOIN rsvps r2 ON r1.event_id = r2.event_id
            WHERE r1.user_id=? AND r2.user_id=?
        """, (uid, f["id"])).fetchone()[0]
        friend_overlap.append({
            "id"       : f["id"],
            "name"     : f["name"],
            "username" : f["username"],
            "avatar_url": get_user_avatar(dict(f)),
            "shared"   : shared,
        })
    friend_overlap.sort(key=lambda x: x["shared"], reverse=True)

    # ── Recent events ───────────────────────────────
    recent = db.execute("""
        SELECT * FROM rsvps WHERE user_id=?
        ORDER BY event_date DESC LIMIT 5
    """, (uid,)).fetchall()

    return {
        "total"          : total,
        "fav_category"   : fav_category,
        "fav_count"      : fav_count,
        "this_month"     : this_month,
        "streak"         : streak,
        "categories"     : categories,
        "monthly"        : monthly,
        "friend_overlap" : friend_overlap,
        "recent"         : [dict(r) for r in recent],
    }


@app.route("/stats")
@login_required
def stats_page():
    uid = session["user_id"]
    with get_db() as db:
        me = db.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
        if not me:
            return redirect(url_for("logout"))
        me = dict(me)
        stats = _get_stats(db, uid)
    return render_template("stats.html", me=me, subject=me,
                           stats=stats, is_own=True,
                           get_user_avatar=get_user_avatar)


@app.route("/stats/<username>")
@login_required
def stats_other(username):
    uid = session["user_id"]
    me  = current_user()
    with get_db() as db:
        subject = db.execute(
            "SELECT * FROM users WHERE username=?", (username,)
        ).fetchone()
        if not subject:
            return "User not found", 404
        subject = dict(subject)
        stats = _get_stats(db, subject["id"])
    return render_template("stats.html", me=me, subject=subject,
                           stats=stats, is_own=(subject["id"] == uid),
                           get_user_avatar=get_user_avatar)


# ── RSVP API (updated to also write to rsvps table) ──
@app.route("/api/rsvp/<int:event_id>", methods=["POST"])
@login_required
def api_rsvp(event_id):
    uid    = session["user_id"]
    d      = request.get_json() or {}
    action = d.get("action", "going")   # "going" | "cancel"

    with get_db() as db:
        # Get event info
        ev = db.execute(
            "SELECT * FROM events WHERE id=?", (event_id,)
        ).fetchone()
        if not ev:
            return jsonify({"error": "Event not found"}), 404

        if action == "going":
            try:
                db.execute("""
                    INSERT INTO rsvps
                      (user_id, event_id, event_title, event_category, event_date)
                    VALUES (?,?,?,?,?)
                """, (uid, event_id,
                      ev["title"],
                      ev["category"],
                      ev["date_time"][:10]))
            except sqlite3.IntegrityError:
                pass  # already rsvped
        else:
            db.execute(
                "DELETE FROM rsvps WHERE user_id=? AND event_id=?",
                (uid, event_id)
            )

    return jsonify({"ok": True})


# ── EVENT DETAIL ──────────────────────────────────
@app.route("/events/<int:event_id>")
@login_required
def event_detail(event_id):
    uid = session["user_id"]
    with get_db() as db:
        event = db.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
        if not event:
            return "Event not found", 404
        event = dict(event)

        # Check if current user has RSVPed
        rsvp = db.execute(
            "SELECT 1 FROM rsvps WHERE user_id=? AND event_id=?", (uid, event_id)
        ).fetchone()
        event["rsvped"] = rsvp is not None

        # Total RSVPs for this event
        total = db.execute(
            "SELECT COUNT(*) as cnt FROM rsvps WHERE event_id=?", (event_id,)
        ).fetchone()
        event["total_rsvps"] = total["cnt"] if total else 0

        # Friends going
        friends_going = db.execute("""
            SELECT u.name, u.avatar_icon, u.avatar_color, u.avatar_bg
            FROM rsvps r
            JOIN users u ON u.id = r.user_id
            JOIN friend_requests fr ON (
                (fr.from_id=? AND fr.to_id=u.id) OR
                (fr.to_id=? AND fr.from_id=u.id)
            )
            WHERE r.event_id=? AND fr.status='accepted' AND u.id != ?
        """, (uid, uid, event_id, uid)).fetchall()
        event["friends_going"] = [dict(f) for f in friends_going]

        # Related events (same category, not this one)
        related = db.execute("""
            SELECT * FROM events
            WHERE category=? AND id!=?
            AND date_time >= datetime('now')
            ORDER BY date_time ASC LIMIT 4
        """, (event["category"], event_id)).fetchall()
        related = [dict(r) for r in related]

        # Add is_free_label
        event["is_free_label"] = "Free" if event["is_free"] else f"KES {event['price']:,}"

        me = db.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
        me = dict(me) if me else {}

    return render_template("event_detail.html", event=event, related=related, me=me)

# ── LOGOUT ────────────────────────────────────────
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("welcome"))

# ── RUN ───────────────────────────────────────────
if __name__ == "__main__":
    print("\n buzzz. is live")
    print(" http://localhost:5000\n")
    app.run(debug=True, port=5000)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)    