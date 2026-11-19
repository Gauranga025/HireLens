# HireLens Documentation Suite

This directory is the source-accurate documentation set for **HireLens**, an AI-assisted resume screening application. It describes the system that is actually implemented in this repository, with file paths, class names, function names, and explicit separation between current behavior and proposed work.

## Source of truth

Application source is authoritative. When a README, design note, or older document disagrees with the code, this suite follows the code.

Primary authoritative areas:

- `backend/app/main.py` — FastAPI application setup and route registration.
- `backend/app/api/routes/` — live HTTP endpoints.
- `backend/app/services/` — parsing, matching, scoring, reporting, and enrichment logic.
- `backend/app/models/`, `backend/app/repositories/`, and `backend/alembic/versions/` — persistence schema and migrations.
- `frontend/app/`, `frontend/components/`, and `frontend/lib/` — user workflow, UI, and API client.
- `backend/app/core/config.py`, `.env.example`, `frontend/.env.example`, and `docker-compose.yml` — configuration and local runtime.

`docs/BACKEND_EXPLANATION.md` is an existing recruiter-friendly algorithm write-up and was used as a validated reference for the matching sections. It is not part of this numbered suite.

## Reading paths

### Recruiter or product reviewer

1. [00 — Project Overview](./00_PROJECT_OVERVIEW.md)
2. [01 — Recruiter Workflow](./01_RECRUITER_WORKFLOW.md)
3. [05 — AI and NLP Matching](./05_AI_NLP_MATCHING.md)
4. [11 — Interview Preparation](./11_INTERVIEW_PREPARATION.md)

### Developer onboarding

1. [00 — Project Overview](./00_PROJECT_OVERVIEW.md)
2. [02 — System Architecture](./02_SYSTEM_ARCHITECTURE.md)
3. [03 — Backend Internals](./03_BACKEND_INTERNALS.md)
4. [04 — Frontend Internals](./04_FRONTEND_INTERNALS.md)
5. [06 — Database Design](./06_DATABASE_DESIGN.md)
6. [07 — API Reference](./07_API_REFERENCE.md)
7. [09 — Local Setup](./09_LOCAL_SETUP.md)

### Evaluation, deployment, and roadmap

1. [08 — Testing and Quality](./08_TESTING_QUALITY.md)
2. [10 — Deployment and Operations](./10_DEPLOYMENT_OPERATIONS.md)
3. [12 — Future Improvements](./12_FUTURE_IMPROVEMENTS.md)

## Document index

| Document | Covers |
|---|---|
| [00 — Project Overview](./00_PROJECT_OVERVIEW.md) | Product purpose, implemented scope, stack, source map, and non-goals. |
| [01 — Recruiter Workflow](./01_RECRUITER_WORKFLOW.md) | The user journey from job description to ranked candidates and exported reports. |
| [02 — System Architecture](./02_SYSTEM_ARCHITECTURE.md) | Components, runtime boundaries, request flow, and design characteristics. |
| [03 — Backend Internals](./03_BACKEND_INTERNALS.md) | FastAPI structure, JD processing, resume upload, evaluation orchestration, and reporting. |
| [04 — Frontend Internals](./04_FRONTEND_INTERNALS.md) | Next.js app, components, state transitions, API client, and validation. |
| [05 — AI and NLP Matching](./05_AI_NLP_MATCHING.md) | Structured requirements, skills, semantics, evidence, scoring, and fallback behavior. |
| [06 — Database Design](./06_DATABASE_DESIGN.md) | Tables, columns, relationships, migrations, repositories, and in-memory state. |
| [07 — API Reference](./07_API_REFERENCE.md) | Endpoints, parameters, response concepts, errors, and request lifecycle. |
| [08 — Testing and Quality](./08_TESTING_QUALITY.md) | Test layout, commands, coverage areas, evaluation utilities, and known limits. |
| [09 — Local Setup](./09_LOCAL_SETUP.md) | Prerequisites, environment variables, database setup, and run instructions. |
| [10 — Deployment and Operations](./10_DEPLOYMENT_OPERATIONS.md) | Current deployment artifacts, operational concerns, and documented gaps. |
| [11 — Interview Preparation](./11_INTERVIEW_PREPARATION.md) | Source-backed talking points, likely questions, and precise answers. |
| [12 — Future Improvements](./12_FUTURE_IMPROVEMENTS.md) | Clearly labelled proposals, not implemented features. |

## Conventions

- **Implemented** describes behavior that can be traced to current source.
- **Not implemented** or **proposed** describes something that does not exist in the current codebase.
- Code identifiers use the form `path/to/file.py::symbol_name`.
- Environment variables are written exactly as the application reads them.
- Mermaid diagrams depict the implemented flow unless explicitly labelled as proposed.

This suite is documentation-only: no application source was changed to produce it.
