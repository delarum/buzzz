"""seed.py — seed Nairobi demo events. Called automatically on first run."""
import sqlite3, os
from datetime import datetime, timedelta

DB_PATH = os.path.join("data", "buzzz.db")

def seed():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c    = conn.cursor()

    # Only seed if empty
    if c.execute("SELECT COUNT(*) FROM events").fetchone()[0] > 0:
        conn.close()
        return

    base = datetime.now()

    events = [
        ("Blankets & Wine Nairobi",
         "East Africa's favourite outdoor music festival returns to Ngong Racecourse. Live performances from top African artists, gourmet food stalls, and craft cocktails on the lawn.",
         "music", "Ngong Racecourse", "Ngong Road, Nairobi",
         -1.3183, 36.7947, base+timedelta(days=3,hours=15), 2500, 0, 350),

        ("Jazz in the Garden — Azmari",
         "An intimate jazz evening featuring Nairobi-based quartet Azmari performing original compositions blending Afrobeat rhythms with jazz improvisation.",
         "music", "Mawimbi Seafood", "Westlands, Nairobi",
         -1.2641, 36.8019, base+timedelta(days=1,hours=19), 800, 0, 120),

        ("Afro Fusion Nights",
         "Three stages. Twelve artists. One unforgettable night of Afropop, Bongo Flava, and Gengetone at the legendary Carnivore grounds.",
         "music", "Carnivore Restaurant", "Langata Road, Nairobi",
         -1.3333, 36.7833, base+timedelta(days=5,hours=18), 3000, 0, 500),

        ("Open Mic Nairobi",
         "Monthly open mic welcoming spoken word artists, singer-songwriters, and comedians. Walk-ins welcome, sign up at the door.",
         "music", "The Alchemist Bar", "Westlands, Nairobi",
         -1.2610, 36.8010, base+timedelta(days=2,hours=20), 0, 1, 80),

        ("Nairobi Street Food Festival",
         "The 10th edition of the most-loved food event in Nairobi. Over 80 vendors, cooking demos, cocktail masterclasses, and live entertainment.",
         "food", "ASK Showgrounds", "Ngong Road, Nairobi",
         -1.3100, 36.7883, base+timedelta(days=3,hours=10), 500, 0, 2000),

        ("Wine & Cheese Evening",
         "A curated wine tasting pairing eight South African and French wines with artisan cheeses, hosted by sommelier Wambui Njoroge.",
         "food", "Ole Sereni Hotel", "Mombasa Road, Nairobi",
         -1.3172, 36.8278, base+timedelta(days=6,hours=18), 3500, 0, 40),

        ("Coffee Origins Workshop",
         "Learn about Kenya's legendary coffee heritage. Cup six single-origin coffees, roast your own beans, and meet the farmers behind the cup.",
         "food", "Nairobi Coffee Exchange", "Westlands, Nairobi",
         -1.2621, 36.8044, base+timedelta(days=2,hours=10), 1500, 0, 30),

        ("Nairobi Dev Meetup",
         "Monthly gathering of software developers, designers, and product thinkers. Lightning talks, networking, and free pizza.",
         "tech", "iHub Nairobi", "Kilimani, Nairobi",
         -1.2894, 36.7826, base+timedelta(days=1,hours=17), 0, 1, 150),

        ("Startup Pitch Night",
         "Eight early-stage startups pitch to a panel of investors and the audience votes for their favourite. Prizes and connections guaranteed.",
         "tech", "Nailab", "Ralph Bunche Road, Nairobi",
         -1.2833, 36.8050, base+timedelta(days=7,hours=17), 500, 0, 200),

        ("AI Everything Kenya",
         "Kenya's largest AI and emerging technology conference. Keynotes, workshops, and a startup exhibition showcasing Africa's most innovative tech companies.",
         "tech", "KICC", "Harambee Avenue, Nairobi",
         -1.2889, 36.8247, base+timedelta(days=20), 5000, 0, 1200),

        ("GoDown Arts Centre Exhibition",
         "Twenty emerging Kenyan artists present mixed-media works exploring identity, climate, and urban life in contemporary Kenya.",
         "art", "GoDown Arts Centre", "Dunga Road, Nairobi",
         -1.3006, 36.8378, base+timedelta(days=0,hours=11), 0, 1, 80),

        ("Nairobi Design Week",
         "Five days of design talks, workshops, installations, and exhibitions. Theme: Designing for the African Climate.",
         "art", "Alliance Française", "Loita Street, Nairobi",
         -1.2889, 36.8189, base+timedelta(days=9), 0, 1, 500),

        ("Nairobi Trail Run — Karura",
         "A 10km trail run through Karura Forest at sunrise. Suitable for all fitness levels. Registration includes breakfast.",
         "outdoor", "Karura Forest", "Karura, Nairobi",
         -1.2372, 36.8358, base+timedelta(days=2,hours=6), 1200, 0, 300),

        ("Ngong Hills Hike",
         "A guided full-day hike across all seven Ngong Hills with stunning panoramic views of the Rift Valley. Moderate difficulty.",
         "outdoor", "Ngong Hills", "Ngong, Kajiado County",
         -1.4167, 36.6500, base+timedelta(days=4,hours=7), 1500, 0, 40),

        ("Yoga in the Park",
         "Free outdoor yoga session every Sunday morning at Uhuru Park. All levels welcome. Bring your own mat.",
         "outdoor", "Uhuru Park", "Uhuru Highway, Nairobi",
         -1.2927, 36.8177, base+timedelta(days=2,hours=8), 0, 1, 60),

        ("Nairobi International Marathon",
         "The annual 42km marathon through the heart of Nairobi. Categories: 5km fun run, 10km, 21km, full marathon.",
         "sports", "Nyayo Stadium", "Mombasa Road, Nairobi",
         -1.3108, 36.8264, base+timedelta(days=14,hours=6), 2000, 0, 5000),

        ("Short Film Saturday — KWFF",
         "Kenya Women Film Festival presents a curated afternoon of short films by East African women filmmakers followed by a Q&A.",
         "film", "Prestige Cinema", "Ngong Road, Nairobi",
         -1.3039, 36.7908, base+timedelta(days=1,hours=14), 500, 0, 120),

        ("Outdoor Cinema Night",
         "A classic film under the stars at the Arboretum. Bring a blanket, picnic food and enjoy the big screen in the open air.",
         "film", "Nairobi Arboretum", "State House Road, Nairobi",
         -1.2756, 36.8133, base+timedelta(days=6,hours=19), 700, 0, 200),

        ("Young Professionals Nairobi",
         "Monthly networking evening for professionals under 35. Speed networking format followed by drinks and open mingling.",
         "networking", "Java House Garden", "Westlands, Nairobi",
         -1.2641, 36.8019, base+timedelta(days=3,hours=18), 1000, 0, 100),

        ("Women in Business Breakfast",
         "Quarterly power breakfast for women entrepreneurs and executives. Guest speaker: CEO of one of Kenya's fastest-growing fintechs.",
         "networking", "Serena Hotel", "Processional Way, Nairobi",
         -1.2889, 36.8089, base+timedelta(days=10,hours=7), 2500, 0, 80),
    ]

    for ev in events:
        (title, desc, cat, loc, addr, lat, lng, dt, price, is_free, att) = ev
        c.execute("""INSERT INTO events
            (source,title,description,category,location_name,address,
             lat,lng,date_time,price,is_free,attendee_count)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            ("local", title, desc, cat, loc, addr, lat, lng,
             dt.strftime("%Y-%m-%d %H:%M:%S"), price, is_free, att))

    conn.commit()
    conn.close()
    print(f"  Seeded {len(events)} Nairobi events.")

if __name__ == "__main__":
    seed()