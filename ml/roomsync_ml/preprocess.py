"""Preprocessing: survey rows / app answers -> canonical profiles -> numeric features."""
from __future__ import annotations

import math
from typing import Any, Mapping

import numpy as np

from . import schema as S

# Categorical features that are one-hot encoded for the latent (PCA) model.
ONEHOT_KEYS = ["climate", "study_env", "food", "nonveg_comfort", "conflict", "weekend"]


class ProfileError(ValueError):
    """Raised when answers do not match the questionnaire schema."""


def _split_multi(value: Any) -> list[str]:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return []
    return [p.strip() for p in str(value).split(",") if p.strip()]


def _clean_choice(key: str, value: Any, strict: bool) -> Any:
    q = S.QUESTIONS[key]
    if value is None or (isinstance(value, float) and math.isnan(value)) or value == "":
        return None
    if q["type"] == "scale":
        try:
            v = int(value)
        except (TypeError, ValueError):
            if strict:
                raise ProfileError(f"{key}: expected integer {q['min']}-{q['max']}, got {value!r}")
            return None
        if not (q["min"] <= v <= q["max"]):
            if strict:
                raise ProfileError(f"{key}: {v} outside {q['min']}-{q['max']}")
            return None
        return v
    v = str(value).strip()
    if v not in q["options"]:
        if strict:
            raise ProfileError(f"{key}: {v!r} is not one of {q['options']}")
        return None
    return v


def profile_from_answers(answers: Mapping[str, Any], dealbreakers=None, priorities=None,
                         strict: bool = True) -> dict:
    """Build a canonical profile. Unknown keys are rejected in strict mode; blanks become None."""
    if strict:
        unknown = set(answers) - set(S.QUESTIONS)
        if unknown:
            raise ProfileError(f"unknown question keys: {sorted(unknown)}")
    prof = {k: _clean_choice(k, answers.get(k), strict) for k in S.QUESTIONS}
    dbs = [d for d in (dealbreakers or []) if d != S.NO_DEALBREAKER]
    bad = [d for d in dbs if d not in S.DEALBREAKERS]
    if bad and strict:
        raise ProfileError(f"unknown dealbreakers: {bad}")
    dbs = [d for d in dbs if d in S.DEALBREAKERS]
    pri = list(dict.fromkeys(priorities or []))
    badp = [p for p in pri if p not in S.PRIORITIES]
    if badp and strict:
        raise ProfileError(f"unknown priorities: {badp}")
    pri = [p for p in pri if p in S.PRIORITIES]
    if len(pri) > S.MAX_PRIORITIES:
        if strict:
            raise ProfileError(f"at most {S.MAX_PRIORITIES} priorities allowed")
        pri = pri[: S.MAX_PRIORITIES]
    prof["dealbreakers"] = sorted(set(dbs))
    prof["priorities"] = pri
    return prof


def profile_from_survey_row(row: Mapping[str, Any]) -> dict:
    """Map one Google-Form CSV row (original column titles) to a canonical profile."""
    answers = {k: row.get(q["col"]) for k, q in S.QUESTIONS.items() if q["col"]}
    return profile_from_answers(
        answers,
        dealbreakers=_split_multi(row.get(S.DEALBREAKER_COL)),
        priorities=_split_multi(row.get(S.PRIORITY_COL)),
        strict=True,
    )


def completeness(profile: Mapping[str, Any]) -> tuple[float, list[str]]:
    """Fraction of required questions answered and the list of missing keys."""
    missing = [k for k in S.REQUIRED_KEYS if profile.get(k) is None]
    if not profile.get("priorities"):
        missing.append("priorities")
    total = len(S.REQUIRED_KEYS) + 1
    return (total - len(missing)) / total, missing


def is_complete(profile: Mapping[str, Any]) -> bool:
    return not completeness(profile)[1]


# ---------- numeric encodings -------------------------------------------------
def ordinal01(profile: Mapping[str, Any], key: str) -> float:
    """Ordinal / scale answer scaled to [0, 1]; NaN when missing."""
    v = profile.get(key)
    if v is None:
        return float("nan")
    q = S.QUESTIONS[key]
    if q["type"] == "scale":
        return (int(v) - q["min"]) / (q["max"] - q["min"])
    opts = q["options"]
    return opts.index(v) / (len(opts) - 1)


ORDINAL_KEYS = [k for k, q in S.QUESTIONS.items()
                if (q["type"] == "scale" or q.get("ordinal")) and not q.get("optional")]


def feature_names() -> list[str]:
    names = list(ORDINAL_KEYS)
    for k in ONEHOT_KEYS:
        names += [f"{k}={o}" for o in S.QUESTIONS[k]["options"]]
    names += [f"prio:{p}" for p in S.PRIORITIES]
    return names


def raw_feature_vector(profile: Mapping[str, Any]) -> np.ndarray:
    """Numeric vector with NaN for missing ordinal values and all-zero one-hot blocks."""
    vals = [ordinal01(profile, k) for k in ORDINAL_KEYS]
    for k in ONEHOT_KEYS:
        v = profile.get(k)
        vals += [1.0 if v == o else 0.0 for o in S.QUESTIONS[k]["options"]]
    pri = profile.get("priorities") or []
    vals += [1.0 if p in pri else 0.0 for p in S.PRIORITIES]
    return np.array(vals, dtype=float)


class MedianImputer:
    """Tiny, serialisable median imputer (fit on the profile corpus)."""

    def __init__(self, medians: np.ndarray | None = None):
        self.medians = medians

    def fit(self, X: np.ndarray) -> "MedianImputer":
        med = np.nanmedian(X, axis=0)
        self.medians = np.where(np.isnan(med), 0.5, med)
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        X = np.array(X, dtype=float, copy=True)
        idx = np.where(np.isnan(X))
        X[idx] = np.take(self.medians, idx[1]) if X.ndim == 2 else self.medians[idx[0]]
        return X
