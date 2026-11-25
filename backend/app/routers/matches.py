from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime, timezone
from ..db import get_db
from ..deps import current_user, oid
from ..schemas import FeedbackIn
from ..services import matching as M

router = APIRouter(prefix="/api", tags=["matching"])


def _require_complete(user):
    from roomsync_ml import completeness
    frac, missing = completeness(M.user_profile(user))
    if missing:
        raise HTTPException(409, {"message": "Complete the questionnaire to see matches", "missing": missing})


@router.get("/matches")
def matches(k: int = Query(10, ge=1, le=50), strict: bool = True, include_demo: bool = True,
            user=Depends(current_user)):
    _require_complete(user)
    me = M.user_profile(user)
    cands = M.candidates_for(user, include_demo)
    by_id = {str(u["_id"]): (u, p) for u, p in cands}
    eng = M.get_engine()
    ranked = eng.rank(me, [(i, p) for i, (_, p) in by_id.items()], k=k, strict=strict, user_id=str(user["_id"]))
    emb = eng.embedder
    out = []
    for rank, r in enumerate(ranked, 1):
        u, p = by_id[r["id"]]
        res = r["result"].to_dict()
        out.append({**M.public_card(u, p), "rank": rank, "score": res["score"], "label": res["label"],
                    "confidence": res["confidence"], "blocked": res["blocked"],
                    "top_strengths": res["strengths"][:2], "top_mismatches": res["mismatches"][:2],
                    "dealbreaker_count": len(res["dealbreakers"])})
    # how many were excluded (transparent about filtering)
    total_pool = sum(1 for _, p in cands if p.get("hostel") == me.get("hostel"))
    return {"matches": out, "pool_size": total_pool, "returned": len(out), "strict": strict,
            "excluded_by_dealbreakers": (total_pool - len(eng.rank(me, [(i, p) for i, (_, p) in by_id.items()], None, True, str(user["_id"])))) if strict else 0,
            "disclaimer": M.DISCLAIMER, "model": {"latent": emb is not None, "residual": eng.residual is not None}}


@router.get("/matches/{other_id}")
def match_detail(other_id: str, user=Depends(current_user)):
    _require_complete(user)
    other = get_db().users.find_one({"_id": oid(other_id)})
    if not other or other["_id"] == user["_id"]:
        raise HTTPException(404, "Student not found")
    op = M.user_profile(other)
    me = M.user_profile(user)
    if me.get("hostel") != op.get("hostel"):
        raise HTTPException(404, "Student not found")  # not an eligible roommate
    from roomsync_ml import completeness
    if completeness(op)[1]:
        raise HTTPException(404, "Student has not completed their profile")
    res = M.get_engine().pair(me, op).to_dict()
    other_answers = {k: v for k, v in op.items() if k not in ("dealbreakers", "priorities") and v is not None}
    return {"student": M.public_card(other, op), "result": res,
            "comparison": [{"key": k, "you": me.get(k), "them": other_answers.get(k)} for k in other_answers],
            "disclaimer": M.DISCLAIMER}


@router.post("/feedback", status_code=201)
def feedback(body: FeedbackIn, user=Depends(current_user)):
    """Rating of an actual roommate relationship (1-5). This is the only source of real training labels."""
    doc = {"user_id": str(user["_id"]), "partner_id": body.partner_id, "rating": body.rating, "note": body.note,
           "created_at": datetime.now(timezone.utc)}
    get_db().feedback.insert_one(doc)
    return {"ok": True}


@router.get("/stats")
def stats(user=Depends(current_user)):
    db = get_db()
    me = M.user_profile(user)
    from roomsync_ml import completeness
    frac, missing = completeness(me)
    out = {"profiles_total": db.users.count_documents({}), "profiles_complete": db.users.count_documents({"profile_complete": True}),
           "real_signups": db.users.count_documents({"is_synthetic": {"$ne": True}}), "my_completeness": round(frac, 3),
           "my_missing": missing, "feedback_labels_collected": db.feedback.count_documents({"partner_id": {"$ne": None}})}
    if not missing:
        r = M.get_engine().rank(me, [(str(u["_id"]), p) for u, p in M.candidates_for(user)], k=None, strict=True, user_id=str(user["_id"]))
        sc = [x["result"].score for x in r]
        out.update({"eligible_matches": len(sc), "best_score": round(max(sc), 1) if sc else None,
                    "avg_top5": round(sum(sc[:5]) / len(sc[:5]), 1) if sc else None})
    return out
