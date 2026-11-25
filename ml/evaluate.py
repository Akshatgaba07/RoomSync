"""Evaluation of the hybrid engine. There are NO ground-truth compatibility labels, so this script
reports (a) invariants, (b) constraint behaviour, (c) robustness/sensitivity, (d) latent-model
stability with leakage-resistant (student-held-out) fitting. It does NOT report accuracy.
Run: python ml/evaluate.py  -> docs/EVALUATION_REPORT.md, docs/metrics.json, docs/figures/*.png"""
import json, sys, itertools
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import kendalltau, spearmanr
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score
from paths import PROCESSED, MODELS, DOCS, SEED
from roomsync_ml import CompatibilityEngine, schema as S
from roomsync_ml.embedding import LatentModel

rng = np.random.default_rng(SEED)
P = json.loads((PROCESSED / "profiles.json").read_text())
ids = [p["record_id"] for p in P]
lat = LatentModel.load(MODELS / "latent_model.joblib")
eng = CompatibilityEngine(embedder=lat)
M = {}
(DOCS / "figures").mkdir(parents=True, exist_ok=True)

# ---- (a) invariants over all same-hostel pairs
pairs = [(i, j) for i, j in itertools.combinations(range(len(P)), 2) if P[i]["hostel"] == P[j]["hostel"]]
res = {(i, j): eng.pair(P[i], P[j]) for i, j in pairs}
sym = max(abs(res[(i, j)].score - eng.pair(P[j], P[i]).score) for i, j in pairs)
scores = np.array([r.score for r in res.values()])
M["invariants"] = {"n_pairs": len(pairs), "max_asymmetry": float(sym), "score_min": float(scores.min()),
                   "score_max": float(scores.max()), "score_mean": float(scores.mean()),
                   "score_std": float(scores.std()), "self_excluded": all(
                       r["id"] != ids[0] for r in eng.rank(P[0], list(zip(ids, P)), None, False, ids[0])),
                   "cross_hostel_excluded": all(P[ids.index(r["id"])]["hostel"] == P[0]["hostel"]
                                                for r in eng.rank(P[0], list(zip(ids, P)), None, False, ids[0]))}
# ---- (b) constraints
blocked = np.array([r.blocked for r in res.values()])
M["constraints"] = {"blocked_pair_share": float(blocked.mean()),
                    "mean_score_blocked": float(scores[blocked].mean()), "mean_score_unblocked": float(scores[~blocked].mean())}
elig, free_at5 = [], []
for i, p in enumerate(P):
    r = eng.rank(p, list(zip(ids, P)), None, True, ids[i]); elig.append(len(r))
    top = r[:5]; free_at5.append(float(all(not x["result"].blocked for x in top)) if top else 1.0)
M["constraints"].update({"strict_eligible_candidates_mean": float(np.mean(elig)), "strict_eligible_min": int(min(elig)),
                         "users_with_<5_eligible": int(sum(e < 5 for e in elig)),
                         "dealbreaker_free_top5_rate_strict": float(np.mean(free_at5))})
nb = [eng.rank(p, list(zip(ids, P)), 5, False, ids[i]) for i, p in enumerate(P)]
M["constraints"]["dealbreaker_free_top5_rate_if_not_strict"] = float(np.mean(
    [np.mean([not x["result"].blocked for x in r]) for r in nb]))

# ---- (c) sensitivity (top-5 overlap, Kendall tau on per-user rankings vs baseline)
def ranking(engine, i):
    r = engine.rank(P[i], list(zip(ids, P)), None, False, ids[i]); return [x["id"] for x in r], {x["id"]: x["result"].score for x in r}
base = [ranking(eng, i) for i in range(len(P))]
def compare(engine):
    ov, tau = [], []
    for i in range(len(P)):
        o, s = ranking(engine, i); b, bs = base[i]
        ov.append(len(set(o[:5]) & set(b[:5])) / 5)
        tau.append(kendalltau([bs[k] for k in b], [s[k] for k in b])[0])
    return float(np.mean(ov)), float(np.nanmean(tau))
import roomsync_ml.schema as SS
orig = {k: d["base"] for k, d in SS.DIMENSIONS.items()}
sens = {}
ov_all, tau_all = [], []
for t in range(20):
    for k in SS.DIMENSIONS: SS.DIMENSIONS[k]["base"] = orig[k] * float(np.exp(rng.normal(0, 0.3)))
    o, ta = compare(eng); ov_all.append(o); tau_all.append(ta)
