"""
Seed script for RapidRelay.
Inserts realistic pre-extracted disaster triage sample records directly into SQLite.
Allows the dashboard and endpoints to be fully demoable without relying on live LLM API calls.
"""

import os
import sys
from datetime import datetime, timezone, timedelta

# Ensure backend package can be imported regardless of execution working directory
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

try:
    from backend.db.database import SessionLocal, engine, Base
    from backend.models.incident import Incident, NeedType, IncidentStatus
except ImportError:
    from db.database import SessionLocal, engine, Base
    from models.incident import Incident, NeedType, IncidentStatus


DEMO_INCIDENTS = [
    {
        "created_at": datetime.now(timezone.utc) - timedelta(minutes=45),
        "original_language": "Hindi",
        "original_text": "मदद करो! हमारे घर में पानी भर गया है, 4 लोग छत पर फंसे हैं और एक बच्चा बीमार है। पटना राजेंद्र नगर।",
        "translated_text": "Help! Water has flooded our house, 4 people are trapped on the roof and a child is sick. Patna Rajendra Nagar.",
        "location": "Rajendra Nagar, Patna, Bihar",
        "severity": 5,
        "need_type": NeedType.RESCUE,
        "people_affected": 4,
        "summary": "4 people trapped on roof with a sick child in floodwaters",
        "confidence": 0.95,
        "status": IncidentStatus.NEW,
    },
    {
        "created_at": datetime.now(timezone.utc) - timedelta(minutes=90),
        "original_language": "Tamil",
        "original_text": "சென்னையில் வேளச்சேரி பகுதியில் வெள்ளம் சூழ்ந்துள்ளது. வீட்டில் ஒரு கர்ப்பிணி பெண் இருக்கிறார், அவசர மருத்துவ உதவி தேவை.",
        "translated_text": "Velachery area in Chennai is surrounded by floods. A pregnant woman is at home and needs urgent medical assistance.",
        "location": "Velachery, Chennai, Tamil Nadu",
        "severity": 5,
        "need_type": NeedType.MEDICAL,
        "people_affected": 1,
        "summary": "Pregnant woman stranded in flooded home requires urgent medical care",
        "confidence": 0.98,
        "status": IncidentStatus.ACKNOWLEDGED,
    },
    {
        "created_at": datetime.now(timezone.utc) - timedelta(hours=3),
        "original_language": "Marathi",
        "original_text": "चिपळूणमध्ये जुने घर कोसळले आहे. दोन वृद्ध लोक मलब्याखाली अडकले आहेत, तातडीने मदत पाठवा.",
        "translated_text": "An old house has collapsed in Chiplun. Two elderly people are trapped under debris, send immediate help.",
        "location": "Chiplun, Ratnagiri, Maharashtra",
        "severity": 5,
        "need_type": NeedType.RESCUE,
        "people_affected": 2,
        "summary": "Two elderly people trapped under collapsed house debris",
        "confidence": 0.96,
        "status": IncidentStatus.DISPATCHED,
    },
    {
        "created_at": datetime.now(timezone.utc) - timedelta(hours=5),
        "original_language": "Hinglish / Bengali",
        "original_text": "Cyclone ke baad hamare gaon me no water supply for 3 days. Almost 50 villagers including children need clean drinking water and food packets.",
        "translated_text": "After the cyclone, there is no water supply in our village for 3 days. Almost 50 villagers including children need clean drinking water and food packets.",
        "location": "Contai, East Midnapore, West Bengal",
        "severity": 4,
        "need_type": NeedType.WATER,
        "people_affected": 50,
        "summary": "50 villagers lacking potable water and food for 3 days post-cyclone",
        "confidence": 0.92,
        "status": IncidentStatus.RESOLVED,
    },
]


def seed_database():
    print("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        existing_count = db.query(Incident).count()
        if existing_count > 0:
            print(f"Database already contains {existing_count} incident(s). Skipping duplicate seed or adding fresh...")

        added = 0
        for item in DEMO_INCIDENTS:
            # Check if this original text already exists
            exists = db.query(Incident).filter(Incident.original_text == item["original_text"]).first()
            if not exists:
                incident = Incident(**item)
                db.add(incident)
                added += 1

        db.commit()
        print(f"Successfully seeded {added} demo incident records into SQLite database.")
        
        total = db.query(Incident).count()
        print(f"Total incidents now in database: {total}")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
