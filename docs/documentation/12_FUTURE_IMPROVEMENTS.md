# 12 — Future Improvements

Everything in this chapter is **proposed** and is not implemented in the current codebase. It is grouped by the source-backed limitation it addresses.

## Priority summary

| Priority | Proposal | Limitation addressed |
|---|---|---|
| High | Build a genuine human-labelled benchmark and accuracy gate | Ranking quality is currently unverified. |
| High | Add authentication and per-user data isolation | No identity or authorization layer exists. |
| High | Containerize backend and frontend; persist uploads and model cache | Compose only defines PostgreSQL. |
| High | Move reports into durable storage | Reports are process-local and lost on restart. |
| Medium | Add OCR/layout-aware parsing | Scanned PDFs are only flagged; parsing is heuristic. |
| Medium | Validate a dedicated experience/qualification component | Experience and qualifications are metadata only. |
| Medium | Add runtime API contract validation on the frontend | TypeScript types do not validate payloads. |
| Medium | Add frontend tests and API integration tests | No frontend test suite exists. |
| Medium | Normalize API error responses | `ErrorResponse` is unused; no global handlers. |
| Lower | Add observability, caching controls, and performance testing | No request metrics or timing are exposed. |
| Lower | Improve frontend accessibility and progressive feedback | Native alerts and indeterminate spinner only. |

## 1. Ranking validation and calibration

Current state:

- The live pipeline has no human-labelled held-out benchmark wired into scoring.
- `backend/app/evaluation/` contains schemas, metrics, split helpers, and calibration scripts, but no genuine labels or results.
- `pilot_target_manifest()` reports `not_collected`, `labelled_pairs = 0`, and `claim_permitted = False`.
- The synthetic `evaluation_dataset.py` contains author-written examples, not independent human annotations.
- General claim gates require at least 20 total JDs, at least 6 held-out JDs, at least 2 held-out JDs per role, positive paired-bootstrap confidence lower bound, reviewer agreement, and zero scoring failures.

Proposal:

1. Collect multi-reviewer relevance grades using `backend/app/evaluation/annotation_schema.py`.
2. Adjudicate disagreements and report Cohen's kappa or Krippendorff's alpha.
3. Freeze JD-level splits with `semantic_dataset_split.py` before tuning.
4. Tune only on development data with `semantic_calibration.py`.
5. Evaluate baseline and proposed systems with `semantic_benchmark.py` using `--allow-real-model` in a controlled environment.
6. Publish NDCG@3, MRR, precision/recall at k, confidence intervals, latency, failure counts, and score-distribution diagnostics.
7. Only then consider changing the 35/15/30/20 weights.

This is a future activity; no accuracy claim is permitted from the current source.

## 2. Authentication and authorization

Current state:

- no user accounts,
- no login or token validation,
- no roles,
- no per-recruiter data partitioning,
- no audit trail of who screened whom.

Proposal:

- add identity provider integration or local accounts,
- scope jobs, resumes, screening results, and reports to an owner or workspace,
- add authorization dependencies to every route except `/health`,
- record audit events for analysis, upload, evaluation, and export,
- redact candidate PII in logs and error messages.

## 3. Deployment and operational hardening

Current state:

- `docker-compose.yml` defines only PostgreSQL 16,
- upload storage is a local directory relative to the backend process,
- model artifacts rely on the local Hugging Face cache,
- reports are in-memory,
- CORS is limited to localhost origins by default.

Proposal:

- add backend and frontend container definitions,
- mount persistent volumes for uploads and the Hugging Face cache,
- use managed object storage for uploaded resumes,
- add health/readiness endpoints that check database, storage, and model state,
- make CORS origins environment-specific,
- define resource limits and graceful shutdown,
- add migration execution as an explicit deployment step,
- document a multi-worker strategy that does not depend on process-local report state.

## 4. Durable report storage

Current state:

- `report_repository` is an in-memory dictionary,
- reports are unavailable after restart and across workers,
- `ReportResponse.report_id` is not used by the visible UI.

