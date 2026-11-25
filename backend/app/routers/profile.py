from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from ..db import get_db
from ..deps import current_user
from ..schemas import ProfileIn, NameIn
from ..services import matching as M

router = APIRouter(prefix="/api", tags=["profile"])


def _me(user):
    from roomsync_ml import completeness
    prof = M.user_profile(user)
    frac, missing = completeness(prof)
    p = user.get("profile", {})
    return {"id": str(user["_id"]), "email": user["email"], "name": user["name"], "is_demo": bool(user.get("is_synthetic")),
            "answers": {k: v for k, v in prof.items() if k not in ("dealbreakers", "priorities") and v is not None},
            "dealbreakers": prof["dealbreakers"], "priorities": prof["priorities"],
            "completeness": round(frac, 3), "missing": missing, "profile_complete": not missing,
            "updated_at": p.get("updated_at")}


@router.get("/questionnaire")
def questionnaire():
    from roomsync_ml import schema as S
    return {"questions": S.questionnaire_spec(), "dealbreakers": S.DEALBREAKERS, "priorities": S.PRIORITIES,
            "max_priorities": S.MAX_PRIORITIES}


@router.get("/me")
def me(user=Depends(current_user)):
    return _me(user)


@router.patch("/me")
def rename(body: NameIn, user=Depends(current_user)):
    get_db().users.update_one({"_id": user["_id"]}, {"$set": {"name": body.name.strip()}})
    return _me(get_db().users.find_one({"_id": user["_id"]}))


@router.put("/profile")
def save_profile(body: ProfileIn, user=Depends(current_user)):
    """Create/replace the questionnaire. Partial drafts are saved; matching needs a complete profile."""
    from roomsync_ml import profile_from_answers, completeness
    from roomsync_ml.preprocess import ProfileError
    try:
        prof = profile_from_answers(body.answers, body.dealbreakers, body.priorities, strict=True)
    except ProfileError as e:
        raise HTTPException(422, str(e))
    _, missing = completeness(prof)
    answers = {k: v for k, v in prof.items() if k not in ("dealbreakers", "priorities") and v is not None}
    get_db().users.update_one({"_id": user["_id"]}, {"$set": {
        "profile": {"answers": answers, "dealbreakers": prof["dealbreakers"], "priorities": prof["priorities"],
                    "updated_at": datetime.now(timezone.utc).isoformat()},
        "profile_complete": not missing}})
    return _me(get_db().users.find_one({"_id": user["_id"]}))
