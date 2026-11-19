# HireLens Backend

FastAPI backend for resume parsing, job-description analysis, evidence-aware scoring, matching, and reports.

For the current application overview, environment reference, and deployment instructions, use:

- [Root README](../README.md)
- [Deployment guide](../DEPLOYMENT.md)

## Quick start

Run from this `backend/` directory so `storage/uploads` and `backend/.env` resolve as documented.

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
py -3.10 -m alembic upgrade head
py -3.10 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Production starts the same app without `--reload`:

```powershell
py -3.10 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Health: `GET /health`. API docs: `/docs` and `/redoc`.

## Environment

Copy the root `.env.example` to `backend/.env`. The backend builds `DATABASE_URL` from `POSTGRES_*`; it does not read a separate application `DATABASE_URL`.

Important settings:

- `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- `CORS_ORIGINS` — JSON array of deployed frontend origins
- `UPLOAD_STORAGE_DIR` — persistent upload directory (default `storage/uploads`)
- `TEST_DATABASE_URL` — disposable test database, required by the test suite
- `SEMANTIC_MODEL_NAME` / `SEMANTIC_MODEL_REVISION` — model runtime overrides
- `HF_HOME` / `HF_HUB_OFFLINE` — model cache controls

See the root `.env.example` and `DEPLOYMENT.md` for the full list.

## Tests

Never run the test suite against the main database. The suite requires an explicit disposable URL whose database name ends in `_test`.

```powershell
$env:TEST_DATABASE_URL='postgresql+asyncpg://resume_user:resume_dev_password@localhost:5432/resume_screening_test'
py -3.10 -m pytest -q
```

Final verification: **317 passed, 2 dependency deprecation warnings**.

## Layout

```text
backend/
├── app/
│   ├── api/routes/       jobs, resumes, matching, reports
│   ├── core/             settings and exceptions
│   ├── db/               async engine and sessions
│   ├── evaluation/       Phase 11.5 benchmark framework
│   ├── models/           SQLAlchemy models
│   ├── repositories/     PostgreSQL data access
│   ├── schemas/          Pydantic schemas
│   ├── services/         parsing, semantic, evidence, and scoring services
│   └── utils/            text and JSONB helpers
├── alembic/versions/     migrations
├── evaluation/           template and reports
├── scripts/              benchmark and evaluation CLIs
├── tests/                pytest suite
└── requirements.txt
```

## Notes

- The semantic model is `sentence-transformers/all-MiniLM-L6-v2` pinned to revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`.
- If semantic inference is unavailable, scoring falls back to required/preferred coverage and records `fallback_used=true`.
- Generated reports are stored in memory and disappear when the API process restarts.
- Ranking accuracy has not been validated on a genuine human-labelled held-out dataset.
