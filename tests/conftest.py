import os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
os.environ.update(MONGODB_URI="mongomock://", JWT_SECRET="test-secret", ENV="test")
sys.path[:0] = [str(ROOT), str(ROOT / "ml")]
import json, pytest

@pytest.fixture(scope="session")
def profiles():
    return json.loads((ROOT / "datasets/processed/profiles.json").read_text())

@pytest.fixture(scope="session")
def engine():
    from roomsync_ml import CompatibilityEngine
    from roomsync_ml.embedding import LatentModel
    return CompatibilityEngine(LatentModel.load(ROOT / "models/latent_model.joblib"))

BASE = dict(year="2nd", hostel="Boys hostel", bedtime="11 PM - 1 AM", wake="6 - 8 AM", light_tolerance=3,
            climate="Fan only", tidiness=3, clearing="Same day", study_time="Evening",
            study_env="Low background noise is fine", gaming="1 - 2 hours", audio="Mostly headphones", calls=2,
            guest_freq=3, guest_comfort=4, weekend="Mix of in and out", food="Vegetarian",
            nonveg_comfort="Yes", room_eating=2, conflict="Bring it up calmly later", sharing=3,
            alone_time=3, relationship="Friendly but independent")

@pytest.fixture
def base_answers():
    return dict(BASE)