Proposal:

- add a `reports` table or object-store bucket,
- persist report content, format, job ID, resume ID, generator version, and creation time,
- add an authenticated download endpoint that streams content with correct MIME types,
- let the UI reuse the returned report ID instead of immediately downloading generated content.

## 5. Parsing and document handling

Current state:

- PDF extraction uses PyMuPDF and flags low-text documents as likely scanned,
- there is no OCR,
- section and skill extraction rely on patterns and curated dictionaries,
- DOCX table extraction is basic,
- generic upload errors hide details from the client.

Proposal:

- add OCR for scanned PDFs with explicit quality metadata,
- add layout-aware extraction for tables, columns, and multi-page resumes,
- expand and validate the skills database,
- add confidence scores to parsed fields,
- preserve `num_paragraphs` in resume retrieval,
- introduce structured errors that are safe to show to the client while retaining internal detail in logs.

## 6. Experience and qualification scoring

Current state:

- JD experience and qualifications are extracted and stored,
- resume experience and projects are classified and temporally annotated,
- these fields enrich evidence and explanations,
- no dedicated weight or multiplier affects the final score.

Proposal:

- define a transparent experience/qualification component with explicit rules,
- validate it against human-labelled relevance before adding it to the formula,
- document new weights and fallback behavior,
- expose per-component contributions in `scoring_strategy`,
- avoid double-counting experience already reflected in evidence.

## 7. API and frontend contract quality

Current state:

- frontend TypeScript types mirror backend schemas but are incomplete in places,
- there is no runtime payload validation on the frontend,
- `ErrorResponse` is defined but unused,
- report generation uses query parameters while an unused `ReportRequest` body schema exists,
- job/resume UUIDs and format values are validated manually in routes.

Proposal:

- generate TypeScript client types from OpenAPI,
- add runtime validation at the API boundary,
- standardize errors through global FastAPI handlers,
- remove or wire the unused `ReportRequest` schema,
- add a consistent HTTP status taxonomy,
- add contract tests between frontend client methods and backend routes.

## 8. Testing and CI

Current state:

- backend has a broad pytest suite under `backend/tests/`,
- frontend has no test script or test files,
- evaluation scripts are fail-closed but are not a substitute for product tests,
- CI configuration is not present in the tracked source inventory reviewed for this suite.

Proposal:

- add frontend component and workflow tests,
- add API contract tests for all eight endpoints,
- add tests for multi-worker report behavior if durable reports are introduced,
- add CI checks for formatting, lint, type checking, backend tests, frontend build, and dependency vulnerability scans,
- keep evaluation scripts separate from unit tests and label synthetic data clearly.

## 9. User experience

Current state:

- one client page with local state,
- no upload progress percentage,
- no filtering, sorting, or searching in the results table,
- native `alert()` dialogs for validation and export errors,
- health status is informational only,
- JSON export exists in the client method but not in the visible UI.

Proposal:

- add real upload and evaluation progress states,
- add sorting, filtering, and comparison across candidates,
- replace native dialogs with accessible inline components,
- expose JSON and CSV export choices,
- gate screening with actionable connection and validation messages,
- persist draft workflow state across reloads,
- add keyboard and screen-reader improvements.

## 10. Observability and performance

Current state:

- semantic caches expose statistics in service code but no HTTP endpoint or dashboard,
- evaluation scripts record latency when explicitly run,
- no request IDs, structured logs, metrics endpoint, or tracing is wired into `main.py`,
- all parsing and scoring happen synchronously in request handlers.

Proposal:

- add structured request logging with correlation IDs,
- expose database, storage, and model readiness checks,
- record per-stage latency for parsing, embedding, scoring, and report generation,
- add background job processing for large batches,
- benchmark throughput and memory under realistic resume sizes,
- document capacity limits and worker configuration.

## Explicit non-goals for this documentation update

This documentation task did not implement any of the proposals above. No application source code, configuration, dependency manifest, migration, or test was changed. The purpose of this chapter is to record credible next steps without presenting them as existing features.
