# 09 — Local Setup

This chapter records the setup path documented in `README.md`, `backend/README.md`, `DEPLOYMENT.md`, and the environment/config files in the repository.

## Prerequisites

| Requirement | Recorded version or note |
|---|---|
| Docker with Docker Compose | Used for local PostgreSQL. |
| Python | Python 3.10 is the documented interpreter; README records verification with 3.10.11. |
| Node.js and npm | Node 20.9+ documented; README records verification with Node 22.18.0 and npm 10.9.8. |
| Internet or pre-populated cache | Needed on first semantic-model use unless the Hugging Face cache is already available. |
| Writable local directory | Needed for uploaded resumes; default is `storage/uploads` relative to the backend process. |

Python's Windows launcher is `py -3.10`. Use `python3.10` on Linux or macOS.

## 1. Start PostgreSQL

From the repository root:

```powershell
docker compose up -d postgres
docker compose ps
```

`docker-compose.yml` defines one service:

- image `postgres:16`
- container `resume-parser-db`
- database `resume_screening`
- user `resume_user`
- password `resume_dev_password`
- host port `5432`
- named volume `postgres_data`
- healthcheck using `pg_isready`

It does not start the backend or frontend.

## 2. Create the Python environment

From the repository root:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

On Linux or macOS:

```bash
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
```

`backend/requirements.txt` includes the backend runtime and test dependencies, including `pytest>=9.2.0`, `httpx>=0.25.0`, and `pytest-asyncio>=1.5.0`.

## 3. Configure environment files

From the repository root:

```powershell
Copy-Item .env.example backend\.env
Copy-Item frontend\.env.example frontend\.env.local
```

The root `.env.example` documents both backend and frontend variables. `frontend/.env.example` contains only `NEXT_PUBLIC_BACKEND_URL`.

### Backend variables

| Variable | Default / example | Notes |
|---|---|---|
| `APP_NAME` | `AI Resume Screening Backend` | Application title. |
| `APP_VERSION` | `0.1.0` | Application version. |
| `DEBUG` | `false` | Also controls SQLAlchemy `echo`. |
| `API_PREFIX` | `/api/v1` | Router prefix. |
| `CORS_ORIGINS` | `["http://localhost:3000","http://127.0.0.1:3000"]` | JSON array of allowed browser origins. |
| `POSTGRES_HOST` | `localhost` | Used to build the database URL. |
| `POSTGRES_PORT` | `5432` | Used to build the database URL. |
| `POSTGRES_DB` | `resume_screening` | Used to build the database URL. |
| `POSTGRES_USER` | `resume_user` | Used to build the database URL. |
| `POSTGRES_PASSWORD` | `resume_dev_password` | Used to build the database URL. |
| `TEST_DATABASE_URL` | unset by default | Only for tests; must end in `_test` and must not be the main database. |
| `UPLOAD_STORAGE_DIR` | `storage/uploads` | Relative paths resolve from the backend process working directory. |

`backend/app/core/config.py::Settings.DATABASE_URL` is a computed property built from the `POSTGRES_*` values. An environment variable named `DATABASE_URL` is intentionally not read.

### Semantic model variables

| Variable | Default | Notes |
|---|---|---|
| `SEMANTIC_MODEL_NAME` | `sentence-transformers/all-MiniLM-L6-v2` | Read directly in `semantic_matching_service.py`. |
| `SEMANTIC_MODEL_REVISION` | `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` | Default applies to the standard model; custom models default to `main`. |
| `HF_HOME` | unset | Hugging Face cache location; point at a persistent path when needed. |
| `HF_HUB_OFFLINE` | `0` | Set to `1` to disallow downloads. |
| `HF_HUB_DISABLE_TELEMETRY` | `1` | Hugging Face library control. |

The `HF_*` variables are library-level controls documented in `.env.example`; they are not fields on `Settings`.

### Frontend variable

| Variable | Default | Notes |
|---|---|---|
| `NEXT_PUBLIC_BACKEND_URL` | `http://localhost:8000` | Browser-visible backend origin; never put secrets in a `NEXT_PUBLIC_*` variable. |

## 4. Apply database migrations

From `backend/`:

```powershell
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m alembic current
```

The expected head is `add_structured_requirements`. The chain is:

1. `525a95dee632_initial_database_schema.py`
2. `add_evidence_fields.py`
3. `add_structured_requirements.py`

Application startup does not run migrations automatically.

## 5. Install frontend dependencies

From `frontend/`:

```powershell
npm ci
```

`frontend/package-lock.json` is committed, so `npm ci` is the reproducible install command.

## 6. Run in development

Start the backend from `backend/`:

```powershell
py -3.10 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Available backend URLs:

- health: `http://127.0.0.1:8000/health`
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

Start the frontend from `frontend/`:

```powershell
npm run dev
```

Open `http://localhost:3000`.

## 7. Verify the setup

1. The frontend header should eventually show `Connected`; it polls `/health` every 30 seconds.
2. `GET /health` should return `status`, `version`, and `app_name`.
3. Analyze a short JD in the UI and confirm an extracted-requirements card appears.
4. Upload a small PDF or DOCX and confirm a success status.
5. Run screening and confirm a ranked results table appears.
6. Expand a candidate and confirm score, evidence, explanation, and strengths/gaps render.
7. Download a CSV report.

If semantic inference fails, the backend should still score candidates and the candidate detail view should indicate that semantic matching is unavailable. The backend logs and `scoring_strategy` contain more detail.

## Running backend tests

Set a disposable database URL first:

```powershell
$env:TEST_DATABASE_URL='postgresql+asyncpg://resume_user:resume_dev_password@localhost:5432/resume_screening_test'
Set-Location backend
py -3.10 -m pytest -q
```

The test database must already exist and must not be the main database. Test fixtures roll back writes. Creating the test database is a manual prerequisite because `Settings` only validates that `TEST_DATABASE_URL` is present; the suffix and main-database checks live in `backend/tests/conftest.py`.

## Running local production-mode checks

Frontend:

```powershell
Set-Location frontend
npm run lint
npx tsc --noEmit
npm run build
npm start -- -p 3000
```

Backend:

```powershell
Set-Location backend
py -3.10 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Do not use `--reload` for a production-style run.

## Common configuration pitfalls

- Setting `DATABASE_URL` does nothing; configure `POSTGRES_*`.
- Using the main database as `TEST_DATABASE_URL` is rejected by the test suite.
- Running uvicorn from the wrong directory can place `storage/uploads` in an unexpected location.
- `CORS_ORIGINS` must be a valid JSON array containing the exact frontend origin.
- `NEXT_PUBLIC_BACKEND_URL` must point to a reachable backend origin from the browser.
- Pinned model artifacts may need to be downloaded on first use unless `HF_HOME` is pre-populated.
- The legacy Streamlit app under `app.py` and `src/` is not started by these commands.
