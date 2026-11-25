"""University bulk roommate matching from an uploaded CSV.

The CSV is processed in memory and is not persisted. Access is protected by a
university-admin shared key configured through UNIVERSITY_ADMIN_KEY.
"""
from __future__ import annotations

import csv
import io
import secrets
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from ..config import get_settings
from ..services import matching as M

router = APIRouter(prefix="/api/university", tags=["university"])


class CsvMatchRequest(BaseModel):
    csv_text: str = Field(min_length=20, max_length=5_000_000)
    mode: str = Field(default="both")


def _authorize(x_university_admin_key: str | None):
    configured = get_settings().university_admin_key
    if not configured:
        raise HTTPException(503, "University admin is not configured. Set UNIVERSITY_ADMIN_KEY in the backend .env.")
    if not x_university_admin_key or not secrets.compare_digest(x_university_admin_key, configured):
        raise HTTPException(401, "Invalid university admin key")


def _pick(row: dict[str, Any], names: tuple[str, ...], fallback: str) -> str:
    lower = {str(k).strip().lower(): v for k, v in row.items() if k is not None}
    for name in names:
        value = lower.get(name.lower())
        if value is not None and str(value).strip():
            return str(value).strip()
    return fallback


@router.post("/matches")
def university_matches(body: CsvMatchRequest, x_university_admin_key: str | None = Header(default=None)):
    """Return per-student top-2 suggestions and one-to-one exclusive pairs."""
    _authorize(x_university_admin_key)
    if body.mode != "both":
        raise HTTPException(422, "This endpoint currently supports mode='both'.")

    from roomsync_ml import profile_from_survey_row, completeness
    from roomsync_ml.preprocess import ProfileError

    try:
        reader = csv.DictReader(io.StringIO(body.csv_text.lstrip("\ufeff")))
        if not reader.fieldnames:
            raise HTTPException(422, "CSV has no header row.")
        rows = list(reader)
    except csv.Error as exc:
        raise HTTPException(422, f"Could not parse CSV: {exc}")

    if len(rows) < 2:
        raise HTTPException(422, "Upload at least two student rows.")
    if len(rows) > 500:
        raise HTTPException(413, "Maximum supported upload is 500 students per run.")

    students = []
    errors = []
    seen_ids = set()
    for index, row in enumerate(rows, start=2):
        if not any(str(v or "").strip() for v in row.values()):
            continue
        sid = _pick(row, ("Student ID", "Registration Number", "Roll Number", "Email Address", "Email address", "Email"), f"student-{index-1}")
        name = _pick(row, ("Student Name", "Full Name", "Name"), sid)
        if sid in seen_ids:
            errors.append(f"Row {index}: duplicate student identifier '{sid}'.")
            continue
        seen_ids.add(sid)
        try:
            profile = profile_from_survey_row(row)
            _, missing = completeness(profile)
            if missing:
                errors.append(f"Row {index} ({sid}): missing required answers: {', '.join(missing)}.")
                continue
            students.append({"id": sid, "name": name, "profile": profile})
        except ProfileError as exc:
            errors.append(f"Row {index} ({sid}): {exc}")

    if errors:
        raise HTTPException(422, {"message": "CSV validation failed. Fix the listed rows and upload again.",
                                  "errors": errors[:30], "error_count": len(errors)})
    if len(students) < 2:
        raise HTTPException(422, "At least two valid, complete student profiles are required.")

    engine = M.get_engine()
    # Individual recommendations: top 2 eligible students for every student.
    individual = []
    for student in students:
        ranked = engine.rank(
            student["profile"],
            [(other["id"], other["profile"]) for other in students],
            k=2, strict=True, user_id=student["id"],
        )
        individual.append({
            "student_id": student["id"],
            "student_name": student["name"],
            "matches": [
                {"student_id": item["id"],
                 "student_name": next(x["name"] for x in students if x["id"] == item["id"]),
                 "score": round(item["result"].score, 1),
                 "label": item["result"].label,
                 "top_strengths": item["result"].strengths[:2]}
                for item in ranked
            ],
        })

    # Exclusive assignment: sort eligible undirected pairs by compatibility and
    # greedily accept an edge only when neither student has already been assigned.
    # This is deterministic and one-to-one, but is not claimed to be a globally
    # optimal maximum-weight matching.
    edges = []
    for i, a in enumerate(students):
        for b in students[i + 1:]:
            if a["profile"].get("hostel") != b["profile"].get("hostel"):
                continue
            result = engine.pair(a["profile"], b["profile"])
            if not result.blocked:
                edges.append((result.score, a, b, result))
    edges.sort(key=lambda edge: (-edge[0], edge[1]["id"], edge[2]["id"]))
    assigned = set()
    pairs = []
    for score, a, b, result in edges:
        if a["id"] in assigned or b["id"] in assigned:
            continue
        assigned.update((a["id"], b["id"]))
        pairs.append({
            "pair_number": len(pairs) + 1,
            "student_1_id": a["id"], "student_1_name": a["name"],
            "student_2_id": b["id"], "student_2_name": b["name"],
            "score": round(score, 1), "label": result.label,
        })

    unmatched = [{"student_id": s["id"], "student_name": s["name"]}
                 for s in students if s["id"] not in assigned]
    return {
        "mode": "both",
        "students_processed": len(students),
        "individual_top2": individual,
        "exclusive_pairs": pairs,
        "unmatched_students": unmatched,
        "allocation_method": "Greedy highest-compatible-pair-first; each student appears in at most one pair. This is not guaranteed to be globally optimal.",
        "disclaimer": M.DISCLAIMER + " Results depend on the uploaded questionnaire data and are not validated against actual roommate outcomes.",
    }
