import pytest
from pydantic import ValidationError

from app.schemas.common import HealthResponse, ErrorResponse
from app.schemas.resume import (
    EducationEntry,
    ExperienceEntry,
    ExtractedResumeInfo,
    DocumentExtractionResult,
)
from app.schemas.job import AnalyzedJobDescription
from app.schemas.matching import MatchResult


def test_health_response_schema() -> None:
    """Test HealthResponse schema validation."""
    response = HealthResponse(
        status="healthy",
        version="1.0.0",
        app_name="Test App",
    )
    assert response.status == "healthy"
    assert response.version == "1.0.0"
    assert response.app_name == "Test App"


def test_error_response_schema() -> None:
    """Test ErrorResponse schema validation."""
    error = ErrorResponse(
        error="ValidationError",
        message="Invalid input",
        details={"field": "email"},
    )
    assert error.error == "ValidationError"
    assert error.message == "Invalid input"
    assert error.details == {"field": "email"}


def test_education_entry_schema() -> None:
    """Test EducationEntry schema validation."""
    entry = EducationEntry(
        degree="B.Tech in Computer Science",
        institution="IIT Delhi",
        year="2016 - 2020",
    )
    assert entry.degree == "B.Tech in Computer Science"
    assert entry.institution == "IIT Delhi"
    assert entry.year == "2016 - 2020"


def test_experience_entry_schema() -> None:
    """Test ExperienceEntry schema validation."""
    entry = ExperienceEntry(
        title="Software Developer",
        company="Infosys",
        duration="June 2020 - December 2022",
    )
    assert entry.title == "Software Developer"
    assert entry.company == "Infosys"
    assert entry.duration == "June 2020 - December 2022"


def test_extracted_resume_info_schema() -> None:
    """Test ExtractedResumeInfo schema validation."""
    info = ExtractedResumeInfo(
        name="Arjun Sharma",
        email="arjun@example.com",
        phone="+91-9876543210",
        education=[
            EducationEntry(
                degree="B.Tech",
                institution="IIT Delhi",
                year="2016-2020",
            )
        ],
        experience=[
            ExperienceEntry(
                title="Software Developer",
                company="Infosys",
                duration="2020-2022",
            )
        ],
        certifications=["AWS Certified"],
        projects=["E-Commerce Platform"],
        skills=["Python", "Django"],
    )
    assert info.name == "Arjun Sharma"
    assert info.email == "arjun@example.com"
    assert len(info.education) == 1
    assert len(info.experience) == 1
    assert len(info.certifications) == 1
    assert len(info.projects) == 1
    assert len(info.skills) == 2


def test_extracted_resume_info_defaults() -> None:
    """Test ExtractedResumeInfo with default empty lists."""
    info = ExtractedResumeInfo(
        name="Test User",
        email="test@example.com",
        phone="1234567890",
    )
    assert info.education == []
    assert info.experience == []
    assert info.certifications == []
    assert info.projects == []
    assert info.skills == []


def test_document_extraction_result_schema() -> None:
    """Test DocumentExtractionResult schema validation."""
    result = DocumentExtractionResult(
        text="Sample resume text",
        source_format="pdf",
        num_pages=2,
        is_scanned=False,
        metadata={"author": "Test"},
    )
    assert result.text == "Sample resume text"
    assert result.source_format == "pdf"
    assert result.num_pages == 2
    assert result.is_scanned is False
    assert result.metadata == {"author": "Test"}


def test_analyzed_job_description_schema() -> None:
    """Test AnalyzedJobDescription schema validation."""
    job = AnalyzedJobDescription(
        title="Software Engineer",
        required_skills=["Python", "Django"],
        preferred_skills=["React"],
        qualifications=["B.Tech in CS"],
        experience_required="3+ years",
        raw_text="Job description text",
    )
    assert job.title == "Software Engineer"
    assert len(job.required_skills) == 2
    assert len(job.preferred_skills) == 1
    assert job.experience_required == "3+ years"


def test_match_result_schema() -> None:
    """Test MatchResult schema validation."""
    match = MatchResult(
        overall_score=75.5,
        tfidf_score=60.0,
        semantic_score=80.0,
        skill_match_score=85.0,
        matched_skills=["Python", "Django"],
        missing_skills=["Kubernetes"],
        additional_skills=["React"],
        explanation="Candidate shows strong alignment",
    )
    assert match.overall_score == 75.5
    assert match.tfidf_score == 60.0
    assert match.semantic_score == 80.0
    assert match.skill_match_score == 85.0
    assert len(match.matched_skills) == 2
    assert len(match.missing_skills) == 1


def test_match_result_without_semantic() -> None:
    """Test MatchResult without semantic score."""
    match = MatchResult(
        overall_score=65.0,
        tfidf_score=60.0,
        semantic_score=None,
        skill_match_score=70.0,
        matched_skills=["Python"],
        missing_skills=["Docker"],
        additional_skills=[],
        explanation="Match without semantic analysis",
    )
    assert match.semantic_score is None


def test_schema_validation_error() -> None:
    """Test that required fields raise ValidationError."""
    with pytest.raises(ValidationError):
        HealthResponse(status="healthy", version="1.0.0")
