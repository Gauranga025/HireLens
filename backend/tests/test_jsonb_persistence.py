"""Regression tests for JSONB serialization at the persistence boundary.

These tests use a real PostgreSQL connection but wrap every write in a
transaction that is rolled back, so they never delete or modify existing data.
"""
import json
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.repositories.job_repository import JobRepository, get_structured_requirements
from app.repositories.resume_repository import ResumeRepository
from app.repositories.screening_repository import ScreeningRepository
from app.schemas.job import (
    ExperienceRequirement,
    ExperienceType,
    FundamentalRequirement,
    MatchMode,
    RequirementGroup,
    RequirementType,
    SkillRequirement,
    StructuredRequirement,
)
from app.utils.serialization import serialize_for_jsonb


def _structured_requirements():
    """Build requirements containing enums, nested models and plain dicts."""
    group = RequirementGroup(
        group_name="Programming Languages",
        match_mode=MatchMode.ANY,
        skills=[
            SkillRequirement(skill="Python", original_text="Python or Java"),
            SkillRequirement(skill="Java", original_text="Python or Java"),
        ],
        original_text="Python or Java",
    )
    experience = ExperienceRequirement(
        min_years=2,
        max_years=5,
        experience_type=ExperienceType.INTERNSHIP,
        original_text="2-5 years internship experience",
    )
    fundamental = FundamentalRequirement(
        skill="Data Structures",
        normalized_skill="data structures",
        original_text="Strong data structures fundamentals",
    )
    return [
        StructuredRequirement(
            requirement_type=RequirementType.REQUIRED_GROUP,
            data=group.model_dump(mode="json"),
            original_text="Python or Java",
        ),
        StructuredRequirement(
            requirement_type=RequirementType.EXPERIENCE,
            data=experience.model_dump(mode="json"),
            original_text="2-5 years internship experience",
        ),
        StructuredRequirement(
            requirement_type=RequirementType.FUNDAMENTAL,
            data=fundamental.model_dump(mode="json"),
            original_text=fundamental.original_text,
        ),
        StructuredRequirement(
            requirement_type=RequirementType.REQUIRED,
            data={"skill": "FastAPI", "normalized_skill": "fastapi"},
            original_text="FastAPI",
        ),
    ]


def test_serialize_for_jsonb_recursively_converts_models_and_enums():
    payload = serialize_for_jsonb(_structured_requirements())

    # Must be JSON-serializable without a custom default encoder.
    json.dumps(payload)

    assert isinstance(payload, list)
    assert payload[0]["requirement_type"] == "REQUIRED_GROUP"
    group_data = payload[0]["data"]
    assert isinstance(group_data, dict)
    assert group_data["match_mode"] == "ANY"
    assert group_data["skills"][0]["skill"] == "Python"
    assert payload[1]["data"]["experience_type"] == "internship"
    assert payload[2]["requirement_type"] == "FUNDAMENTAL"
    assert payload[3]["data"]["skill"] == "FastAPI"


def test_serialize_for_jsonb_handles_nested_models_inside_dicts():
    """Models nested below an arbitrary dict key are still converted."""
    group = RequirementGroup(
        group_name="Databases",
        match_mode=MatchMode.ANY,
        skills=[SkillRequirement(skill="PostgreSQL", original_text="PostgreSQL")],
        original_text="PostgreSQL",
    )
    experience = ExperienceRequirement(
        min_years=1,
        experience_type=ExperienceType.PROFESSIONAL,
        original_text="1 year",
    )

    payload = serialize_for_jsonb(
        {
            "group": group,
            "experience": experience,
            "requirements": [group],
        }
    )
    json.dumps(payload)

    assert payload["group"]["match_mode"] == "ANY"
    assert payload["group"]["skills"][0]["skill"] == "PostgreSQL"
    assert payload["experience"]["experience_type"] == "professional"
    assert payload["requirements"][0]["group_name"] == "Databases"


