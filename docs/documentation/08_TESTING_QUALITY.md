# 08 — Testing and Quality

This chapter describes the test assets that exist in the repository and the limits of what they prove.

## Backend test suite

Backend tests live under `backend/tests/`. The test files present in the tracked source are:

| Area | Test files |
|---|---|
| Application and config | `test_main.py`, `test_config.py`, `test_test_isolation.py`, `test_schemas.py` |
| HTTP API | `test_api.py` |
| Document and storage | `test_document_service.py`, `test_file_storage.py`, `test_resume_parser_service.py`, `test_section_detection.py` |
| Matching and scoring | `test_matching_service.py`, `test_matching_accuracy.py`, `test_scoring_service.py`, `test_score_stability.py`, `test_phase11_3_scoring_correctness.py`, `test_bug_fixes.py` |
| Evidence and semantics | `test_evidence_extraction.py`, `test_group_evidence_semantics.py`, `test_requirement_semantic_service.py`, `test_semantic_input_service.py`, `test_semantic_matching.py`, `test_semantic_intelligence.py` |
| Persistence | `test_jsonb_persistence.py` |
| Evaluation utilities | `test_phase11_5_benchmark.py`, `test_semantic_pipeline_baseline.py` |

`backend/tests/conftest.py` contains shared fixtures and test database isolation. Configuration is in `backend/pytest.ini`:

```ini
[pytest]
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
testpaths = tests
python_files = test_*.py
markers =
    db: test requires the disposable TEST_DATABASE_URL database
    e2e: test exercises the API through the ASGI transport
```

The application reads `TEST_DATABASE_URL` only for tests. `validate_test_database_url()` in `backend/tests/conftest.py` requires the variable, rejects missing or malformed URLs, rejects the main database, and enforces a `_test` suffix. Test fixtures roll back database writes.

There are 24 `test_*.py` files containing 310 test function definitions. Two parameterized functions expand the collected total to 317 cases.

The command recorded in `README.md` and `backend/README.md` is run from the repository root environment with a disposable test database:

```powershell
$env:TEST_DATABASE_URL='postgresql+asyncpg://resume_user:resume_dev_password@localhost:5432/resume_screening_test'
Set-Location backend
py -3.10 -m pytest -q
```

For the benchmark framework subset:

```powershell
Set-Location backend
py -3.10 -m pytest -q tests/test_phase11_5_benchmark.py
```

Those README files record a final backend result of **317 passed, 2 warnings**. The warnings are AnyIO/Pytest and FastAPI/Starlette test-client dependency deprecations; no test was skipped or weakened. Those are repository-recorded results, not a new test run performed for this documentation.

## Frontend quality checks

The frontend has no test files and no `test` script. Available scripts in `frontend/package.json`:

```bash
npm run dev
npm run build
npm run start
npm run lint
```

`npm run lint` invokes ESLint with the Next.js core-web-vitals and TypeScript configurations from `frontend/eslint.config.mjs`. `npm run build` invokes `next build`.

The checks recorded in `README.md` are:

```powershell
Set-Location frontend
npm run lint
npx tsc --noEmit
npm run build
```

The recorded result is: ESLint clean, TypeScript clean, and production build successful for `/` and `/_not-found`.

TypeScript strict mode is enabled in `frontend/tsconfig.json`. This catches type-level mistakes but does not validate runtime API payloads.

## What the tests cover conceptually

Based on test names and imported modules, the suite covers:

- health and API behavior
- configuration and test database isolation
- Pydantic schemas
- document validation and extraction
- resume field parsing and section detection
- file storage validation and path-key safety
- evidence extraction and group semantics
- semantic input construction and semantic scoring
- canonical scoring, score stability, and phase-specific scoring correctness
- JSONB persistence
- legacy matching service behavior
- evaluation framework behavior and legacy semantic baseline characterization

These are code-level tests. They do not constitute a human-labelled ranking accuracy benchmark.

The `db` and `e2e` markers are declared in `pytest.ini` and re-registered in `conftest.py`, but no test function currently uses them. There are 18 `skipif` decorators guarding optional imports such as parsing libraries, `sentence-transformers`, and scoring or semantic imports. No `skip` or `xfail` markers are recorded in the test source.

Separate legacy root tests exist at `tests/test_information_extractor.py`, `tests/test_resume_extractor.py`, and `tests/test_resume_matcher.py`. They exercise the older `src/` Streamlit-era modules and are not part of the active backend suite.

## Evaluation utilities

`backend/app/evaluation/` contains eight modules and no `__init__.py`; it behaves as an implicit namespace package. These modules are not imported by `backend/app/main.py` or the live API routes. They are used by scripts under `backend/scripts/` and by evaluation tests.

| Module | Purpose |
|---|---|
| `annotation_schema.py` | Phase 11.5 human annotation schema, rubric, validation, agreement statistics. |
| `evaluation_dataset.py` | Ten hand-written synthetic examples for three role categories. |
| `evaluation_metrics.py` | Generic ranking, skill extraction, and evidence metrics. |
| `semantic_metrics.py` | Phase 11.5 ranking metrics, ties, correlations, confidence intervals, paired bootstrap. |
| `semantic_intelligence_dataset.py` | Phase 11.4 benchmark schema/scaffold and claim gates; no examples included. |
| `semantic_dataset_split.py` | Deterministic JD-level split freezing and leakage checks. |
| `semantic_calibration.py` | Development-only parameter search with production-parity checks. |
| `semantic_benchmark.py` | Baseline versus proposed ranking runner using real services when explicitly enabled. |

