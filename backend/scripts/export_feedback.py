"""Export (a_id, b_id, rating) from app feedback for ml/train_supervised.py. Writes pairs.csv + profiles_real.json"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pandas as pd
from backend.app.config import get_settings
from backend.app.db import get_db
from backend.app.services.matching import user_profile

get_settings(); db = get_db(); rows, profs = [], {}
for f in db.feedback.find({"partner_id": {"$ne": None}}):
    a, b = db.users.find_one({"_id": __import__("bson").ObjectId(f["user_id"])}), db.users.find_one({"_id": __import__("bson").ObjectId(f["partner_id"])})
    if a and b:
        for u in (a, b): profs[str(u["_id"])] = {**user_profile(u), "record_id": str(u["_id"])}
        rows.append((str(a["_id"]), str(b["_id"]), f["rating"]))
pd.DataFrame(rows, columns=["a_id", "b_id", "rating"]).to_csv("pairs.csv", index=False)
Path("profiles_real.json").write_text(json.dumps(list(profs.values())))
print(f"exported {len(rows)} labelled pairs")