@pytest.mark.asyncio
async def test_job_repository_persists_nested_structured_requirements(db_session):
    generator = _structured_requirements()
    job = await JobRepository().create(
        db=db_session,
        title="Backend Engineer",
        description="Python or Java. 2-5 years internship experience.",
        required_skills=["Python", "Java", "FastAPI"],
        preferred_skills=["Docker"],
        qualifications=["BSc Computer Science"],
        experience_required="2-5 years",
        structured_requirements=generator,
        analysis_data={
            "title": "Backend Engineer",
            "structured_requirements": generator,
            "required_skills": ["Python", "Java", "FastAPI"],
            "preferred_skills": ["Docker"],
        },
    )

    # Verify the database really stored JSON (not Python objects or strings).
    result = await db_session.execute(
        text(
            """
            SELECT
                jsonb_typeof(structured_requirements) AS root_type,
                structured_requirements->0->>'requirement_type' AS first_type,
                structured_requirements->0->'data'->>'match_mode' AS match_mode,
                structured_requirements->1->'data'->>'experience_type' AS experience_type,
                structured_requirements->2->>'requirement_type' AS fundamental_type,
                structured_requirements->3->'data'->>'skill' AS individual_skill,
                jsonb_typeof(analysis_data->'structured_requirements') AS analysis_type
            FROM jobs
            WHERE id = :job_id
            """
        ),
        {"job_id": job.id},
    )
    row = result.one()

    assert row.root_type == "array"
    assert row.first_type == "REQUIRED_GROUP"
    assert row.match_mode == "ANY"
    assert row.experience_type == "internship"
    assert row.fundamental_type == "FUNDAMENTAL"
    assert row.individual_skill == "FastAPI"
    assert row.analysis_type == "array"

    # Reload through the ORM; values must be usable Python primitives.
    loaded = await JobRepository().get_by_id(db_session, job.id)
    assert loaded is not None
    assert loaded.structured_requirements[0]["requirement_type"] == "REQUIRED_GROUP"
    assert loaded.structured_requirements[0]["data"]["match_mode"] == "ANY"
    assert loaded.structured_requirements[0]["data"]["skills"][1]["skill"] == "Java"
    assert loaded.analysis_data["structured_requirements"][1]["data"][
        "experience_type"
    ] == "internship"


@pytest.mark.asyncio
async def test_job_repository_persists_empty_requirements_as_empty_lists(db_session):
    job = await JobRepository().create(
        db=db_session,
        title="Empty Requirements",
        description="No explicit requirements.",
        required_skills=[],
        preferred_skills=[],
        qualifications=[],
        experience_required="Not specified",
        structured_requirements=[],
        analysis_data={"structured_requirements": []},
    )

    result = await db_session.execute(
        text(
            """
            SELECT
                jsonb_typeof(structured_requirements) AS structured_type,
                structured_requirements AS structured_value,
                jsonb_typeof(required_skills) AS skills_type,
                required_skills AS skills_value
            FROM jobs
            WHERE id = :job_id
            """
        ),
        {"job_id": job.id},
    )
    row = result.one()

    assert row.structured_type == "array"
    assert row.structured_value == []
    assert row.skills_type == "array"
    assert row.skills_value == []


@pytest.mark.asyncio
async def test_legacy_job_falls_back_to_analysis_data_requirements(db_session):
    """A job row with an empty dedicated column still exposes legacy analysis data."""
    job = await JobRepository().create(
        db=db_session,
        title="Legacy Job",
        description="Legacy description",
        required_skills=["Python"],
        preferred_skills=[],
        qualifications=[],
        experience_required="Not specified",
        structured_requirements=[],
        analysis_data={
            "structured_requirements": [
                {
                    "requirement_type": "REQUIRED",
                    "data": {"skill": "Python"},
                    "original_text": "Python",
                }
            ]
        },
    )

    requirements = get_structured_requirements(job)
    assert requirements[0]["requirement_type"] == "REQUIRED"
    assert requirements[0]["data"]["skill"] == "Python"


@pytest.mark.asyncio
async def test_screening_upsert_is_idempotent_for_job_resume_pair(db_session):
    job = await JobRepository().create(
        db=db_session,
        title="Upsert Job",
        description="Python",
        required_skills=["Python"],
        preferred_skills=[],
        qualifications=[],
        experience_required="Not specified",
    )
    resume = await ResumeRepository().create(
        db=db_session,
        original_filename="candidate.pdf",
        file_type="pdf",
        candidate_name="Candidate",
        email="candidate@example.com",
        phone=None,
        candidate_info={"name": "Candidate"},
        extracted_text="Python developer",
        skills=["Python"],
        storage_key=f"uploads/{uuid4()}.pdf",
    )

    repository = ScreeningRepository()
    first = await repository.upsert(
        db=db_session,
        job_id=job.id,
        resume_id=resume.id,
        overall_score=10.0,
        tfidf_score=10.0,
        semantic_score=None,
        skill_match_score=10.0,
        matched_skills=["Python"],
        missing_skills=[],
        additional_skills=[],
        explanation="first",
        screening_status="completed",
    )
    second = await repository.upsert(
        db=db_session,
        job_id=job.id,
        resume_id=resume.id,
        overall_score=90.0,
        tfidf_score=90.0,
        semantic_score=None,
        skill_match_score=90.0,
        matched_skills=["Python"],
        missing_skills=[],
        additional_skills=[],
        explanation="second",
        screening_status="completed",
    )

    assert first.id == second.id

    result = await db_session.execute(
        text(
            "SELECT count(*) AS total, max(overall_score) AS score "
            "FROM screening_results WHERE job_id = :job_id AND resume_id = :resume_id"
        ),
        {"job_id": job.id, "resume_id": resume.id},
    )
    row = result.one()
    assert row.total == 1
    assert row.score == 90.0