for k in SS.DIMENSIONS: SS.DIMENSIONS[k]["base"] = orig[k]
sens["dimension_weights_lognormal_sigma0.3_20runs"] = {"top5_overlap_mean": float(np.mean(ov_all)), "top5_overlap_min": float(np.min(ov_all)),
                                                       "kendall_tau_mean": float(np.mean(tau_all))}
for name, e in {"no_priority_personalisation": CompatibilityEngine(lat, priority_boost=1.0),
                "latent_alpha_0 (rules only)": CompatibilityEngine(None),
                "latent_alpha_0.5": CompatibilityEngine(lat, alpha=0.5)}.items():
    o, ta = compare(e); sens[name] = {"top5_overlap_mean": o, "kendall_tau_mean": ta}
M["sensitivity_vs_baseline"] = sens
# rule vs latent agreement
rule = np.array([r.rule_score for r in res.values()]); lt = np.array([r.latent_similarity for r in res.values()])
M["rule_vs_latent_spearman"] = float(spearmanr(rule, lt)[0])

# ---- (d) latent stability, student-held-out
tr, te = np.split(rng.permutation(len(P)), [int(0.8 * len(P))])
lat_tr = LatentModel(seed=SEED).fit([P[i] for i in tr])
tpairs = [(i, j) for i, j in itertools.combinations(te, 2)]
full = [lat.similarity(P[i], P[j]) for i, j in tpairs]; part = [lat_tr.similarity(P[i], P[j]) for i, j in tpairs]
aris = []
Z = np.vstack([lat.embed(p) for p in P]); k = lat.kmeans.n_clusters; ref = lat.kmeans.labels_
for b in range(30):
    idx = rng.choice(len(P), len(P)); km = KMeans(k, n_init=5, random_state=b).fit(Z[idx])
    aris.append(adjusted_rand_score(ref, km.predict(Z)))
M["latent_model"] = {"n_components": int(lat.pca.n_components_), "cumulative_variance": float(sum(lat.explained_variance())),
                     "silhouette_by_k": lat.k_scores, "chosen_k": k, "best_silhouette": float(lat.best_silhouette),
                     "bootstrap_ARI_mean": float(np.mean(aris)), "bootstrap_ARI_std": float(np.std(aris)),
                     "heldout_students": len(te), "heldout_pair_similarity_spearman_train_fit_vs_full_fit": float(spearmanr(full, part)[0])}

# ---- figures
plt.figure(figsize=(6,3.5)); plt.hist(scores, bins=25, color="#4f46e5"); plt.xlabel("Compatibility score"); plt.ylabel("Pairs")
plt.title("Score distribution (same-hostel pairs, synthetic profiles)"); plt.tight_layout(); plt.savefig(DOCS/"figures"/"score_distribution.png", dpi=130); plt.close()
b0 = [i for i, p in enumerate(P) if p["hostel"] == S.HOSTEL[0]]
H = np.array([[100.0 if i == j else eng.pair(P[i], P[j]).score for j in b0] for i in b0])
plt.figure(figsize=(6,5)); plt.imshow(H, cmap="viridis"); plt.colorbar(label="score"); plt.title("Pairwise scores, boys-hostel profiles"); plt.tight_layout()
plt.savefig(DOCS/"figures"/"pairwise_heatmap.png", dpi=130); plt.close()
imp = {k: 0.0 for k in SS.DIMENSIONS}
for r in res.values():
    for d in r.dimensions:
        if d["score"] is not None: imp[d["key"]] += d["weight"] * (0.5 - d["score"]) ** 2
tot = sum(imp.values()); imp = {k: v / tot for k, v in imp.items()}
M["dimension_influence_on_score_spread"] = imp
plt.figure(figsize=(6,4)); ks = sorted(imp, key=imp.get); plt.barh([SS.DIMENSIONS[k]["label"] for k in ks], [imp[k] for k in ks], color="#0d9488")
plt.title("Share of weighted score spread by dimension"); plt.tight_layout(); plt.savefig(DOCS/"figures"/"dimension_influence.png", dpi=130); plt.close()
plt.figure(figsize=(4.5,3)); plt.plot(list(lat.k_scores), list(lat.k_scores.values()), "o-"); plt.xlabel("k"); plt.ylabel("silhouette"); plt.tight_layout()
plt.savefig(DOCS/"figures"/"silhouette.png", dpi=130); plt.close()

