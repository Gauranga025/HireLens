"""Regression tests for Phase 10.2 group semantics and evidence consistency."""
from app.services.scoring_service import ScoringService
from app.services.skill_service import match_structured_requirements


def _group_requirement(match_mode, skills):
    return {
        "requirement_type": "REQUIRED_GROUP",
        "data": {
            "group_name": "Cloud",
            "match_mode": match_mode,
            "skills": [{"skill": skill, "normalized_skill": skill.lower()} for skill in skills],
        },
        "original_text": "Cloud skills",
    }


def test_satisfied_any_group_does_not_report_unmatched_alternative_as_gap():
    service = ScoringService()
    result = service.compute_match(
        resume_text=(
            "Skills: Python, Docker\n"
            "Experience: Implemented Docker deployment pipelines for production."
        ),
        job_text="Python required. Proficiency in at least one of Docker, Kubernetes, or AWS.",
        resume_skills=["Python", "Docker"],
        required_skills=["Python", "Docker", "Kubernetes", "AWS"],
        preferred_skills=[],
        use_semantic=False,
        structured_requirements=[
            {
                "requirement_type": "REQUIRED",
                "data": {"skill": "Python", "normalized_skill": "python"},
                "original_text": "Python required",
            },
            _group_requirement("ANY", ["Docker", "Kubernetes", "AWS"]),
        ],
    )

    group = result["group_evaluation"][0]
    assert group["is_satisfied"] is True
    assert result["required_skill_coverage"] == 100.0

    # Unmatched alternatives inside a satisfied ANY group are not gaps.
    assert "Kubernetes" not in result["missing_skills"]
    assert "AWS" not in result["missing_skills"]
    assert result["requirement_evaluations"]["Kubernetes"]["satisfied_by_group"] is True
    assert "Kubernetes" not in result["evidence_summary"]["unsupported_required_skills"]
    assert not any("Kubernetes" in gap for gap in result["gaps"])

    # Directly matched group members keep their evidence.
    assert "Docker" in result["evidence_summary"]["demonstrated_skills"]
    assert any("Docker" in strength for strength in result["strengths"])


def test_unsatisfied_all_group_reports_missing_alternative_as_gap():
    service = ScoringService()
    result = service.compute_match(
        resume_text="Skills: Python, Docker\nExperience: Implemented Docker pipelines.",
        job_text="Python, Docker and Kubernetes required.",
        resume_skills=["Python", "Docker"],
        required_skills=["Python", "Docker", "Kubernetes"],
        preferred_skills=[],
        use_semantic=False,
        structured_requirements=[
            {
                "requirement_type": "REQUIRED",
                "data": {"skill": "Python", "normalized_skill": "python"},
                "original_text": "Python",
            },
            _group_requirement("ALL", ["Docker", "Kubernetes"]),
        ],
    )

    group = result["group_evaluation"][0]
    assert group["is_satisfied"] is False
    assert "Kubernetes" in result["missing_skills"]
    assert "Kubernetes" in result["evidence_summary"]["unsupported_required_skills"]
    assert any("Kubernetes" in gap for gap in result["gaps"])
    assert result["requirement_evaluations"]["Kubernetes"]["satisfied_by_group"] is False


def test_preferred_match_does_not_inflate_required_coverage():
    result = match_structured_requirements(
        candidate_skills=["Docker"],
        structured_requirements=[
            {
                "requirement_type": "REQUIRED",
                "data": {"skill": "Python", "normalized_skill": "python"},
                "original_text": "Python",
            },
            {
                "requirement_type": "PREFERRED",
                "data": {"skill": "Docker", "normalized_skill": "docker"},
                "original_text": "Docker",
            },
        ],
    )

    assert result["match_percentage"] == 0.0
    assert "Docker" in result["matched"]
    assert "Python" in result["missing"]


def test_duplicate_individual_requirements_are_counted_once():
    result = match_structured_requirements(
        candidate_skills=["Python"],
        structured_requirements=[
            {
                "requirement_type": "REQUIRED",
                "data": {"skill": "Python", "normalized_skill": "python"},
                "original_text": "Python",
            },
            {
                "requirement_type": "REQUIRED",
                "data": {"skill": "Python", "normalized_skill": "python"},
                "original_text": "Python again",
            },
            {
                "requirement_type": "REQUIRED",
                "data": {"skill": "Java", "normalized_skill": "java"},
                "original_text": "Java",
            },
        ],
    )

    assert result["match_percentage"] == 50.0
    assert result["missing"] == ["Java"]