### Annotation and benchmark schemas

`annotation_schema.py` defines:

- `ANNOTATION_SCHEMA_VERSION = "phase11_5_annotation_v1"`
- `RUBRIC_VERSION = "phase11_5_relevance_v1"`
- a five-level relevance grade from `NOT_RELEVANT` to `EXCELLENT_MATCH`
- `LabelledBenchmark`, `JobRecord`, `ResumeRecord`, and `AnnotationRecord`
- `validate_benchmark`, `require_valid`, consensus grades, disagreement summaries, and readiness checks
- unweighted and quadratic weighted Cohen's kappa, Krippendorff's alpha, and agreement summaries

`semantic_intelligence_dataset.py` defines the earlier Phase 11.4 scaffold with:

- `RUBRIC_VERSION = "phase11_4_relevance_v1"`
- `DATASET_SCHEMA_VERSION = "phase11_4_benchmark_v1"`
- `LabelledPair` and `BenchmarkDataset`
- empty pilot dataset and target manifests
- validation, JD-level split assignment, kappa, and a general-claim gate

### Metrics

`evaluation_metrics.py` implements:

- precision@k and recall@k
- NDCG with linear gains
- mean reciprocal rank
- skill extraction precision, recall, and F1
- evidence precision and section classification accuracy

`semantic_metrics.py` implements Phase 11.5 deterministic metrics with:

- `DEFAULT_K_VALUES = (1, 3, 5, 10)`
- graded gain `2**grade - 1`
- average tie ranks and stable descending rank order
- NDCG, precision@k, recall@k, MRR, Spearman, and Kendall tau-b
- missing-score accounting
- normal confidence intervals and paired bootstrap confidence intervals with seed `20261119`

### Splitting and claim gates

`semantic_dataset_split.py` uses:

- `SPLIT_ALGORITHM_VERSION = "phase11_5_jd_hash_split_v1"`
- `SPLIT_SEED = 20261119`
- SHA-256-based JD ordering and dataset hashing
- leakage checks that move shared candidates entirely to held-out
- a claim gate requiring valid splits, at least six held-out JDs, at least twenty total JDs, at least two held-out JDs per role, positive bootstrap lower bound, reviewer agreement, and zero scoring failures

`semantic_calibration.py` tunes only on development data. It defines `DEFAULT_PARAMETERS`, eight `CANDIDATE_PARAMETERS`, production-parity checks, and `require_development_split`.

`semantic_benchmark.py` compares:

- `BASELINE_SYSTEM = "baseline_whole_document"`
- `PROPOSED_SYSTEM = "phase11_4_requirement_chunk"`

It requires labels and explicit `--allow-real-model` opt-in before producing measured results. Failures are recorded rather than silently dropped.

## Evaluation scripts

| Script | Purpose |
|---|---|
| `backend/scripts/prepare_semantic_benchmark.py` | Create annotation templates or check benchmark readiness. |
| `backend/scripts/evaluate_semantic_benchmark.py` | Run Phase 11.5 baseline-versus-proposed evaluation with split, parameter, and model gates. |
| `backend/scripts/evaluate_semantic_intelligence.py` | Run Phase 11.4 dataset evaluation with explicit dataset/model opt-in. |
| `backend/scripts/analyze_semantic_errors.py` | Categorize error cases from measured evaluation results. |
| `backend/scripts/evaluate_matching.py` | Run the synthetic dataset with semantic disabled and write JSON/Markdown reports. |

These scripts are evaluation tools, not live application endpoints.

## Important quality limits

1. **No genuine human-labelled benchmark exists in the repository.** The annotation template is empty and the pilot manifest reports no collected labels.
2. **Synthetic examples are not benchmark evidence.** `evaluation_dataset.py` contains ten hand-written examples.
3. **No ranking accuracy claim is permitted.** The source's claim gates are deliberately fail-closed.
4. **Real-model evaluation requires explicit opt-in.** Without `--allow-real-model`, scripts return blocked statuses rather than metrics.
5. **No frontend tests exist.** UI correctness is currently supported only by lint and build checks.
6. **TypeScript types are not runtime validation.** Backend field additions or omissions can pass type checking and still affect UI rendering.
7. **`/health` is liveness only.** It does not verify database, storage, or model readiness.
8. **Evaluation scripts are separate from production scoring.** Importing `app.evaluation` does not change the live API.

## Relationship to product confidence

The test suite supports implementation correctness: functions behave as coded, schemas validate expected payloads, persistence works, and scoring is stable under tested conditions. It does not yet support a claim that the ranking predicts hiring success or that one parameter set is objectively better without a collected, adjudicated, held-out benchmark.

Recommended work is in [12 — Future Improvements](./12_FUTURE_IMPROVEMENTS.md).
