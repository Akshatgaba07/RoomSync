# RoomSync: roommate compatibility for Bennett University hostels

A full-stack project: **React** UI, **FastAPI** backend, **MongoDB** persistence, and a **Python ML engine**
(rule-based pairwise scoring + unsupervised latent model + dealbreaker constraints + an optional supervised stage
that only activates when real feedback labels exist). Every recommendation comes with a plain-language explanation.

## Read this first: what is and isn't real
- The supplied CSV has **60 profiles, all synthetic**, and its compatibility-label column is **empty**. There is therefore **no ground
  truth**, and this project reports **no accuracy / Precision@K / NDCG against real outcomes**. See `docs/EVALUATION_REPORT.md`
  for what *was* measured (invariants, constraint behaviour, robustness, stability).
- No public roommate-pair dataset was found. Big Five data (OpenPsychometrics/Kaggle) exist but can't be linked to students; they are
  documented, not used (`datasets/DATA_SOURCES.md`). I could not download them in the build sandbox, so their licence/availability
  were not checked first-hand.
- Scores are **estimates**, not guarantees. The supervised pipeline was exercised only on **simulated** labels (`docs/supervised_smoke_test.json`).

## Verified in the build environment
| Item | Status |
|---|---|
| ML pipeline (`build_dataset` -> `train_embedding` -> `evaluate` -> `train_supervised --smoke`) | Executed, outputs in `docs/`, `models/` |
| 28 pytest tests (ML engine + API incl. auth, validation, dealbreakers, hostel isolation, dynamic recalculation) | Passing (against `mongomock`) |
| Real-browser E2E (Playwright/Chromium: signup -> questionnaire -> dashboard -> matches -> detail -> edit preferences -> mobile -> logout/login) | Passing (`tests/e2e`, screenshots included) |
| Frontend production build (`npm run build`) | Passing |
| **Real MongoDB server** | **Not run here** (none available); code uses standard `pymongo` calls only |
| **Docker / docker-compose** | **Not run here**; files provided but untested |

## Quick start A: no database needed (in-memory demo)
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# edit .env:  MONGODB_URI=mongomock://   AUTO_SEED_DEMO=true
uvicorn backend.app.main:app --port 8000
# second terminal
cd frontend && npm install && npm run dev               # http://localhost:5173
```
Data is lost when the backend restarts. Log in as `demo01@roomsync.demo` / `RoomSync-demo-1` (demo01...demo60, all **synthetic**),
or sign up and fill the questionnaire.

## Quick start B: real MongoDB
```bash
docker run -d --name rs-mongo -p 27017:27017 mongo:7      # or any MongoDB 6/7 install
# .env: MONGODB_URI=mongodb://localhost:27017   JWT_SECRET=<long random>
python backend/scripts/seed_demo.py                      # loads the 60 synthetic demo accounts (idempotent; --reset to reload)
uvicorn backend.app.main:app --port 8000
cd frontend && npm install && npm run dev
```
## Quick start C: Docker Compose (untested here)
`docker compose up --build` -> UI http://localhost:8080, API docs http://localhost:8000/docs.

## Reproduce the ML work and run tests
```bash
./run_pipeline.sh                       # dataset build, training, evaluation, smoke test, pytest (seed 42)
python tests/e2e/e2e_browser.py         # needs: playwright install chromium, backend :8000 (mongomock+seed) and frontend :5173 running
```
Outputs: `datasets/processed/`, `models/latent_model.joblib` (+meta), `docs/EVALUATION_REPORT.md`, `docs/metrics.json`, `docs/figures/`.

## When you have real data
1. Add real Bennett responses as new profiles tagged `origin=real_bennett`; re-run `ml/build_dataset.py` and `ml/train_embedding.py`.
2. Students rate real roommate arrangements in the app (`POST /api/feedback`). Run `python backend/scripts/export_feedback.py`, then
   `python ml/train_supervised.py --pairs pairs.csv --profiles profiles_real.json` (needs >= 150 labelled pairs; student-held-out validation).
   The backend then blends the learned model in automatically.

## Layout
```
backend/   FastAPI app (routers, security, db, matching service), scripts/seed_demo.py, export_feedback.py
frontend/  React + Vite (landing, auth, multi-step questionnaire, dashboard, matches, breakdown, profile, preferences)
ml/        roomsync_ml/ (schema, preprocess, engine, embedding), build_dataset, train_embedding, evaluate, train_supervised
datasets/  raw/ (original, untouched), processed/, external/ (optional Big Five fetcher), DATA_SOURCES.md
models/    latent_model.joblib, latent_model_meta.json
docs/      METHODOLOGY.md, API.md, EVALUATION_REPORT.md, metrics.json, figures/
tests/     test_ml.py, test_api.py, e2e/
```
## Security notes
bcrypt password hashing; JWT auth; input validation (pydantic + schema checks); `JWT_SECRET` must be set when `ENV=production`;
other students' emails are never exposed. Not included: rate limiting, email verification, password reset, HTTPS (use a reverse proxy).
Demo accounts share a well-known password; do not seed them in production.


## University CSV matching (Campus Match)

Set a long private `UNIVERSITY_ADMIN_KEY` in the backend `.env`, restart the API,
then open `/university` in the React app. Upload a UTF-8 CSV exported from the
RoomSync/Google Forms questionnaire. Required questions and the priorities
column must be complete for every row. The page produces both individual
top-2 recommendations and one-to-one exclusive roommate pairs, plus an
unmatched-students report. CSV contents are processed in memory and are not
stored by this endpoint. The shared admin key is a lightweight project/demo
access control; for production, replace it with university-specific accounts,
role-based access, HTTPS, and audit logging.

Exclusive pairs are generated using deterministic greedy highest-score-first
matching, not a globally optimal assignment algorithm. Compatibility scores
remain estimates, not validated predictions of roommate outcomes.
