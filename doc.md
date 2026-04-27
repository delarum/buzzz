# Project Blueprint — Event Discovery & Social App

**Project Stage:** Planning & Architecture  
**Stack:** Python (Flask) · SQLite · HTML/CSS/JS  

---

## 1. Project Overview

This application is an event discovery and social platform. Users create a personalised profile, get matched to upcoming events based on their preferences, view those events on an interactive map, and connect with friends to track each other's event attendance.

The product flow is linear across five core experiences:

```
Onboarding → Preference Quiz → Event Feed + Map → Friends & Chat → Stats Dashboard
```

---

## 2. Feature Breakdown

### 2.1 Onboarding — "Peel Away" Welcome Screen

The first thing a user sees is a welcome screen styled as a peel-away page (Page 1). This is a purely presentational animated entry screen that transitions into the registration form.

**What it includes:**
- App name and tagline
- A call-to-action button: **Get Started**
- Animated page-peel transition into the signup flow

**How it is built:**
- HTML/CSS `@keyframes` animation simulates the peel effect
- Flask route `/` renders the landing page
- On "Get Started" click, JavaScript transitions to the signup form or redirects to `/signup`

---

### 2.2 User Registration & Profile Setup

After the welcome screen, the user creates their account.

**Fields collected:**
- Display name
- Username (unique, alphanumeric + underscores)
- Password (minimum 6 characters, stored as a bcrypt hash)
- Avatar / character selection (like Bitmoji — emoji or illustrated avatar grid)


### 2.3 Preference Quiz

Immediately after signup, the user answers a short series of questions so the app can recommend relevant events. This happens only once and can be updated later in settings.

**Example questions:**
- What type of events do you enjoy? *(Music / Sports / Food / Tech / Art / Outdoors)*
- How far are you willing to travel? *(Under 5km / 5–20km / Anywhere)*
- When do you prefer events? *(Weekdays / Weekends / Either)*
- Do you prefer free or ticketed events?

**How it is built:**
- Events api
- AI model using an API to push the algorithm or a filter depending on the bulk


### 2.4 Event Feed + Map View

The central screen of the app. Recommended events are shown as cards in a feed, and simultaneously plotted as pins on an interactive map. This mirrors how apps like Snapchat's Snap Map and Eventbrite work.

#### Apis
- Live events Kenya
- Eventbrite
- Meetup(it is limited)

flask fetches nairobi envents live

**Card data per event:**
- Event name
- Category badge
- Date and time
- Location name and distance from user
- Thumbnail image
- Number of friends attending
- Price (Free / KES XX)

**Map behaviour:**
- Each event is a pin on the map
- Pins are colour-coded by category
- Tapping a pin opens a bottom-sheet card with event details
- User's current location is shown as a pulsing dot


### 2.5 Event Detail Page

When a user taps any event (on the feed or map), they see the full detail view.

**Includes:**
- Full event description
- Date, time, and venue
- Map pin for that specific event
- List of friends who are attending or have attended
- RSVP / "I'm going" button
- Share button


### 2.6 Avatar / Character System (Bitmoji-style)

During signup and in profile settings, users choose a character to represent them. This avatar appears on the map and in chats.

**Two implementation options:**

**Option A (Simple) — Emoji grid:**
- Present a grid of emoji avatars at signup
- Store selected emoji as a string in the users table
- Fast to implement, zero dependencies

**Option B (Advanced) — Illustrated avatar builder:**
- Use DiceBear Avatars API (free): `https://api.dicebear.com/7.x/adventurer/svg?seed=username`
- Generates a unique illustrated avatar from any seed string
- Stored as a URL in the users table

```python
def get_avatar_url(username):
    return f"https://api.dicebear.com/7.x/adventurer/svg?seed={username}"
```

---

### 2.7 Friends & Chat

Users can search for others, add them as friends, and see which events they have attended or are currently at.

**Friend features:**
- Search users by name or username
- Send / accept friend requests
- View friend's profile with their attended events
- See a "currently at event" status if a friend RSVPed to a live event

**Chat features:**
- Direct messages between friends
- Message threads stored in database
- Auto-refresh every 2 seconds via polling

```
GET  /friends                    — friends list
POST /friends/add/<username>     — send request
GET  /messages/<username>        — open chat thread
POST /messages/<username>        — send message
```


### 2.8 Stats Dashboard

Users can view a personal statistics page showing their event history. Friends' stats are also visible from their profile.

**Metrics shown:**
- Total events attended
- Favourite category (most attended)
- Events attended this month
- Streak (consecutive weeks with at least one event)
- Events attended alongside each friend

**How it is built:**

```
GET /stats              — current user's stats
GET /stats/<username>   — another user's public stats
```

##  Installation & Running

```bash
# 1. Install dependencies
pip install flask werkzeug

# 2. Seed demo data
python seed.py

# 3. Run the app
python app.py

# 4. Open in browser
http://localhost:5000
```

### Monday
2.1, 2.2, 2.3
### Tuesday
2.4, 2.5
### Wednesday
2.7
### Thursday
2.8 