(DOCS / "metrics.json").write_text(json.dumps(M, indent=1))
c, s, l, v = M["constraints"], M["sensitivity_vs_baseline"], M["latent_model"], M["invariants"]
w = s["dimension_weights_lognormal_sigma0.3_20runs"]
md = f"""# RoomSync evaluation report (auto-generated by `ml/evaluate.py`)

**Read this first.** The data contain 60 *synthetic* profiles and **zero** compatibility labels
(the "current roommate compatibility" column is empty). Accuracy, Precision@K or NDCG against
real outcomes therefore **cannot be computed** and none is reported. What follows are
invariant checks, constraint behaviour, robustness and stability, all on synthetic profiles.

## 1. Invariants ({v['n_pairs']} same-hostel pairs)
- Max |score(A,B) - score(B,A)|: **{v['max_asymmetry']:.2e}** (symmetric)
- Score range {v['score_min']:.1f}-{v['score_max']:.1f}, mean {v['score_mean']:.1f}, sd {v['score_std']:.1f}
- Self-match excluded: {v['self_excluded']}; cross-hostel excluded: {v['cross_hostel_excluded']}

## 2. Hard constraints
- {c['blocked_pair_share']*100:.1f}% of same-hostel pairs violate at least one dealbreaker/stated constraint.
- Mean score of blocked pairs {c['mean_score_blocked']:.1f} vs unblocked {c['mean_score_unblocked']:.1f}.
- Strict mode: mean eligible candidates per student {c['strict_eligible_candidates_mean']:.1f} (min {c['strict_eligible_min']});
  students with <5 eligible: {c['users_with_<5_eligible']}; dealbreaker-free top-5 rate {c['dealbreaker_free_top5_rate_strict']:.2f}.
- Non-strict mode: dealbreaker-free share of top-5 = {c['dealbreaker_free_top5_rate_if_not_strict']:.2f}
  (blocked pairs are capped at {39}, so they rarely reach the top).

## 3. Sensitivity (agreement with baseline ranking, per student, averaged)
| Perturbation | Top-5 overlap | Kendall tau |
|---|---|---|
| Random dimension weights (lognormal sd 0.3, 20 runs) | {w['top5_overlap_mean']:.2f} (min {w['top5_overlap_min']:.2f}) | {w['kendall_tau_mean']:.2f} |
| No priority personalisation | {s['no_priority_personalisation']['top5_overlap_mean']:.2f} | {s['no_priority_personalisation']['kendall_tau_mean']:.2f} |
| Rules only (no latent model) | {s['latent_alpha_0 (rules only)']['top5_overlap_mean']:.2f} | {s['latent_alpha_0 (rules only)']['kendall_tau_mean']:.2f} |
| Latent weight 0.5 | {s['latent_alpha_0.5']['top5_overlap_mean']:.2f} | {s['latent_alpha_0.5']['kendall_tau_mean']:.2f} |

Rule score vs latent similarity Spearman: {M['rule_vs_latent_spearman']:.2f}.

## 4. Latent model
- PCA: {l['n_components']} components, {l['cumulative_variance']*100:.0f}% variance.
- KMeans k={l['chosen_k']}, silhouette **{l['best_silhouette']:.3f}** (weak: the profiles have little cluster structure; archetypes are descriptive only).
- Bootstrap ARI {l['bootstrap_ARI_mean']:.2f} +/- {l['bootstrap_ARI_std']:.2f}.
- Leakage-resistant check: model refit on 80% of students, similarity of pairs among the {l['heldout_students']} held-out students correlates with the full-data model at Spearman **{l['heldout_pair_similarity_spearman_train_fit_vs_full_fit']:.2f}**.

Figures: `docs/figures/`. Raw numbers: `docs/metrics.json`.

## Limitations
Synthetic data; heuristic rule weights not validated against real outcomes; sensitivity does not equal validity.
Supervised learning is implemented (`ml/train_supervised.py`) but needs real roommate-satisfaction feedback.
"""
(DOCS / "EVALUATION_REPORT.md").write_text(md); print(md)
