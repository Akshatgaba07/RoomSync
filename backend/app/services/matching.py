"""Glue between the database and the ml/ engine."""
from functools import lru_cache
from pathlib import Path
from ..config import get_settings
from ..db import get_db

DISCLAIMER = ("This is a compatibility estimate from questionnaire answers using a rule-based + "
              "unsupervised model. It is not validated against real roommate outcomes and is not a "
              "guarantee of a good (or bad) living arrangement.")


@lru_cache
def get_engine():
    get_settings()
    from roomsync_ml import CompatibilityEngine
    from roomsync_ml.embedding import LatentModel
    models = Path(get_settings().models_dir)
    emb = LatentModel.load(models / "latent_model.joblib") if (models / "latent_model.joblib").exists() else None
    residual = None
    fm = models / "feedback_model.joblib"
    if fm.exists():  # only exists if trained on real feedback (train_supervised.py refuses <150 labels)
        import sys; sys.path.insert(0, get_settings().ml_dir)
        from residual import ResidualModel
        residual = ResidualModel.load(fm)
    return CompatibilityEngine(embedder=emb, residual=residual)


def user_profile(user: dict) -> dict:
    from roomsync_ml import profile_from_answers
    p = user.get("profile") or {}
    return profile_from_answers(p.get("answers", {}), p.get("dealbreakers", []), p.get("priorities", []), strict=False)


def public_card(user: dict, prof: dict) -> dict:
    return {"id": str(user["_id"]), "name": user["name"], "year": prof.get("year"), "hostel": prof.get("hostel"),
            "is_demo": bool(user.get("is_synthetic")), "priorities": prof.get("priorities", []),
            "dealbreakers": prof.get("dealbreakers", [])}


def candidates_for(user: dict, include_demo: bool = True):
    from roomsync_ml import is_complete
    q = {"_id": {"$ne": user["_id"]}, "profile_complete": True}
    if not include_demo:
        q["is_synthetic"] = {"$ne": True}
    out = []
    for u in get_db().users.find(q):
        prof = user_profile(u)
        if is_complete(prof):
            out.append((u, prof))
    return out
