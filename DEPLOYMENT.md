# HireLens Deployment Guide

This document describes how to deploy the existing HireLens application without adding features. The application has two independently deployed parts:

- **Frontend:** Next.js 16 app in `frontend/`; deploy to Vercel or any Node-capable host.
- **Backend:** long-running FastAPI process in `backend/`; deploy to a container service, VM, or PaaS that supports a persistent process.
- **Database:** PostgreSQL 16; schema is managed with Alembic.
- **State:** uploaded resumes use a local filesystem directory. Generated reports are process-local and are not durable.

FastAPI is **not** deployed as part of the Next.js application. Do not assume a Vercel deployment can serve the backend API.

---

## 1. Prerequisites

- PostgreSQL 16 (or a compatible managed PostgreSQL service).
- Python 3.10 runtime for the backend.
- Node.js 20.9+ (verified 22.18.0) and npm 10+ for the frontend.
- A persistent directory for uploaded resume files.
- A persistent directory for the Hugging Face model cache, or a preloaded image cache.
- Network access on first model download unless the cache is pre-populated.

---

## 2. Backend deployment

### 2.1 Install

From `backend/`:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

On Linux/macOS use the equivalent `python3.10 -m venv .venv` and activation commands.

### 2.2 Environment

Set these in the backend process environment (or a protected `backend/.env` file):

```env
APP_NAME=HireLens API
APP_VERSION=0.1.0
DEBUG=false
API_PREFIX=/api/v1
CORS_ORIGINS=["https://your-frontend.example"]
POSTGRES_HOST=your-postgres-host
POSTGRES_PORT=5432
POSTGRES_DB=hirelens
POSTGRES_USER=hirelens_app
POSTGRES_PASSWORD=<secret-from-your-secret-manager>
UPLOAD_STORAGE_DIR=/var/lib/hirelens/uploads
HF_HOME=/var/cache/hirelens/huggingface
HF_HUB_OFFLINE=0
HF_HUB_DISABLE_TELEMETRY=1
SEMANTIC_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
SEMANTIC_MODEL_REVISION=1110a243fdf4706b3f48f1d95db1a4f5529b4d41
```

Notes:

- `DATABASE_URL` is computed from `POSTGRES_*`; do not set a separate URL for the application.
- `CORS_ORIGINS` must be a JSON array and must exactly include the deployed frontend origin.
- `UPLOAD_STORAGE_DIR` must be writable and backed by persistent storage. If it is left as the default `storage/uploads`, files are relative to the API working directory and may be lost when a container is replaced.
- `HF_HOME` must be persistent or baked into the image to avoid repeated model downloads.
- Do not put production credentials in `.env.example`, source files, or a public Git repository.

### 2.3 Migrate

Run once per deployment/release before starting the new API process:

```powershell
Set-Location backend
$env:POSTGRES_HOST='your-postgres-host'
$env:POSTGRES_DB='hirelens'
$env:POSTGRES_USER='hirelens_app'
$env:POSTGRES_PASSWORD='<secret>'
py -3.10 -m alembic upgrade head
py -3.10 -m alembic current
```

Expected revision: `add_structured_requirements (head)`.

Migrations are additive. Do not run downgrades against a database that holds data you need.

### 2.4 Start

From `backend/`:

```powershell
py -3.10 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

For a container, use the same command as the process entrypoint and publish port 8000. Configure the platform health check to call `GET /health`.

The health response is a liveness check (`status`, `version`, `app_name`). Semantic readiness is reported per scoring request in `scoring_strategy.semantic_status`, `semantic_model_available`, `semantic_error`, and `semantic_details`.

### 2.5 Backups and persistence

- Back up PostgreSQL using your provider's normal database backup mechanism.
- Back up the directory named by `UPLOAD_STORAGE_DIR`; the database stores only a storage key and parsed data, not the original file bytes.
- Generated reports live in process memory and intentionally disappear on restart. Re-generate them through `POST /api/v1/reports/generate`.

---

## 3. Frontend deployment

### 3.1 Build locally

From `frontend/`:

```powershell
npm ci
npm run lint
npx tsc --noEmit
npm run build
```

`NEXT_PUBLIC_BACKEND_URL` is embedded at build time. Set it before `npm run build` when building for a deployed backend:

```powershell
$env:NEXT_PUBLIC_BACKEND_URL='https://api.your-domain.example'
npm run build
```

Only `NEXT_PUBLIC_*` values are browser-visible. Never put a secret in one of them.

### 3.2 Vercel

Create a Vercel project rooted at `frontend/`:

- Framework preset: Next.js.
- Build command: `npm run build`.
- Output: default Next.js output.
- Environment variable: `NEXT_PUBLIC_BACKEND_URL=https://api.your-domain.example`.
- Add the Vercel origin to the backend `CORS_ORIGINS`.
- Redeploy after changing `NEXT_PUBLIC_BACKEND_URL` because it is compiled into the client bundle.

No FastAPI process is created by Vercel; keep the backend deployed separately.

### 3.3 Node host / container

From `frontend/`:

```powershell
npm ci
npm run build
npm start -- -p 3000
```

Publish port 3000 and configure the backend CORS list with the public frontend origin.

---

## 4. Model cache behaviour

- Model: `sentence-transformers/all-MiniLM-L6-v2`
- Pinned revision: `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`
- Tokenizer: `BertTokenizerFast`, maximum sequence length 256.
- The model is loaded lazily once per process and embeddings are cached in bounded in-process LRU caches.
- On first use without a populated cache, Hugging Face downloads the snapshot. Set `HF_HUB_OFFLINE=1` to fail cleanly instead of downloading.
- If loading fails, the API returns a scored result using the documented fallback and sets `scoring_strategy.fallback_used=true`; the process does not crash.
- On Windows hosts where scikit-learn is imported before torch, a DLL initialization conflict can prevent model loading. Preload `sentence_transformers` before the backend service in such environments, or accept the documented fallback.

The pinned snapshot was verified locally to have identical config, tokenizer vocabulary, weights, and embeddings to the cached unpinned snapshot. Cross-environment bit-for-bit reproducibility is not claimed.

---

## 5. Local Docker Compose

`docker-compose.yml` provisions PostgreSQL 16 only. It does not build or run the API or frontend.

```powershell
docker compose up -d postgres
docker compose ps
```

The named volume `postgres_data` persists the local database. Never run `docker compose down -v` unless you intentionally want to delete that data.

---

## 6. Post-deployment verification

1. `GET /health` returns HTTP 200.
2. `GET /docs` is available when desired (disable or protect it for public deployments if needed).
3. Analyze a synthetic job description through `POST /api/v1/jobs/analyze`.
4. Upload synthetic PDF and DOCX files through `POST /api/v1/resumes/upload`.
5. Run `POST /api/v1/matching/evaluate` and confirm results are sorted by `overall_score`.
6. Confirm `scoring_strategy.semantic_status` is `used` or an expected fallback.
7. Generate JSON and CSV reports through `POST /api/v1/reports/generate`.
8. Confirm the frontend loads and can reach the backend origin without CORS errors.
9. Confirm uploads appear under the configured persistent `UPLOAD_STORAGE_DIR`.

Use synthetic documents for deployment checks. Ranking accuracy has not been validated on a genuine human-labelled held-out dataset.
