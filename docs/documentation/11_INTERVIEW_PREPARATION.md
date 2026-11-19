# 11 — Interview Preparation

This chapter contains source-backed talking points. Each answer should be framed as a description of the current implementation, not as a claim about unimplemented capabilities.

## Two-minute project summary

“HireLens is a FastAPI and Next.js application that screens resumes against a job description. A recruiter analyzes a JD, uploads PDF or DOCX resumes, and receives a ranked table with explanations.

The backend parses the JD into flat skill lists and structured requirements, uploads resumes to local storage, extracts text with PyMuPDF or python-docx, and parses candidate details with rule-based helpers. During evaluation, `CandidateEvaluationService` calls `ScoringService.compute_match`. The score combines required skill coverage, preferred skill coverage, pinned MiniLM semantic similarity, and evidence strength using 35/15/30/20 weights. If semantic scoring is unavailable, the remaining weights are renormalized and the response records the fallback.

The frontend is a single Next.js client page with local React state. It calls the backend through a typed `ApiClient`, shows ranked candidates, expands per-candidate evidence, and downloads CSV reports. PostgreSQL stores jobs, resumes, and screening results; generated reports are in-memory only.”

## Five-minute technical walkthrough

“There are four main API workflows. `POST /api/v1/jobs/analyze` calls `analyze_job_description`, which uses a curated skills database and section keywords to produce required, preferred, optional, alternative, experience, and fundamental requirements. `POST /api/v1/resumes/upload` validates and stores each file, extracts text, parses candidate fields, adds technical and soft skills, and enriches experience and projects with classification and temporal metadata.

`POST /api/v1/matching/evaluate` loads the stored job and resumes, deduplicates resume IDs, builds a `CandidateEvaluationContext` for each candidate, and calls `CandidateEvaluationService.evaluate_candidate`. Structured requirements are authoritative over flat skill lists. `match_structured_requirements` creates individual, ANY, and ALL units and gives hierarchy credit to exact and related skills; the API sets the related-skill threshold to 0.5.

The semantic path builds weighted requirement units and section-aware tokenizer-verified resume chunks. MiniLM embeddings are cached, cosine similarity is clipped to 0–1, chunks below 0.25 are discarded, and the top three are ranked with 1.00/0.50/0.25 weights. Evidence scoring only uses required units and distinguishes measurable or implemented evidence from a bare skills-list claim.

The final score is `0.35 required + 0.15 preferred + 0.30 semantic + 0.20 evidence`, clamped to 0–100. `ScoringService` generates a natural-language explanation, `EvidenceMappingService` adds requirement evaluations, strengths, and gaps, and the route upserts a screening result before sorting candidates by score. Reports reuse the same pipeline but are stored in an in-memory repository.”

## Likely questions and precise answers

### 1. What is the final scoring formula?

`0.35 × required_coverage + 0.15 × preferred_coverage + 0.30 × semantic_score + 0.20 × evidence_score`, clamped to 0–100. All four inputs are already on a 0–100 scale. Source: `backend/app/services/scoring_service.py::ScoringService._compute_overall_score`.

### 2. Which component owns the official score?

`ScoringService.compute_match`. `CandidateEvaluationService.evaluate_candidate` orchestrates it, and both `/matching/evaluate` and `/reports/generate` use it. `CandidateEvaluationService` adds temporal metadata and overwrites the visible algorithm version with `3.0.0-unified-evaluation`.

### 3. Is TF-IDF part of the live score?

No. TF-IDF has a default weight of `0.0`. `ScoringService` imports `tfidf_similarity` from `matching_service.py`, but it is dormant in live responses.

### 4. What is the difference between `ScoringService` and the legacy `matching_service.py::compute_match`?

The legacy function uses `0.3 TF-IDF + 0.4 semantic + 0.3 skill`, or `0.5 TF-IDF + 0.5 skill` without semantic. It is not called by live routes. The live pipeline uses the 35/15/30/20 formula and structured requirement units.

### 5. How are required and preferred skills identified?

`job_analysis_service.py::analyze_job_description` tracks section keywords such as `must have`, `required`, `preferred`, and `nice to have`. It stores both flat skill lists and structured requirements. Structured requirements are authoritative at evaluation time.

### 6. How does an alternative requirement such as “Python, Java, or JavaScript” work?

`parse_alternative_group` emits a `REQUIRED_GROUP` with `match_mode = ANY`. At scoring time, the group uses the maximum member credit, so the candidate needs at least one qualifying skill. `ALL` is supported by the schema and scorer and uses the mean member credit, but current JD analysis does not produce `ALL` groups.

### 7. How are aliases and related skills handled?

