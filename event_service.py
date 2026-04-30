import os, json, sqlite3, requests
from datetime import datetime

EVENTBRITE_TOKEN = os.environ.get("EVENTBRITE_TOKEN", "")
EVENTBRITE_BASE  = "https://www.eventbriteapi.com/v3"
DB_PATH          = os.path.join("data", "buzzz.db")

EB_CATEGORY_IDS = {
    "music": "103", "sports": "108", "food": "110", "tech": "102",
    "art": "105", "outdoor": "113", "film": "104", "networking": "101",
}

# ── Eventbrite ──────────────────────────────────────────────────────────────

def fetch_eventbrite(categories=None, distance_km=30, lat=-1.2864, lng=36.8172):
    if not EVENTBRITE_TOKEN:
        return None
    headers = {"Authorization": f"Bearer {EVENTBRITE_TOKEN}"}
    cat_ids = ",".join(EB_CATEGORY_IDS[c] for c in (categories or []) if c in EB_CATEGORY_IDS) or None
    params  = {
        "location.latitude": lat, "location.longitude": lng,
        "location.within": f"{distance_km}km",
        "expand": "venue,ticket_availability,organizer",
        "sort_by": "date", "start_date.keyword": "this_month",
    }
    if cat_ids:
        params["categories"] = cat_ids
    try:
        r = requests.get(f"{EVENTBRITE_BASE}/events/search/", headers=headers, params=params, timeout=8)
        r.raise_for_status()
        return [_norm_eb(e) for e in r.json().get("events", [])]
    except Exception as e:
        print(f"[Eventbrite] {e}")
        return None

def _norm_eb(e):
    venue = e.get("venue") or {}
    addr  = venue.get("address") or {}
    tix   = e.get("ticket_availability") or {}
    is_free   = e.get("is_free", False)
    min_price = tix.get("minimum_ticket_price") or {}
    price_val = 0 if is_free else int(float(min_price.get("major_value", 0)))
    rev = {v: k for k, v in EB_CATEGORY_IDS.items()}
    return {
        "id": e["id"], "source": "eventbrite",
        "title": e["name"]["text"],
        "description": (e.get("description") or {}).get("text", ""),
        "category": rev.get(str(e.get("category_id")), "general"),
        "location_name": venue.get("name") or addr.get("city", "Nairobi"),
        "address": addr.get("localized_address_display", "Nairobi, Kenya"),
        "lat": float(venue.get("latitude") or -1.2864),
        "lng": float(venue.get("longitude") or 36.8172),
        "date_time": e["start"]["local"],
        "price": price_val, "is_free": is_free,
        "image_url": (e.get("logo") or {}).get("url", ""),
        "event_url": e.get("url", ""),
        "attendee_count": 0,
    }

# ── Local DB ─────────────────────────────────────────────────────────────────

def get_local_events(categories=None, distance_km=50, max_price=None, timing=None):
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row
    q = "SELECT * FROM events WHERE 1=1"; p = []
    if categories:
        q += f" AND category IN ({','.join('?'*len(categories))})"; p += categories
    if max_price == 0:
        q += " AND price = 0"
    if timing == "evenings":
        q += " AND CAST(strftime('%H',date_time) AS INTEGER) >= 18"
    elif timing == "weekends":
        q += " AND strftime('%w',date_time) IN ('0','6')"
    elif timing == "weekdays":
        q += " AND strftime('%w',date_time) NOT IN ('0','6')"
    q += " AND date_time >= datetime('now') ORDER BY date_time ASC LIMIT 40"
    rows = [dict(r) for r in conn.execute(q, p).fetchall()]
    conn.close()
    return rows

def get_event_detail(event_id, source="local"):
    if source == "eventbrite" and EVENTBRITE_TOKEN:
        try:
            r = requests.get(f"{EVENTBRITE_BASE}/events/{event_id}/",
                headers={"Authorization": f"Bearer {EVENTBRITE_TOKEN}"},
                params={"expand": "venue,ticket_availability,organizer"}, timeout=8)
            r.raise_for_status()
            return _norm_eb(r.json())
        except Exception:
            pass
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row
    row  = conn.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_events(categories=None, distance_km=30, timing=None, price_type=None,
               lat=-1.2864, lng=36.8172):
    if EVENTBRITE_TOKEN:
        events = fetch_eventbrite(categories, distance_km, lat, lng)
        if events:
            return events, "eventbrite"
    events = get_local_events(categories, distance_km,
                              0 if price_type == "free" else None, timing)
    return events, "local"