"""Hybrid pairwise compatibility engine.

score = 100 * penalty * ((1 - alpha) * rule_score + alpha * latent_similarity)

* rule_score    : importance-weighted mean of 12 domain-designed dimension scores in [0, 1]
                  (weights personalised by each student's top-3 priorities, symmetric in the pair).
* latent_sim    : Gaussian-kernel similarity in a PCA latent space fitted (unsupervised) on the
                  profile corpus. Optional; the engine works without it.
* penalty       : multiplicative penalty when a dimension *either student ranked as a top priority*
                  scores very low (a plain mean can hide a critical clash).
* hard constraints (dealbreakers) are checked in BOTH directions and never averaged away: in strict
  mode the pair is excluded; otherwise the score is capped and the conflict is reported.
* residual model: an optional supervised model trained on real roommate-satisfaction feedback
  (see ml/train_supervised.py). It is only blended in when such a model file has been trained on
  real labels; otherwise the engine is purely rule-based + unsupervised.

No compatibility "label" is invented anywhere: the dimension rules encode documented domain
logic (see docs/METHODOLOGY.md) and are not claimed to be validated against real outcomes.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from typing import Any, Mapping, Sequence

from . import schema as S
from .preprocess import ordinal01

ALPHA_LATENT = 0.20
BLOCKED_SCORE_CAP = 39.0
PRIORITY_PENALTY_THRESHOLD = 0.35
PRIORITY_PENALTY = 0.92  # per critical dimension, floor 0.78
STRENGTH_T, MISMATCH_T = 0.75, 0.50

nan = float("nan")


def _isnan(x) -> bool:
    return x is None or (isinstance(x, float) and math.isnan(x))


def _ans(p: Mapping, k: str) -> str:
    v = p.get(k)
    return "not answered" if v is None else str(v)


def _clip(x: float) -> float:
    return max(0.0, min(1.0, x))


def _o(p, k):
    return ordinal01(p, k)


def _opt_idx(p, k):
    v = p.get(k)
    return None if v is None else S.QUESTIONS[k]["options"].index(v)


# ------------------------------------------------------------------ dimension scorers
# Each returns (score in [0,1] or None when data are missing, short factual note).
def d_sleep(a, b):
    ba, bb, wa, wb = _o(a, "bedtime"), _o(b, "bedtime"), _o(a, "wake"), _o(b, "wake")
    parts, w = [], []
    if not (_isnan(ba) or _isnan(bb)):
        parts.append(abs(ba - bb) ** 0.8), w.append(0.55)
    if not (_isnan(wa) or _isnan(wb)):
        parts.append(abs(wa - wb) ** 0.8), w.append(0.45)
    if not parts:
        return None, "sleep schedule not answered"
    score = 1 - sum(p * x for p, x in zip(parts, w)) / sum(w)
    # The earlier sleeper is disturbed more when they are a light sleeper.
    if not (_isnan(ba) or _isnan(bb)):
        earlier = a if ba <= bb else b
        lt = _o(earlier, "light_tolerance")
        if not _isnan(lt):
            score -= 0.25 * abs(ba - bb) * (1 - lt)
    note = (f"Bedtime {_ans(a,'bedtime')} vs {_ans(b,'bedtime')}; "
            f"wake-up {_ans(a,'wake')} vs {_ans(b,'wake')}")
    return _clip(score), note


_STUDY_SENS = {"Total silence": 1.0, "Low background noise is fine": 0.6,
               "Music with headphones": 0.3, "Anything works, I don't mind": 0.0}


def _emission(p):
    vals = [(_o(p, "audio"), 0.4), (_o(p, "gaming"), 0.35), (_o(p, "calls"), 0.25)]
    vals = [(v, w) for v, w in vals if not _isnan(v)]
    if not vals:
        return nan
    return sum(v * w for v, w in vals) / sum(w for _, w in vals)


def d_noise_study(a, b):
    sa, sb = _STUDY_SENS.get(a.get("study_env")), _STUDY_SENS.get(b.get("study_env"))
    ea, eb = _emission(a), _emission(b)
    if sa is None or sb is None or _isnan(ea) or _isnan(eb):
        return None, "study environment or noise habits not answered"
    fab, fba = sa * eb, sb * ea
    friction = 0.7 * max(fab, fba) + 0.3 * (fab + fba) / 2
    score = 1 - min(1.0, 1.4 * friction)
    ta, tb = _opt_idx(a, "study_time"), _opt_idx(b, "study_time")
    if ta is not None and tb is not None and abs(ta - tb) == 2 and max(sa, sb) >= 0.6:
        score -= 0.1
    note = (f"Study setting: {_ans(a,'study_env')} vs {_ans(b,'study_env')}; "
            f"calls {_ans(a,'calls')}/5 vs {_ans(b,'calls')}/5")
    return _clip(score), note


def d_cleanliness(a, b):
    ta, tb, ca, cb = _o(a, "tidiness"), _o(b, "tidiness"), _o(a, "clearing"), _o(b, "clearing")
    parts, w = [], []
    if not (_isnan(ta) or _isnan(tb)):
        parts.append(abs(ta - tb)), w.append(0.6)
    if not (_isnan(ca) or _isnan(cb)):
        parts.append(abs(ca - cb)), w.append(0.4)
    if not parts:
        return None, "cleanliness not answered"
    pen = sum(p * x for p, x in zip(parts, w)) / sum(w)
    tidy = max(x for x in (ta, tb) if not _isnan(x)) if not (_isnan(ta) and _isnan(tb)) else 0.5
    score = 1 - min(1.0, pen * 1.25 * (0.8 + 0.4 * tidy))
    note = (f"Tidiness {_ans(a,'tidiness')}/5 vs {_ans(b,'tidiness')}/5; "
            f"clears mess: {_ans(a,'clearing')} vs {_ans(b,'clearing')}")
    return _clip(score), note


_NONVEG = {"Vegetarian": 0.0, "Eggetarian": 0.4, "Non-vegetarian": 1.0, "Jain / other restrictions": 0.0}
_TOL = {"Yes": 1.0, "Only if it's not smelly / cleaned up": 0.55, "No": 0.0}


def _tolerance(p):
    t = _TOL.get(p.get("nonveg_comfort"))
    if p.get("food") == "Jain / other restrictions" and t is not None:
        t = min(t, 0.2)
    return t


def _nv_exposure(p):
    nv = _NONVEG.get(p.get("food"))
    if nv is None:
        return None
    re_ = _o(p, "room_eating")
    re_ = 0.5 if _isnan(re_) else re_
    return nv * (0.35 + 0.65 * re_)


def d_food(a, b):
    dirs = []
    for x, y in ((a, b), (b, a)):  # does x tolerate y's non-veg exposure?
        tol, exp = _tolerance(x), _nv_exposure(y)
        if tol is not None and exp is not None:
            dirs.append(1 - exp * (1 - tol))
    if not dirs:
        return None, "food preferences not answered"
    score = min(dirs)
    ra, rb = _o(a, "room_eating"), _o(b, "room_eating")
    if not (_isnan(ra) or _isnan(rb)):
        score = 0.8 * score + 0.2 * (1 - abs(ra - rb))
    note = (f"Diet {_ans(a,'food')} vs {_ans(b,'food')}; non-veg in room: "
            f"{_ans(a,'nonveg_comfort')} / {_ans(b,'nonveg_comfort')}")
    return _clip(score), note


_CLIMATE = {frozenset(["Windows open, nothing on"]): 1, frozenset(["Fan only"]): 1,
            frozenset(["AC or cooler on all night"]): 1, frozenset(["No preference"]): 1,
            frozenset(["Windows open, nothing on", "Fan only"]): 0.7,
            frozenset(["Fan only", "AC or cooler on all night"]): 0.5,
            frozenset(["Windows open, nothing on", "AC or cooler on all night"]): 0.1}


def d_climate(a, b):
    ca, cb = a.get("climate"), b.get("climate")
    if ca is None or cb is None:
        return None, "night-time climate preference not answered"
    s = _CLIMATE.get(frozenset([ca, cb]), 0.85 if "No preference" in (ca, cb) else 0.6)
    return s, f"Night-time: {ca} vs {cb}"


def d_entertainment(a, b):
    ga, gb, aa, ab = _o(a, "gaming"), _o(b, "gaming"), _o(a, "audio"), _o(b, "audio")
    parts = []
    if not (_isnan(ga) or _isnan(gb)):
        parts.append(abs(ga - gb))
    if not (_isnan(aa) or _isnan(ab)):
        parts.append(abs(aa - ab))
    if not parts:
        return None, "gaming / audio habits not answered"
    return _clip(1 - sum(parts) / len(parts)), (
        f"Gaming {_ans(a,'gaming')} vs {_ans(b,'gaming')}; audio {_ans(a,'audio')} vs {_ans(b,'audio')}")


def d_guests(a, b):
    fa, fb, ca, cb = _o(a, "guest_freq"), _o(b, "guest_freq"), _o(a, "guest_comfort"), _o(b, "guest_comfort")
    fr = []
    if not (_isnan(fb) or _isnan(ca)):
        fr.append(fb * (1 - ca))
    if not (_isnan(fa) or _isnan(cb)):
        fr.append(fa * (1 - cb))
    if not fr:
        return None, "guest habits not answered"
    score = 1 - min(1.0, 1.3 * max(fr))
    if not (_isnan(fa) or _isnan(fb)):
        score = 0.7 * score + 0.3 * (1 - abs(fa - fb))
    note = (f"Hosts friends {_ans(a,'guest_freq')}/5 vs {_ans(b,'guest_freq')}/5; "
            f"comfort with guests {_ans(a,'guest_comfort')}/5 vs {_ans(b,'guest_comfort')}/5")
    return _clip(score), note


_WK = {"Mostly in the hostel": 0, "Mix of in and out": 1, "Mostly out with friends": 2, "I go home often": 3}
_WK_M = {(0, 0): .75, (0, 1): .85, (0, 2): .9, (0, 3): 1.0, (1, 1): 1.0, (1, 2): .9, (1, 3): .95,
         (2, 2): .9, (2, 3): .9, (3, 3): .9}
_WK_PRESENCE = {0: 1.0, 1: 0.55, 2: 0.3, 3: 0.0}


def d_weekend(a, b):
    wa, wb = _WK.get(a.get("weekend")), _WK.get(b.get("weekend"))
    if wa is None or wb is None:
        return None, "weekend lifestyle not answered"
    return _WK_M[tuple(sorted((wa, wb)))], f"Weekends: {a['weekend']} vs {b['weekend']}"


def _presence(p):
    parts = []
    g = _o(p, "guest_freq")
    if not _isnan(g):
        parts.append(g)
    w = _WK.get(p.get("weekend"))
    if w is not None:
        parts.append(_WK_PRESENCE[w])
    return sum(parts) / len(parts) if parts else nan


def d_privacy(a, b):
    la, lb, pa, pb = _o(a, "alone_time"), _o(b, "alone_time"), _presence(a), _presence(b)
    fr = []
    if not (_isnan(la) or _isnan(pb)):
        fr.append(la * pb)
    if not (_isnan(lb) or _isnan(pa)):
        fr.append(lb * pa)
    if not fr:
        return None, "privacy needs not answered"
    return _clip(1 - min(1.0, 1.2 * max(fr))), (
        f"Alone time needed {_ans(a,'alone_time')}/5 vs {_ans(b,'alone_time')}/5 "
        f"against how often the other is in the room")


def d_sharing(a, b):
    x, y = _o(a, "sharing"), _o(b, "sharing")
    if _isnan(x) or _isnan(y):
        return None, "sharing attitude not answered"
    return _clip(1 - 1.1 * abs(x - y)), f"Sharing attitude {_ans(a,'sharing')}/5 vs {_ans(b,'sharing')}/5"


_CS = {"Say it directly, right away": "D", "Bring it up calmly later": "C",
       "Hint at it indirectly": "I", "Stay quiet and avoid conflict": "A"}
_CS_M = {("D", "D"): .85, ("C", "D"): .95, ("D", "I"): .55, ("A", "D"): .3, ("C", "C"): 1.0,
         ("C", "I"): .65, ("A", "C"): .6, ("I", "I"): .5, ("A", "I"): .35, ("A", "A"): .25}


def d_conflict(a, b):
    ca, cb = _CS.get(a.get("conflict")), _CS.get(b.get("conflict"))
    if ca is None or cb is None:
        return None, "conflict style not answered"
    return _CS_M[tuple(sorted((ca, cb)))], f"When bothered: {a['conflict']} vs {b['conflict']}"


def d_relationship(a, b):
    x, y = _o(a, "relationship"), _o(b, "relationship")
    if _isnan(x) or _isnan(y):
        return None, "desired relationship not answered"
    s = {0.0: 1.0, 0.5: 0.55, 1.0: 0.1}[round(abs(x - y) * 2) / 2]
    return s, f"Wants: {_ans(a,'relationship')} vs {_ans(b,'relationship')}"


DIM_FUNCS = {"sleep": d_sleep, "noise_study": d_noise_study, "cleanliness": d_cleanliness, "food": d_food,
             "climate": d_climate, "entertainment": d_entertainment, "guests": d_guests,
             "weekend": d_weekend, "privacy": d_privacy, "sharing": d_sharing, "conflict": d_conflict,
             "relationship": d_relationship}
DIM_ORDER = list(DIM_FUNCS)


# ------------------------------------------------------------------ hard constraints
def _late(p):
    i = _opt_idx(p, "bedtime")
    return None if i is None else i >= 2


def _violation(db: str, p: Mapping) -> tuple[bool | None, str]:
    """Does profile p exhibit the behaviour named by dealbreaker `db`? (None = cannot tell)."""
    if db == "Keeps lights / noise on late at night":
        late = _late(p)
        if late is None:
            return None, ""
        loud = (p.get("study_time") == "Late night (after midnight)" or (_opt_idx(p, "gaming") or 0) >= 2
                or (_opt_idx(p, "audio") or 0) >= 2)
        return late and loud, f"goes to bed {p.get('bedtime')} and stays active late"
    if db == "Takes loud calls at night":
        late, c = _late(p), p.get("calls")
        if late is None or c is None:
            return None, ""
        return late and c >= 4, f"late bedtime ({p.get('bedtime')}) with frequent calls ({c}/5)"
    if db == "Plays music or videos on speaker":
        i = _opt_idx(p, "audio")
        return (None, "") if i is None else (i >= 2, f"audio habit: {p.get('audio')}")
    if db == "Eats non-veg in the room":
        f, r = p.get("food"), p.get("room_eating")
        if f is None or r is None:
            return None, ""
        return f == "Non-vegetarian" and r >= 3, f"non-vegetarian who eats in the room ({r}/5)"
    if db == "Has overnight guests often":
        g = p.get("guest_freq")
        return (None, "") if g is None else (g >= 4, f"hosts friends in the room often ({g}/5)")
    if db == "Keeps the room messy":
        t = p.get("tidiness")
        return (None, "") if t is None else (t <= 2, f"tidiness {t}/5")
    if db == "Drinks alcohol in the room":
        v = p.get("alcohol_in_room")
        return (None, "") if v is None else (v == "Yes", "drinks alcohol in the room")
    if db == "Smokes / vapes":
        v = p.get("smokes")
        return (None, "") if v is None else (v == "Yes", "smokes / vapes")
    return None, ""


def check_hard_constraints(a: Mapping, b: Mapping) -> tuple[list[dict], list[dict]]:
    """Both directions. Returns (violations, unverifiable)."""
    viol, unk = [], []
    for who, x, y in (("you", a, b), ("them", b, a)):  # x's dealbreakers applied to y's behaviour
        for db in x.get("dealbreakers") or []:
            v, ev = _violation(db, y)
            who_text = "Your dealbreaker" if who == "you" else "Their dealbreaker"
            if v is None:
                if db in ("Drinks alcohol in the room", "Smokes / vapes") or ev == "":
                    unk.append({"owner": who, "dealbreaker": db,
                                "message": f"{who_text} \u201c{db}\u201d cannot be verified: the other "
                                           f"student has not answered that question."})
            elif v:
                viol.append({"owner": who, "dealbreaker": db, "kind": "dealbreaker",
                             "message": f"{who_text} \u201c{db}\u201d is triggered ({ev})."})
        # Declared hard comfort limit on non-veg (only if not already a dealbreaker)
        if "Eats non-veg in the room" not in (x.get("dealbreakers") or []):
            tol, exp = _tolerance(x), _nv_exposure(y)
            if tol == 0.0 and exp is not None and exp >= 0.65:
                viol.append({"owner": who, "dealbreaker": "Not comfortable with non-veg in the room",
                             "kind": "stated_constraint",
                             "message": ("You said you are not comfortable with" if who == "you"
                                         else "They said they are not comfortable with")
                                        + " a roommate eating non-veg in the room, and the other student "
                                          "is non-vegetarian and eats in the room."})
    return viol, unk


# ------------------------------------------------------------------ result container
@dataclass
class PairResult:
    score: float
    label: str
    rule_score: float
    latent_similarity: float | None
    confidence: float
    blocked: bool
    dimensions: list[dict] = field(default_factory=list)
    dealbreakers: list[dict] = field(default_factory=list)
    unverified: list[dict] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    mismatches: list[str] = field(default_factory=list)
    residual_used: bool = False

    def to_dict(self) -> dict:
        d = asdict(self)
        for k in ("score", "rule_score", "confidence"):
            d[k] = round(d[k], 4 if k != "score" else 1)
        if d["latent_similarity"] is not None:
            d["latent_similarity"] = round(d["latent_similarity"], 4)
        return d


def score_label(score: float, blocked: bool) -> str:
    if blocked:
        return "Dealbreaker conflict"
    if score >= 80:
        return "Excellent match"
    if score >= 65:
        return "Good match"
    if score >= 50:
        return "Workable with some compromise"
    return "Low compatibility"


class CompatibilityEngine:
    def __init__(self, embedder=None, residual=None, alpha: float = ALPHA_LATENT,
                 priority_boost: float = S.PRIORITY_BOOST, residual_weight: float = 0.3):
        self.embedder, self.residual, self.alpha = embedder, residual, alpha
        self.priority_boost, self.residual_weight = priority_boost, residual_weight

    # -- weights ---------------------------------------------------------
    def pair_weights(self, a, b) -> dict[str, float]:
        w = {}
        for key, d in S.DIMENSIONS.items():
            pr = d["priority"]
            hits = sum(1 for p in (a, b) if pr and pr in (p.get("priorities") or [])) / 2
            w[key] = d["base"] * (1 + (self.priority_boost - 1) * hits)
        return w

    def dimension_scores(self, a, b) -> dict[str, tuple[float | None, str]]:
        return {k: f(a, b) for k, f in DIM_FUNCS.items()}

    # -- main ------------------------------------------------------------
    def pair(self, a: Mapping, b: Mapping) -> PairResult:
        dims = self.dimension_scores(a, b)
        w = self.pair_weights(a, b)
        avail = {k: v for k, (v, _) in dims.items() if v is not None}
        total_w = sum(w.values())
        w_av = sum(w[k] for k in avail)
        rule = sum(w[k] * v for k, v in avail.items()) / w_av if w_av else 0.5
        confidence = w_av / total_w

        penalty = 1.0
        prio_a, prio_b = set(a.get("priorities") or []), set(b.get("priorities") or [])
        for k, v in avail.items():
            pr = S.DIMENSIONS[k]["priority"]
            if pr and (pr in prio_a or pr in prio_b) and v < PRIORITY_PENALTY_THRESHOLD:
                penalty *= PRIORITY_PENALTY
        penalty = max(penalty, 0.78)

        latent = None
        if self.embedder is not None:
            latent = float(self.embedder.similarity(a, b))
            base = (1 - self.alpha) * rule + self.alpha * latent
        else:
            base = rule
        score = 100 * base * penalty

        residual_used = False
        if self.residual is not None:
            pred = self.residual.predict_score(self.pair_features(a, b, dims, latent))
            score = (1 - self.residual_weight) * score + self.residual_weight * pred
            residual_used = True

        viol, unk = check_hard_constraints(a, b)
        blocked = bool(viol)
        if blocked:
            score = min(score, BLOCKED_SCORE_CAP)
        score = max(0.0, min(100.0, score))

        dim_out, strengths, mism = [], [], []
        for k in DIM_ORDER:
            v, note = dims[k]
            if v is None:
                verdict = "unknown"
            elif v >= STRENGTH_T:
                verdict = "strength"
            elif v < MISMATCH_T:
                verdict = "mismatch"
            else:
                verdict = "neutral"
            dim_out.append({"key": k, "label": S.DIMENSIONS[k]["label"],
                            "score": None if v is None else round(v, 3), "weight": round(w[k], 3),
                            "priority": bool(S.DIMENSIONS[k]["priority"] and (
                                S.DIMENSIONS[k]["priority"] in prio_a or S.DIMENSIONS[k]["priority"] in prio_b)),
                            "verdict": verdict, "note": note})
            if verdict == "strength":
                strengths.append(f"{S.DIMENSIONS[k]['label']}: {note}")
            elif verdict == "mismatch":
                mism.append(f"{S.DIMENSIONS[k]['label']}: {note}")
        return PairResult(score=score, label=score_label(score, blocked), rule_score=rule,
                          latent_similarity=latent, confidence=confidence, blocked=blocked,
                          dimensions=dim_out, dealbreakers=viol, unverified=unk,
                          strengths=strengths, mismatches=mism, residual_used=residual_used)

    def pair_features(self, a, b, dims=None, latent=None) -> list[float]:
        """Feature vector for the supervised residual model: 12 dimension scores (missing -> 0.5),
        latent similarity (missing -> 0.5), rule confidence."""
        dims = dims or self.dimension_scores(a, b)
        vec = [0.5 if dims[k][0] is None else dims[k][0] for k in DIM_ORDER]
        if latent is None and self.embedder is not None:
            latent = float(self.embedder.similarity(a, b))
        vec.append(0.5 if latent is None else latent)
        return vec

    # -- ranking ---------------------------------------------------------
    def rank(self, user: Mapping, candidates: Sequence[tuple[Any, Mapping]], k: int | None = 10,
             strict: bool = True, user_id: Any = None) -> list[dict]:
        """Rank candidates for `user`. Excludes self, duplicate ids and same-hostel violations
        (students only room with the same hostel type). Returns dicts with id + PairResult."""
        seen, out = set(), []
        for cid, prof in candidates:
            if cid == user_id or cid in seen:
                continue
            seen.add(cid)
            if user.get("hostel") and prof.get("hostel") and user["hostel"] != prof["hostel"]:
                continue
            res = self.pair(user, prof)
            if strict and res.blocked:
                continue
            out.append({"id": cid, "result": res})
        out.sort(key=lambda r: (-r["result"].score, str(r["id"])))
        return out[:k] if k else out