`normalize_skill_name` maps aliases such as `js → javascript` and `postgres → postgresql`. `SkillHierarchyRegistry.get_match_credit` gives `1.0` for aliases/equivalents, `0.5` for parent-child or related skills, and `0.0` for distinct or unknown relationships. The live routes use a related-skill threshold of `0.5`.

### 8. What model is used for semantic matching?

`sentence-transformers/all-MiniLM-L6-v2`, pinned by default to revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`. `SEMANTIC_MODEL_NAME` and `SEMANTIC_MODEL_REVISION` can override it.

### 9. Is the whole resume embedded as one document?

No. `semantic_input_service.py::build_resume_chunks` creates section-aware, tokenizer-verified chunks, skips personal information, deduplicates, and retains at most 64 chunks. Retrieval uses section `beta` weights and keeps the top three relevant chunks.

### 10. How does evidence scoring reduce keyword stuffing?

`EvidenceExtractionService` classifies where and how a skill appears. A skills-list mention is basic strength with a claimed multiplier of 0.8; measurable project or experience evidence can reach 1.2 before the score is capped. The separate keyword-stuffing penalty exists but is disabled by default.

### 11. Does years of experience directly add points?

No. Experience is extracted, classified, temporally annotated, and used as context for evidence and explanations. There is no dedicated experience weight, seniority multiplier, or recency score in the final formula.

### 12. What happens when the semantic model cannot load?

The semantic status becomes `model_unavailable` or `inference_failed`, semantic weight becomes zero, and the remaining weights are divided by 0.70. Effective weights become 0.5000 required, about 0.2143 preferred, and about 0.2857 evidence. `fallback_used` is true for these cases.

### 13. How are candidates ranked?

`backend/app/api/routes/matching.py::evaluate_matching` sorts results with `results.sort(key=lambda x: x.match_result.overall_score, reverse=True)`. The frontend displays the array order as rank and does no client-side sorting.

### 14. Where are reports stored?

In `backend/app/core/repository.py::report_repository`, an in-memory dictionary. Reports are not stored in PostgreSQL and disappear when the backend process restarts.

### 15. Is the application deployed with containers?

`docker-compose.yml` defines only PostgreSQL 16 with a named volume. It does not define backend or frontend services.

### 16. Is there authentication?

No. There are no user accounts, roles, or auth dependencies in the API.

### 17. What are the major limitations to acknowledge?

- No human-labelled ranking benchmark is wired into the live pipeline.
- PDF parsing is heuristic and low-text PDFs are only flagged; there is no OCR.
- Experience and qualifications do not directly affect the score.
- Reports and caches are process-local.
- Upload storage is local filesystem based.
- There is no authentication, multi-worker report sharing, or standardized error envelope.

## Strong engineering decisions to highlight

1. **One canonical scorer.** Matching and reports both call `CandidateEvaluationService` → `ScoringService.compute_match`, so displayed and exported scores use the same logic.
2. **Structured requirement units.** Individual, ANY, and ALL units preserve alternative semantics and avoid double-counting.
3. **Explicit fallback.** Semantic failures are represented in `scoring_strategy` instead of silently changing the score meaning.
4. **Evidence-aware scoring.** The system differentiates demonstrated and measurable evidence from a bare skills list.
5. **Separation of layers.** Routes, services, repositories, models, and schemas have distinct responsibilities.

## Honest limitations to volunteer

- The system is decision support, not a validated predictor of job performance.
- Heuristic parsers can be sensitive to resume formatting.
- The pinned MiniLM model improves reproducibility but still requires a compatible local runtime.
- There is no OCR, vector database, fine-tuning, or LLM component.
- In-memory report storage and local upload storage are unsuitable for unrestricted multi-instance production without additional work.

## Code references to keep handy

| Topic | Reference |
|---|---|
| App setup | `backend/app/main.py` |
| Endpoint contracts | `backend/app/api/routes/` |
| Scoring formula | `backend/app/services/scoring_service.py::ScoringService._compute_overall_score` |
| Orchestration | `backend/app/services/candidate_evaluation_service.py::CandidateEvaluationService.evaluate_candidate` |
| JD analysis | `backend/app/services/job_analysis_service.py::analyze_job_description` |
| Skill matching | `backend/app/services/skill_service.py::match_structured_requirements` |
| Semantic inputs | `backend/app/services/semantic_input_service.py::build_semantic_inputs` |
| Semantic score | `backend/app/services/requirement_semantic_service.py::RequirementSemanticService.score` |
| Evidence | `backend/app/services/evidence_extraction_service.py`, `evidence_mapping_service.py` |
| DB models | `backend/app/models/` |
| Migrations | `backend/alembic/versions/` |
| Frontend workflow | `frontend/app/page.tsx` |
| API client | `frontend/lib/api-client.ts` |
| Configuration | `backend/app/core/config.py`, `.env.example`, `frontend/.env.example` |
