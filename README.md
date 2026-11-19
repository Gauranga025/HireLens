# HireLens — AI Resume Screening and Job Matching

HireLens is a full-stack resume screening application that parses PDF and DOCX resumes, analyzes job descriptions into structured requirements, scores candidates with an evidence-aware hybrid scorer, and returns ranked results with explanations and JSON/CSV reports.

> **Release status:** deployment-prepared for controlled/internal use. The application is **not hardened for untrusted multi-user production**: it has no authentication, uses development credentials in local examples, and has not undergone a formal security, privacy, or fairness audit. Ranking accuracy has **not** been validated on a genuine human-labelled held-out dataset. Scores are decision-support signals, not hiring decisions.

---

## Table of contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Technology stack](#technology-stack)
- [Repository structure](#repository-structure)
- [Prerequisites](#prerequisites)
- [Local setup](#local-setup)
- [Environment variables](#environment-variables)
- [Model download and cache](#model-download-and-cache)
- [Running the application](#running-the-application)
- [Testing](#testing)
- [Production build and deployment](#production-build-and-deployment)
- [Database and persistence](#database-and-persistence)
- [API](#api)
- [Scoring and structured requirements](#scoring-and-structured-requirements)
- [Known limitations](#known-limitations)
- [GitHub handoff](#github-handoff)
- [Documentation](#documentation)

---

## Overview

The active application consists of:

- **Frontend:** Next.js 16, React 19, TypeScript, Tailwind CSS 4.
- **Backend:** FastAPI, SQLAlchemy 2.0 async, Pydantic 2, Alembic.
- **Database:** PostgreSQL 16.
- **NLP:** Sentence Transformers (`all-MiniLM-L6-v2`, pinned revision), scikit-learn, PyMuPDF, python-docx.
- **Evaluation infrastructure:** benchmark tooling is present but its real-data evaluation is blocked because no genuine human-labelled dataset exists.

The legacy Streamlit prototype (`app.py`, `src/`, root `tests/`, and root `requirements*.txt`) is retained as history and is not used by the active application.

---

## Features

### Job description analysis

- Extracts a role title, required/preferred skills, qualifications, and experience text.
- Produces structured requirements for individual skills, `ANY`/`ALL` alternative groups, experience constraints, and fundamental engineering skills.
- Persists flat skills and structured requirements in PostgreSQL.
- Falls back to `analysis_data` for legacy jobs that lack the dedicated structured-requirements column.

### Resume processing

- Accepts PDF and DOCX uploads up to 10 MB per file.
- Extracts text, candidate details, education, experience, certifications, projects, and skills.
- Adds experience classification, project intelligence, and temporal metadata.
- Stores uploaded files locally and parsed data in PostgreSQL.
- Reports per-file failures without dropping successfully uploaded files.

### Evidence-aware evaluation

- Ranks candidates by an overall score from 0 to 100.
- Reports required/preferred coverage, semantic similarity, evidence strength, and per-requirement evaluation.
- Links matched skills to section-aware evidence and demonstration levels.
- Handles satisfied `ANY` groups without double counting or false gaps.
- Deduplicates repeated resume IDs and upserts screening rows for repeated evaluations.

### Reports and UI

- Generates JSON and CSV reports through the same evaluation pipeline as the matching endpoint.
- Displays score breakdown, evidence, strengths, gaps, requirement groups, and explanations.
- Shows failed uploads and failed candidates.
- Polls backend connection status every 30 seconds.

---

## Architecture

```mermaid
flowchart LR
    UI["Next.js UI<br/>frontend/"] --> API["FastAPI API<br/>backend/app"]
    API --> DB[("PostgreSQL 16<br/>jobs, resumes,<br/>screening_results")]
    API --> FS[("Upload directory<br/>UPLOAD_STORAGE_DIR")]
    API --> NLP["Parsing and scoring services<br/>evidence, requirements, scoring"]
    NLP --> MODEL["Sentence Transformers<br/>all-MiniLM-L6-v2 (pinned)"]
```

Request flow:

1. `POST /api/v1/jobs/analyze` parses and persists a job description.
2. `POST /api/v1/resumes/upload` validates, stores, parses, and persists each resume.
3. `POST /api/v1/matching/evaluate` evaluates all requested candidates, upserts screening rows, and returns results sorted by score.
4. `POST /api/v1/reports/generate` recomputes one candidate with the same pipeline and returns JSON or CSV content.

The frontend and backend are separate deployment units. FastAPI is not served by Next.js.

---

## Technology stack

| Component | Technology | Verified version |
|---|---|---|
| Backend API | FastAPI | 0.141.1 in verification environment (`>=0.104.0` declared) |
| Backend server | Uvicorn | 0.52.1 (`>=0.24.0` declared) |
| Validation | Pydantic / pydantic-settings | 2.x |
| Database | PostgreSQL | 16 |
| ORM / driver | SQLAlchemy async / asyncpg | 2.x / 0.29.0 |
| Migrations | Alembic | 1.13.1 |
| PDF extraction | PyMuPDF | 1.24.10 |
| DOCX extraction | python-docx | 1.2.0 installed; 1.1.2 declared |
| Semantic embeddings | sentence-transformers | 3.1.1 |
| Transformers runtime | transformers | 4.39.3 installed; 4.57.6 declared |
| ML utilities | scikit-learn / NumPy | 1.7.2 / 1.26.4 installed; 1.3.2 / 1.24.4 declared |
| Frontend | Next.js / React | 16.4.6 / 19.3.0 |
| Language | TypeScript | 5.9.3 |
| Styling | Tailwind CSS | 4.3.3 |
| Python runtime | CPython | 3.10.11 |
| Node runtime | Node.js / npm | 22.18.0 / 10.9.8 |

The installed and declared versions above differ for a few ML packages because verification used the established local Python 3.10 environment. No dependency files were changed during final preparation.

---

## Repository structure

```text
intern/
├── backend/
│   ├── app/
│   │   ├── api/routes/             jobs, resumes, matching, reports
│   │   ├── core/                   settings, exceptions, in-memory report store
│   │   ├── db/                     async engine, sessions, declarative base
│   │   ├── evaluation/             benchmark framework
│   │   ├── models/                 Job, Resume, ScreeningResult
│   │   ├── repositories/           PostgreSQL data access
│   │   ├── schemas/                API and domain schemas
│   │   ├── services/               parsing, analysis, evidence, semantic, scoring
│   │   └── utils/                  text processing and JSONB serialization
│   ├── alembic/versions/           database migrations
│   ├── scripts/                    benchmark/evaluation CLIs
│   ├── tests/                      backend pytest suite
│   ├── evaluation/                 benchmark annotation template
│   └── requirements.txt
├── frontend/
│   ├── app/                        Next.js App Router page
│   ├── components/                 workflow and result components
│   ├── lib/                        API client and TypeScript types
│   └── package.json / package-lock.json
├── src/                            legacy Streamlit prototype modules
├── tests/                          legacy prototype tests
├── sample_data/                    sample artifacts
├── storage/                        local upload root (ignored)
├── docker-compose.yml              PostgreSQL 16 service only
├── .env.example                    backend/frontend environment template
└── DEPLOYMENT.md                   manual deployment instructions
```

---

## Prerequisites

- Docker with Docker Compose for local PostgreSQL.
- Python 3.10 (verified 3.10.11). Use `py -3.10` where multiple Python versions are installed.
- Node.js 20.9+ and npm (verified 22.18.0 / 10.9.8).
- Internet access on first semantic-model use, unless the Hugging Face cache is pre-populated.
- A persistent directory for uploaded files in any non-local deployment.

---

## Local setup

### 1. Start PostgreSQL

From the repository root:

```powershell
docker compose up -d postgres
docker compose ps
```

PostgreSQL is exposed on `localhost:5432` with a named volume `postgres_data`.

> Do not run `docker compose down -v` unless you intentionally want to delete the local database volume.

### 2. Create the Python environment

From the repository root:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

On Linux/macOS use `python3.10 -m venv .venv` and `source .venv/bin/activate`.

### 3. Configure environment files

```powershell
Copy-Item .env.example backend\.env
Copy-Item frontend\.env.example frontend\.env.local
```

- The backend reads `backend/.env` when started from `backend/`.
- The frontend reads `frontend/.env.local` at build/dev time.
- Neither real `.env` file should be committed.
- `DATABASE_URL` is computed from `POSTGRES_*`; there is no application `DATABASE_URL` setting.
- Add every deployed frontend origin to `CORS_ORIGINS`.

### 4. Apply migrations

From `backend/`:

```powershell
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m alembic current
```

If the path with a space is inconvenient, use `py -3.10` with the installed dependencies:

```powershell
py -3.10 -m alembic upgrade head
py -3.10 -m alembic current
```

Expected revision: `add_structured_requirements (head)`.

### 5. Install the frontend

From `frontend/`:

```powershell
npm ci
```

`npm ci` uses the committed `package-lock.json`.

---

## Environment variables

### Backend

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `APP_NAME` | No | `AI Resume Screening Backend` | API title |
| `APP_VERSION` | No | `0.1.0` | Version metadata |
| `DEBUG` | No | `false` | SQL echo/debug mode; keep false in deployment |
| `API_PREFIX` | No | `/api/v1` | API route prefix |
| `CORS_ORIGINS` | Yes in deployment | local Next.js origins | JSON array of allowed browser origins |
| `POSTGRES_HOST` | Yes | `localhost` | PostgreSQL host |
| `POSTGRES_PORT` | Yes | `5432` | PostgreSQL port |
| `POSTGRES_DB` | Yes | `resume_screening` | Database name |
| `POSTGRES_USER` | Yes | `resume_user` | Database user |
| `POSTGRES_PASSWORD` | Yes | development-only value | Database password |
| `UPLOAD_STORAGE_DIR` | No | `storage/uploads` | Directory for original uploaded files; point at persistent storage |
| `TEST_DATABASE_URL` | Tests only | unset | Disposable test database URL; must end in `_test` and differ from the main DB |
| `SEMANTIC_MODEL_NAME` | No | `sentence-transformers/all-MiniLM-L6-v2` | Sentence Transformers repository name |
| `SEMANTIC_MODEL_REVISION` | No | `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` | Verified model snapshot; use `main` only intentionally |
| `HF_HOME` | No | Hugging Face default | Model cache root; make persistent in deployment |
| `HF_HUB_OFFLINE` | No | unset/`0` | Set `1` to prevent downloads and fail cleanly from cache |
| `HF_HUB_DISABLE_TELEMETRY` | No | unset | Set `1` to disable Hugging Face telemetry |

### Frontend

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `NEXT_PUBLIC_BACKEND_URL` | Yes for deployment | `http://localhost:8000` | Backend origin used by the browser |

`NEXT_PUBLIC_*` variables are public and are compiled into the browser bundle. Never put secrets in them.

Full deployment configuration is in [DEPLOYMENT.md](DEPLOYMENT.md).

---

## Model download and cache

- Model: `sentence-transformers/all-MiniLM-L6-v2`.
- Pinned revision: `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`.
- Tokenizer: `BertTokenizerFast`; verified maximum sequence length: 256; embedding dimension: 384.
- The model is loaded lazily once per process. Requirement and chunk embeddings use bounded in-process LRU caches, so a model is not reloaded for every candidate.
- On first use, Hugging Face downloads the pinned snapshot into its cache. Set `HF_HOME` to a persistent directory and keep it across restarts.
- `HF_HUB_OFFLINE=1` prevents downloads; if the cache is absent, semantic inference fails safely and the API reports fallback metadata instead of crashing.
- Loading errors are classified as package, import, DLL, download/cache, or loading failures.
- The pinned snapshot was verified locally to match the unpinned cached snapshot in config, tokenizer vocabulary, weights, and sample embeddings. Cross-environment bit-for-bit reproducibility is not claimed.

---

## Running the application

### Development backend

From `backend/`:

```powershell
py -3.10 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- Health: `http://localhost:8000/health`
- Swagger: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Development frontend

From `frontend/`:

```powershell
npm run dev
```

Open `http://localhost:3000`.

### Production mode locally

From `frontend/`:

```powershell
npm run lint
npx tsc --noEmit
npm run build
npm start -- -p 3000
```

From `backend/`:

```powershell
py -3.10 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

`--reload` must not be used in production.

---

## Testing

### Backend

Tests require an explicitly disposable database. The test suite refuses to run against the main database.

```powershell
$env:TEST_DATABASE_URL='postgresql+asyncpg://resume_user:resume_dev_password@localhost:5432/resume_screening_test'
Set-Location backend
py -3.10 -m pytest -q
```

The database name must end in `_test`. Database-backed fixtures roll back writes.

Final verification result: **317 passed, 2 warnings**. The warnings are dependency deprecations from AnyIO/Pytest and the FastAPI/Starlette test client; no test was skipped or weakened.

### Frontend

From `frontend/`:

```powershell
npm run lint
npx tsc --noEmit
npm run build
```

Final verification: ESLint clean, TypeScript clean, production build successful for `/` and `/_not-found`.

### Benchmark framework

Phase 11.5 tests are synthetic framework-validation tests only:

```powershell
Set-Location backend
py -3.10 -m pytest -q tests/test_phase11_5_benchmark.py
```

Real benchmark evaluation remains blocked because no genuine human-labelled JD/resume dataset exists. No accuracy claim is made.

---

## Production build and deployment

### Build

Backend has no separate build artifact; install dependencies and run Alembic plus Uvicorn.

Frontend:

```powershell
Set-Location frontend
npm ci
npm run lint
npx tsc --noEmit
npm run build
```

Set `NEXT_PUBLIC_BACKEND_URL` before `npm run build`.

### Deploy

- **Frontend:** Vercel or a Node host/container running `npm start`.
- **Backend:** container service, VM, or PaaS running `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
- **Database:** PostgreSQL 16; apply `alembic upgrade head` as a release step.
- **CORS:** add the deployed frontend origin to `CORS_ORIGINS`.
- **Storage:** mount a persistent volume at the path in `UPLOAD_STORAGE_DIR`; the container filesystem alone is not durable.
- **Model cache:** mount or preload a persistent `HF_HOME`; use `HF_HUB_OFFLINE=1` if downloads are disallowed.
- **Health check:** `GET /health`.

Exact manual steps are in [DEPLOYMENT.md](DEPLOYMENT.md). No deployment was performed automatically as part of final preparation.

---

## Database and persistence

### Tables

- `jobs`: title, description, flat skills, qualifications, experience text, `structured_requirements` JSONB, `analysis_data` JSONB.
- `resumes`: original filename, file type, candidate info JSONB, extracted text, skills JSONB, storage key, processing status.
- `screening_results`: scores, matched/missing/additional skills, explanation, evidence JSONB, requirement matches JSONB, scoring strategy JSONB. Unique on `(job_id, resume_id)`.

### Migration chain

1. `525a95dee632` — initial schema.
2. `add_evidence_fields` — evidence and scoring columns.
3. `add_structured_requirements` — `jobs.structured_requirements`.

### Backup and retention

- Back up PostgreSQL with normal database backups.
- Back up `UPLOAD_STORAGE_DIR`; the database stores only storage keys.
- Generated reports are in-memory and disappear when the API restarts.
- There is no UI or API for deleting jobs/resumes; plan retention explicitly.

---

## API

Base path: `/api/v1`

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Liveness/version check |
| `POST` | `/jobs/analyze` | Analyze and persist a job description |
| `GET` | `/jobs/{job_id}` | Retrieve a stored job analysis |
| `POST` | `/resumes/upload` | Upload and process one or more resumes (`files` multipart field) |
| `GET` | `/resumes/{resume_id}` | Retrieve a stored resume |
| `POST` | `/matching/evaluate` | Rank candidates for a job |
| `POST` | `/reports/generate` | Generate a JSON or CSV report |
| `GET` | `/reports/{report_id}` | Retrieve a generated report from the in-memory store |

Example matching request:

```json
{
  "job_id": "<uuid>",
  "resume_ids": ["<uuid>"],
  "use_semantic": true
}
```

The matching response includes per-candidate scores, matched/missing/additional skills, evidence, requirement evaluations, group evaluation, strengths, gaps, explanation, `scoring_strategy`, and an `error` field for failed candidates.

---

## Scoring and structured requirements

### Default weights

Defined in `backend/app/services/scoring_service.py`:

| Component | Weight |
|---|---:|
| Required-skill coverage | 35% |
| Preferred-skill coverage | 15% |
| Semantic similarity | 30% |
| Evidence strength | 20% |
| TF-IDF similarity | 0% (computed only when enabled in code) |

These weights were not changed during final preparation.

### Behavior

- Structured requirements are authoritative when present.
- `ANY`: one matched alternative satisfies the group; unmatched alternatives in a satisfied group are not gaps.
- `ALL`: every member must match.
- Related-skill partial credit threshold is `0.5`.
- Education-aware keyword-stuffing analysis is enabled but its score penalty is disabled by default.
- If semantic inference is unavailable, the semantic weight is removed and the non-semantic configured weights are renormalized: required skills 0.35/0.70 ≈ 50%, preferred skills 0.15/0.70 ≈ 21.4%, evidence 0.20/0.70 ≈ 28.6%, TF-IDF 0%. `scoring_strategy.fallback_used` is set to `true`, and `semantic_status` is `model_unavailable`, `inference_failed`, or `empty_text`.
- `skill_match_score` is an alias of required-skill coverage for backward compatibility.

Scores are decision-support signals. They are not objective measures of candidate quality or hiring recommendations.

---

## Known limitations

1. **Ranking accuracy is unverified.** No genuine human-labelled held-out benchmark exists. Phase 11.5 infrastructure exists, but its real-data evaluation is pending and no accuracy claim is permitted.
2. **No authentication or authorization.** Anyone who can reach the API can read or create data.
3. **Development credentials and CORS defaults** are suitable only for local use.
4. **No rate limiting, audit logging, tenant isolation, or formal security/privacy/fairness audit.**
5. **PostgreSQL is published on all host interfaces** by the local Compose file.
6. **Uploaded files use local filesystem storage.** A persistent volume or host directory is required in deployment.
7. **Generated reports are in memory** and disappear on API restart.
8. **Screening results are write-only through the public API**; there is no listing endpoint.
9. **No OCR.** Scanned/image-only PDFs require external OCR.
10. **English-oriented heuristics** and skill taxonomy.
11. **Structured requirement parsing is heuristic** and may miss unusual phrasing.
12. **The semantic model revision is pinned locally**, but cross-environment reproducibility is not claimed. On this Windows environment, importing scikit-learn before torch can trigger a torch DLL initialization conflict; the service falls back safely. Preload `sentence_transformers` before the application service if semantic inference is required in a similar environment.
13. **No browser-level E2E automation.** Final UI verification used lint, typecheck, production build, served-page checks, and direct API contract checks.
14. **Historical phase reports are not part of the release.** This README and `DEPLOYMENT.md` are the authoritative current documentation.
15. **The working tree is uncommitted** and contains extensive historical deletions/dirty work; do not run destructive Git cleanup.
16. **No license file is included.**

---

## GitHub handoff

The working tree is intentionally left uncommitted. Review Git status before pushing; do not stage, commit, or push automatically.

Generated artifacts that should remain ignored:

- `backend/**/__pycache__/`, `.pytest_cache/`
- `frontend/node_modules/`, `frontend/.next/`, `frontend/out/`
- real `.env`, `.env.local`, and backend `.env` files
- uploaded resumes and generated PDF/DOCX files
- model caches and large datasets

Committed environment templates:

- `.env.example`
- `frontend/.env.example` (explicitly unignored)

No real secrets should be committed. If a secret was ever committed historically, rotate it before pushing.

The repository has a large number of historical dirty/deleted paths from prior phases. This is pre-existing state; preserve it and explain it rather than cleaning it automatically.

---

## Documentation

- [DEPLOYMENT.md](DEPLOYMENT.md) — manual deployment instructions.
- [backend/README.md](backend/README.md) — backend-only quick start and layout.
- API reference — run the backend and open `/docs`.
