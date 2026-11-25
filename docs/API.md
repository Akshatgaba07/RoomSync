# API (FastAPI; interactive docs at http://localhost:8000/docs)
All routes are under `/api`. Auth: `Authorization: Bearer <JWT>` (12 h). Errors are `{"detail": ...}`.

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | no | status, user count, which models are loaded |
| POST | `/auth/signup` | no | `{email, password (8-72), name}` -> `{access_token}`; 409 if the email exists, 422 invalid |
| POST | `/auth/login` | no | `{email, password}` -> `{access_token}`; 401 on bad credentials |
| GET | `/questionnaire` | no | questions, options, dealbreakers, priorities (drives the frontend form) |
| GET | `/me` | yes | profile, answers, completeness, missing keys |
| PATCH | `/me` | yes | `{name}` |
| PUT | `/profile` | yes | `{answers, dealbreakers, priorities}`; validated (422 on bad values); partial drafts allowed; recalculation is implicit because matches are computed on request |
| GET | `/matches?k=10&strict=true&include_demo=true` | yes | ranked recommendations (409 until the profile is complete). Returns pool size, excluded count, disclaimer |
| GET | `/matches/{id}` | yes | full breakdown: dimensions, strengths, mismatches, dealbreakers, unverified, side-by-side answers; 404 for self / other hostel / incomplete |
| POST | `/feedback` | yes | `{rating 1-5, partner_id?, note?}`; ratings with `partner_id` become training labels |
| GET | `/stats` | yes | live pool statistics and your own eligible-match numbers |

Emails and password hashes are never returned for other students.


## University bulk matching

Configure `UNIVERSITY_ADMIN_KEY` in the backend `.env` before using this endpoint.
The key is sent in the `X-University-Admin-Key` header. Keep it private and share it
only with the university administrator.

`POST /api/university/matches`

JSON body:
```json
{ "csv_text": "<UTF-8 CSV contents>", "mode": "both" }
```

The CSV must use the original Google Forms question headings documented in
`ml/roomsync_ml/schema.py`. Every row must have all required answers and the
priorities column. Optional identifier columns are `Student ID`, `Registration
Number`, `Roll Number`, `Email Address`, `Email address`, or `Email`; optional
display-name columns are `Student Name`, `Full Name`, or `Name`. If absent,
stable row-based IDs/names are generated.

The response contains:
- `individual_top2`: up to two eligible recommendations per student.
- `exclusive_pairs`: one-to-one pairs, no student repeated, respecting hostel
  type and hard dealbreakers.
- `unmatched_students`: students not allocated to an exclusive pair.

Exclusive allocation uses deterministic greedy highest-score-first pairing.
It is not guaranteed to be the globally optimal maximum-weight assignment.
The CSV is processed in memory and is not persisted by this endpoint.
Maximum upload: 500 students / 5 MB request body.
