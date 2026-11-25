"""Load the 60 SYNTHETIC profiles as clearly labelled demo accounts + create a blank 'sample' account.
Usage (from repo root): python backend/scripts/seed_demo.py [--reset]
Demo logins: demo01@roomsync.demo ... demo60@roomsync.demo, password from DEMO_PASSWORD (default RoomSync-demo-1).
demo01..demo30 -> boys hostel pool, per the CSV order; every demo account is flagged is_synthetic=True."""
import json, sys
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.app.config import get_settings
from backend.app.db import get_db
from backend.app.security import hash_password


def seed(reset=False):
    s = get_settings(); db = get_db()
    profiles = json.loads((Path(s.ml_dir).parent / "datasets" / "processed" / "profiles.json").read_text())
    if reset:
        db.users.delete_many({"is_synthetic": True})
    pw = hash_password(s.demo_password); n = 0
    for i, p in enumerate(profiles, 1):
        email = f"demo{i:02d}@roomsync.demo"
        if db.users.find_one({"email": email}):
            continue
        answers = {k: v for k, v in p.items() if k in __import__("roomsync_ml").schema.QUESTIONS and v is not None}
        db.users.insert_one({"email": email, "name": f"Demo Student {i:02d}", "password_hash": pw, "is_synthetic": True,
                             "source_record": p["record_id"], "created_at": datetime.now(timezone.utc),
                             "profile": {"answers": answers, "dealbreakers": p["dealbreakers"], "priorities": p["priorities"]},
                             "profile_complete": True}); n += 1
    print(f"seeded {n} demo users ({db.users.count_documents({'is_synthetic': True})} total demo). Password: {s.demo_password}")


if __name__ == "__main__":
    seed("--reset" in sys.argv)
