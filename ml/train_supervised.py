"""Supervised stage for when real labels exist.

Labels: pairs of students who actually lived together, with a 1-5 satisfaction rating
(collected through the app's feedback form / the 'current roommate compatibility' survey column).
Features: the engine's 12 dimension scores + latent similarity (pair_features).
Validation: STUDENT-LEVEL split (a pair is used for testing only if BOTH students are held out;
pairs straddling the split are dropped) so no student leaks between train and test.
Metrics: MAE (0-100 scale), Spearman, Precision@K / NDCG@K of ranking each test student's partners.

  python ml/train_supervised.py --pairs pairs.csv --profiles datasets/processed/profiles.json
  python ml/train_supervised.py --smoke      # pipeline smoke test on SIMULATED labels (not a result)

Real runs refuse to save a model with fewer than MIN_LABELS pairs.
"""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import numpy as np, pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, ndcg_score
from scipy.stats import spearmanr
from paths import PROCESSED, MODELS, DOCS, SEED
from roomsync_ml import CompatibilityEngine
from roomsync_ml.embedding import LatentModel
from residual import ResidualModel

MIN_LABELS = 150


def simulate_pairs(P, n, rng):
    """SIMULATED ratings from a hidden function + noise. Only for exercising the pipeline."""
    eng = CompatibilityEngine(LatentModel.load(MODELS / "latent_model.joblib"))
    rows = []
    while len(rows) < n:
        i, j = rng.choice(len(P), 2, replace=False)
        if P[i]["hostel"] != P[j]["hostel"]: continue
        f = eng.pair_features(P[i], P[j])
        hidden = 100 * (0.5 * f[0] + 0.3 * f[1] + 0.2 * f[2]) + rng.normal(0, 8)
        rows.append((P[i]["record_id"], P[j]["record_id"], float(np.clip(1 + 4 * hidden / 100, 1, 5))))
    return pd.DataFrame(rows, columns=["a_id", "b_id", "rating"])


def precision_ndcg(df, k=3):
    p, n = [], []
    for sid, g in df.groupby("a_id"):
        if len(g) < 2: continue
        rel = (g.y >= 70).astype(int).values
        top = np.argsort(-g.pred.values)[:k]
        p.append(rel[top].mean()); n.append(ndcg_score([g.y.values], [g.pred.values], k=min(k, len(g))))
    return (float(np.mean(p)) if p else None, float(np.mean(n)) if n else None, len(p))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs"); ap.add_argument("--profiles", default=str(PROCESSED / "profiles.json"))
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    rng = np.random.default_rng(SEED)
    P = json.loads(Path(a.profiles).read_text()); by = {p["record_id"]: p for p in P}
    pairs = simulate_pairs(P, 600, rng) if a.smoke else pd.read_csv(a.pairs)
    eng = CompatibilityEngine(LatentModel.load(MODELS / "latent_model.joblib"))
    X = np.array([eng.pair_features(by[r.a_id], by[r.b_id]) for r in pairs.itertuples()])
    y = (pairs.rating.values - 1) / 4 * 100
    students = np.array(sorted(set(pairs.a_id) | set(pairs.b_id))); rng.shuffle(students)
    test_s = set(students[: max(2, int(0.25 * len(students)))])
    ia = pairs.a_id.isin(test_s).values; ib = pairs.b_id.isin(test_s).values
    tr, te = ~ia & ~ib, ia & ib
    print(f"pairs={len(pairs)} train={tr.sum()} test={te.sum()} dropped_straddling={len(pairs)-tr.sum()-te.sum()}")
    if te.sum() < 5 or tr.sum() < 20:
        sys.exit("Not enough pairs for a student-held-out evaluation.")
    base = np.clip(X[:, :12].mean(1) * 100, 0, 100)
    out = {"mode": "SMOKE_TEST_ON_SIMULATED_LABELS" if a.smoke else "REAL_LABELS", "n_pairs": int(len(pairs)),
           "n_train": int(tr.sum()), "n_test": int(te.sum()),
           "baseline_mean_of_dimensions_MAE": float(mean_absolute_error(y[te], base[te]))}
    cands = {"ridge": Ridge(alpha=1.0), "gbr": GradientBoostingRegressor(n_estimators=150, max_depth=2, random_state=SEED)}
    best, best_mae = None, 1e9
    for name, m in cands.items():
        m.fit(X[tr], y[tr]); pr = m.predict(X[te]); mae = mean_absolute_error(y[te], pr)
        out[name] = {"MAE": float(mae), "spearman": float(spearmanr(y[te], pr)[0])}
        if mae < best_mae: best, best_mae, best_pred, best_name = m, mae, pr, name
    d = pd.DataFrame({"a_id": pairs.a_id[te].values, "y": y[te], "pred": best_pred})
    out["best_model"] = best_name
    out["precision_at_3_ndcg_at_3_students"] = precision_ndcg(d)
    if hasattr(best, "coef_"):
        from roomsync_ml.engine import DIM_ORDER
        out["ridge_coefficients"] = dict(zip(DIM_ORDER + ["latent"], map(float, best.coef_)))
    if a.smoke:
        out["WARNING"] = "Labels are simulated. These numbers only show the code runs; they say nothing about real compatibility."
        (DOCS / "supervised_smoke_test.json").write_text(json.dumps(out, indent=1))
    else:
        if len(pairs) < MIN_LABELS: sys.exit(f"Need >= {MIN_LABELS} labelled pairs to save a model (got {len(pairs)}).")
        best.fit(X, y)
        ResidualModel(best, out).save(MODELS / "feedback_model.joblib")
        (DOCS / "supervised_real_report.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))

if __name__ == "__main__":
    main()
