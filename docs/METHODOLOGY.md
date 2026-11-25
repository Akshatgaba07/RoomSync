# RoomSync ML methodology

## 1. Problem and the label constraint
Goal: rank potential roommates for a student and explain why. Data: 60 **synthetic** profiles (28 columns); the only
outcome column ("compatibility with CURRENT roommate") is empty. With no pair labels, a classifier of "compatible vs not"
would just learn whatever rule generated the labels, so none is trained. The engine is a **hybrid, documented-rule +
unsupervised system**, with a supervised stage that activates only when real feedback exists.

## 2. Pipeline
1. `ml/build_dataset.py` - validates the CSV against `roomsync_ml/schema.py`, maps the 25 survey questions to canonical keys,
   splits multi-select answers (dealbreakers, top-3 priorities), tags provenance, writes `datasets/processed/*`.
2. Encoding (`preprocess.py`) - ordinal answers and 1-5 scales -> [0,1]; categoricals -> one-hot (latent model only);
   missing values stay `NaN`. The rule engine **skips** missing dimensions and renormalises weights (reported as
   *confidence*); the latent model uses a median imputer fitted on the corpus.
3. `ml/train_embedding.py` - StandardScaler -> PCA (components for 80% variance) -> Gaussian kernel similarity
   `exp(-d^2 / 2 sigma^2)`, sigma^2 = median pairwise squared distance; KMeans archetypes (k by silhouette, 3-7).
   Priorities are excluded from the embedding (they are weights, not lifestyle). Saved to `models/latent_model.joblib`.
4. `engine.py` - pairwise scoring (below). 5. `evaluate.py` - evaluation. 6. `train_supervised.py` - feedback stage.

## 3. Scoring
`score = 100 * penalty * ((1 - 0.2) * rule + 0.2 * latent)`; hard constraints override.

**Twelve dimension scores in [0,1]** (each symmetric in the pair, with directional friction where the harm is one-sided):
sleep (bedtime/wake distance, extra penalty when the earlier sleeper is a light sleeper), noise & study (one student's
noise sensitivity x the other's emission from audio, gaming, calls), cleanliness, food (each direction: tolerance for
non-veg vs the other's non-veg exposure x in-room eating), night climate (windows-vs-AC is a near-conflict), gaming/audio
similarity, guests (frequency vs the other's comfort), weekends, privacy (alone-time need x the other's presence),
sharing, conflict style (pair matrix; two avoiders score low because issues never get resolved), desired relationship.
The functional forms and constants are expert-chosen from the roommate-compatibility literature themes (sleep, cleanliness,
conflict, social habits). **They are priors, not fitted values, and have not been validated against outcomes.**

**Personalised weights.** Each dimension has a base importance; dimensions tied to a student's top-3 priorities get x1.8.
Pair weight = base x (1 + 0.8 x share of the two students who prioritised it), so it is symmetric.

**Priority-critical penalty.** If a dimension either student prioritised scores < 0.35, multiply by 0.92 (floor 0.78): a mean can hide a
deal-breaking clash in what someone cares about.

**Hard constraints.** All 8 dealbreakers are evaluated on the *other* student's answers, in both directions, via explicit
behaviour rules (e.g. "loud calls at night" = calls >= 4/5 and bedtime after 1 AM). A declared "not comfortable with non-veg in
the room" is treated as a stated constraint. Strict mode excludes such pairs; otherwise score is capped at 39 and flagged.
"Drinks alcohol" and "Smokes/vapes" can't be checked from the original survey, so the app asks two optional extra questions;
when the other student hasn't answered, the dealbreaker is reported as **unverified**, not assumed.

**Eligibility.** Same hostel type only; self and duplicates are removed; only complete profiles are ranked.

**Supervised residual (optional).** `train_supervised.py` fits Ridge / gradient boosting on [12 dimension scores, latent
similarity] -> real 1-5 roommate rating, with a **student-level split** (a pair is a test pair only if both students are held
out; straddling pairs are dropped), reports MAE, Spearman, Precision@3 and NDCG@3, and refuses to save a model with fewer than
150 labelled pairs. If `models/feedback_model.joblib` exists the backend blends it in at weight 0.3. Ridge coefficients double as
learned dimension importances. Run on **simulated** labels (`--smoke`) it only proves the code runs (`docs/supervised_smoke_test.json`).

## 4. Explainability
Every `PairResult` lists per-dimension score, weight, whether it is a top priority, verdict (strength >= 0.75, mismatch < 0.5),
a factual note quoting both students' answers, dealbreaker violations with evidence, unverifiable constraints, and model confidence.
`docs/figures/dimension_influence.png` shows which dimensions drive score differences across the pool.

## 5. Limitations
- Synthetic data; real Bennett responses were not available. Distribution and cluster structure are artefacts of the generator
  (silhouette ~0.08: archetypes are weak and descriptive).
- Rule constants and the 0.2 latent weight are not calibrated to outcomes. Sensitivity (top-5 overlap ~0.9 under random weight noise)
  shows robustness, not correctness.
- Self-reported answers; people are poor judges of their own habits. Personality (Big Five) is not measured.
- Dealbreaker behaviour rules are heuristics from coarse survey buckets.
- Scores are estimates and not a guarantee about a living arrangement; the UI says so.
- Fairness: only lifestyle answers and hostel type are used; no gender, religion or region features. Food preference is used, and could
  correlate with community; it is applied only through the student's own stated comfort and dealbreakers.
