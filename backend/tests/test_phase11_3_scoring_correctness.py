"""Focused regressions for Phase 11.3 scoring correctness findings."""
import pytest

from app.schemas.matching import ScoringStrategy
from app.services.evidence_extraction_service import (
    DemonstrationLevel,
    EvidenceStrength,
    EvidenceType,
    SkillEvidence,
)
from app.services.job_analysis_service import analyze_job_description
from app.services.scoring_service import ScoringConfig, ScoringService
from app.services.section_detection_service import SectionType
from app.services.skill_service import (
    extract_skills,
    match_skills_to_requirements,
    match_structured_requirements,
)


class FakeSemanticService:
    """Deterministic semantic test double; never loads the real model."""

    def __init__(self, available=False, score=None, error=None, raises=False):
        self.available = available
        self.score = score
        self.error = error
        self.raises = raises

    def is_available(self):
        return self.available

    def get_error_info(self):
        return self.error

    def compute_similarity(self, text1, text2):
        if self.raises:
            raise RuntimeError("simulated inference failure")
        return self.score


def _service(semantic=None, evidence=None, config=None):
    semantic = semantic or FakeSemanticService(available=False)
    service = ScoringService(config=config, semantic_service=semantic)
    if evidence is not None:
        service.evidence_service.extract_skill_evidence = (
            lambda *args, **kwargs: evidence
        )
    return service


def _evidence(
    skill,
    strength=EvidenceStrength.MODERATE,
    level=DemonstrationLevel.MENTIONED,
):
    return SkillEvidence(
        skill=skill,
        section=SectionType.EXPERIENCE,
        evidence_type=EvidenceType.DEMONSTRATED_IN_EXPERIENCE,
        snippet=f"Implemented {skill} in production",
        strength=strength,
        start_offset=0,
        end_offset=len(skill),
        demonstration_level=level,
    )


def _requirement(skill, requirement_type="REQUIRED"):
    return {
        "requirement_type": requirement_type,
        "data": {"skill": skill, "normalized_skill": skill.lower()},
        "original_text": skill,
    }


def _group(mode, skills):
    return {
        "requirement_type": "REQUIRED_GROUP",
        "data": {
            "group_name": "Alternatives",
            "match_mode": mode,
            "skills": [
                {"skill": skill, "normalized_skill": skill.lower()}
                for skill in skills
            ],
        },
        "original_text": ", ".join(skills),
    }


# --- F-01: required-only evidence -------------------------------------------------

def test_preferred_evidence_does_not_change_required_evidence_score():
    requirements = [_requirement("Python")]
    base_evidence = {"Python": [_evidence("Python")]}

    base = _service(evidence=base_evidence).compute_match(
        resume_text="Used Python",
        job_text="Python required",
        resume_skills=["Python"],
        required_skills=["Python"],
        preferred_skills=[],
        use_semantic=False,
        structured_requirements=requirements,
    )

    with_preferred = _service(
        evidence={
            **base_evidence,
            "Docker": [
                _evidence(
                    "Docker",
                    EvidenceStrength.STRONG,
                    DemonstrationLevel.MEASURABLE,
                )
            ],
        }
    ).compute_match(
        resume_text="Used Python and Docker",
        job_text="Python required; Docker preferred",
        resume_skills=["Python", "Docker"],
        required_skills=["Python"],
        preferred_skills=["Docker"],
        use_semantic=False,
        structured_requirements=requirements + [_requirement("Docker", "PREFERRED")],
    )

    without_preferred_evidence = _service(evidence=base_evidence).compute_match(
        resume_text="Used Python",
        job_text="Python required; Docker preferred",
        resume_skills=["Python"],
        required_skills=["Python"],
        preferred_skills=["Docker"],
        use_semantic=False,
        structured_requirements=requirements + [_requirement("Docker", "PREFERRED")],
    )

    assert base["evidence_score"] == pytest.approx(75.0)
    assert with_preferred["evidence_score"] == pytest.approx(75.0)
    assert without_preferred_evidence["evidence_score"] == pytest.approx(75.0)
    assert with_preferred["required_skill_coverage"] == pytest.approx(100.0)
    assert with_preferred["preferred_skill_coverage"] == pytest.approx(100.0)
    assert without_preferred_evidence["preferred_skill_coverage"] == pytest.approx(0.0)


def test_satisfied_any_group_contributes_at_most_one_evidence_representative():
    evidence = {
        "Python": [
            _evidence(
                "Python",
                EvidenceStrength.WEAK,
                DemonstrationLevel.MENTIONED,
            )
        ],
        "Docker": [_evidence("Docker")],
        "Kubernetes": [_evidence("Kubernetes")],
        "AWS": [_evidence("AWS")],
    }
    result = _service(evidence=evidence).compute_match(
        resume_text="Python, Docker, Kubernetes, AWS",
        job_text="Python and one of Docker/Kubernetes/AWS",
        resume_skills=["Python", "Docker", "Kubernetes", "AWS"],
        required_skills=["Python"],
        preferred_skills=[],
        use_semantic=False,
        structured_requirements=[
            _requirement("Python"),
            _group("ANY", ["Docker", "Kubernetes", "AWS"]),
        ],
    )

    # (weak individual 25 + one group representative 75) / 2 eligible units.
    assert result["evidence_score"] == pytest.approx(50.0)
    assert result["required_skill_coverage"] == pytest.approx(100.0)


# --- F-02: actual hierarchy credit ------------------------------------------------

def test_hierarchy_credit_is_fractional_not_binary():
    related = match_skills_to_requirements(
        ["MySQL"], ["PostgreSQL"], related_skill_credit_threshold=0.5
    )
    alias = match_skills_to_requirements(
        ["RESTful services"], ["REST API"], related_skill_credit_threshold=0.5
    )
    distinct = match_skills_to_requirements(
        ["JavaScript"], ["Java"], related_skill_credit_threshold=0.5
    )

    assert related["match_percentage"] == pytest.approx(50.0)
    assert related["requirement_credits"]["PostgreSQL"] == pytest.approx(0.5)
    assert alias["match_percentage"] == pytest.approx(100.0)
    assert distinct["match_percentage"] == pytest.approx(0.0)
    assert distinct["requirement_credits"]["Java"] == pytest.approx(0.0)


def test_exact_related_and_distinct_matches_produce_distinct_overall_scores():
    config = ScoringConfig(related_skill_credit_threshold=0.5)

    def score(candidate):
        return _service(config=config).compute_match(
            resume_text=f"Skills: {candidate}",
            job_text="Required: PostgreSQL",
            resume_skills=[candidate],
            required_skills=["PostgreSQL"],
            preferred_skills=[],
            use_semantic=False,
        )["overall_score"]

    exact = score("PostgreSQL")
    related = score("MySQL")
    distinct = score("JavaScript")

    assert exact > related > distinct


def test_requirement_evaluation_exposes_partial_match_credit():
    config = ScoringConfig(related_skill_credit_threshold=0.5)
    result = _service(config=config).compute_match(
        resume_text="Skills: MySQL",
        job_text="Required: PostgreSQL",
        resume_skills=["MySQL"],
        required_skills=["PostgreSQL"],
        preferred_skills=[],
        use_semantic=False,
    )

    evaluation = result["requirement_evaluations"]["PostgreSQL"]
    assert evaluation["match_credit"] == pytest.approx(0.5)
    assert evaluation["match_type"] == "related"


# --- F-03/F-04: semantic status policy --------------------------------------------

def test_semantic_paths_report_explicit_status_and_weights():
    disabled = _service().compute_match(
        "Python", "Python", ["Python"], ["Python"], [], use_semantic=False
    )
    unavailable = _service(
        FakeSemanticService(
            available=False,
            error={"error_type": "model_loading_failure", "message": "stub"},
        )
    ).compute_match(
        "Python", "Python", ["Python"], ["Python"], [], use_semantic=True
    )
    inference_failed = _service(
        FakeSemanticService(available=True, score=None)
    ).compute_match(
        "Python", "Python", ["Python"], ["Python"], [], use_semantic=True
    )
    used = _service(FakeSemanticService(available=True, score=0.8)).compute_match(
        "Python", "Python", ["Python"], ["Python"], [], use_semantic=True
    )
    empty_text = _service(FakeSemanticService(available=True, score=0.8)).compute_match(
        "", "Python", [], ["Python"], [], use_semantic=True
    )

    assert disabled["scoring_strategy"]["semantic_status"] == "disabled"
    assert disabled["semantic_score"] is None
    assert disabled["scoring_strategy"]["fallback_used"] is False
    assert unavailable["scoring_strategy"]["semantic_status"] == "model_unavailable"
    assert unavailable["scoring_strategy"]["semantic_model_available"] is False
    assert unavailable["scoring_strategy"]["semantic_error"] is not None
    assert unavailable["semantic_score"] is None
    assert inference_failed["scoring_strategy"]["semantic_status"] == "inference_failed"
    assert inference_failed["scoring_strategy"]["semantic_model_available"] is True
    assert inference_failed["semantic_score"] is None
    assert used["scoring_strategy"]["semantic_status"] == "used"
    assert used["semantic_score"] == pytest.approx(80.0)
    assert empty_text["scoring_strategy"]["semantic_status"] == "empty_text"
    assert empty_text["semantic_score"] is None

    for result in (disabled, unavailable, inference_failed, empty_text):
        strategy = result["scoring_strategy"]
        assert strategy["fallback_used"] is True or result is disabled
        assert strategy["weights"]["semantic"] == 0.0
        assert sum(strategy["weights"].values()) == pytest.approx(1.0)
        assert strategy["weights"]["required_skills"] == pytest.approx(0.5)
        assert strategy["weights"]["preferred_skills"] == pytest.approx(0.15 / 0.70)
        assert strategy["weights"]["evidence"] == pytest.approx(0.20 / 0.70)

    assert used["scoring_strategy"]["weights"] == pytest.approx(
        {
            "required_skills": 0.35,
            "preferred_skills": 0.15,
            "semantic": 0.30,
            "evidence": 0.20,
            "tfidf": 0.0,
        }
    )
    assert used["scoring_strategy"]["configured_weights"] == pytest.approx(
        used["scoring_strategy"]["weights"]
    )
    assert sum(used["scoring_strategy"]["weights"].values()) == pytest.approx(1.0)


def test_semantic_exception_reports_inference_failure_and_fallback_metadata():
    result = _service(FakeSemanticService(available=True, raises=True)).compute_match(
        "Python", "Python", ["Python"], ["Python"], [], use_semantic=True
    )

    strategy = result["scoring_strategy"]
    assert strategy["semantic_status"] == "inference_failed"
    assert result["semantic_score"] is None
    assert strategy["semantic_model_available"] is True
    assert strategy["fallback_used"] is True
    assert strategy["semantic_error"] is not None
    assert strategy["semantic_error"]["error_type"] == "inference_failure"
    assert strategy["semantic_error"]["message"] == "simulated inference failure"
    assert strategy["weights"]["semantic"] == 0.0
    assert sum(strategy["weights"].values()) == pytest.approx(1.0)
    assert strategy["weights"]["required_skills"] == pytest.approx(0.5)
    assert strategy["weights"]["preferred_skills"] == pytest.approx(0.15 / 0.70)
    assert strategy["weights"]["evidence"] == pytest.approx(0.20 / 0.70)
    assert strategy["configured_weights"] == pytest.approx(
        {
            "required_skills": 0.35,
            "preferred_skills": 0.15,
            "semantic": 0.30,
            "evidence": 0.20,
            "tfidf": 0.0,
        }
    )


def test_scoring_strategy_schema_accepts_additive_semantic_metadata():
    result = _service(
        FakeSemanticService(
            available=False,
            error={"error_type": "model_loading_failure", "message": "stub"},
        )
    ).compute_match("Python", "Python", ["Python"], ["Python"], [], use_semantic=True)

    strategy = ScoringStrategy(**result["scoring_strategy"])
    assert strategy.semantic_status == "model_unavailable"
    assert strategy.semantic_model_available is False
    assert strategy.configured_weights["semantic"] == pytest.approx(0.30)


# --- F-05: punctuation-safe extraction and JD line scanning ----------------------

def test_punctuated_skill_extraction_distinguishes_similar_names():
    combined = extract_skills(
        "Skills: C++, C#, .NET, ASP.NET Core, Java, JavaScript, Node.js, Node, C, CI/CD"
    )["technical_skills"]
    assert {
        "C",
        "C++",
        "C#",
        ".NET",
        "ASP.NET Core",
        "Java",
        "JavaScript",
        "Node.js",
        "CI/CD",
    }.issubset(set(combined))

    assert extract_skills("Skills: C++")["technical_skills"] == ["C++"]
    assert extract_skills("Skills: C#")["technical_skills"] == ["C#"]
    assert extract_skills("Skills: .NET")["technical_skills"] == [".NET"]
    assert extract_skills("Skills: Node")["technical_skills"] == ["Node.js"]
    assert extract_skills("Skills: Java")["technical_skills"] == ["Java"]
    assert extract_skills("Skills: JavaScript")["technical_skills"] == ["JavaScript"]
    assert extract_skills("Node.js, Node, Node.js")["technical_skills"] == ["Node.js"]


def test_jd_line_scanning_keeps_skills_on_metadata_and_keyword_lines():
    jd = """Required Skills:
- 5+ years experience with Python and FastAPI
- Java
Preferred Skills:
- Docker
"""
    result = analyze_job_description(jd)

    assert {"Python", "FastAPI", "Java"}.issubset(set(result["required_skills"]))
    assert "Docker" in result["preferred_skills"]
    experience = [
        req for req in result["structured_requirements"]
        if req["requirement_type"] == "EXPERIENCE"
    ]
    assert experience and experience[0]["data"]["min_years"] == 5

    keyword_line = analyze_job_description("Required skills: Python\n- Java")
    assert {"Python", "Java"}.issubset(set(keyword_line["required_skills"]))


def test_punctuated_jd_and_alternative_lines_preserve_all_members():
    punctuated = analyze_job_description("Required:\n- C++\n- .NET\n- C\n- C#")
    assert punctuated["required_skills"] == ["C++", ".NET", "C", "C#"]

    alternatives = analyze_job_description(
        "Required:\n- Python, Java, or JavaScript\n- SQL"
    )
    assert {"Python", "Java", "JavaScript", "SQL"}.issubset(
        set(alternatives["required_skills"])
    )
    groups = [
        req for req in alternatives["structured_requirements"]
        if req["requirement_type"] == "REQUIRED_GROUP"
    ]
    assert len(groups) == 1
    assert groups[0]["data"]["match_mode"] == "ANY"
    assert {skill["skill"] for skill in groups[0]["data"]["skills"]} == {
        "Python",
        "Java",
        "JavaScript",
    }


# --- F-07: structured preference and group metadata -------------------------------

def test_structured_preferred_requirements_take_precedence_over_flat_preferred_skills():
    requirements = [
        _requirement("Python"),
        _requirement("Docker", "PREFERRED"),
    ]
    helper_result = match_structured_requirements(["Python"], requirements)
    assert helper_result["match_percentage"] == pytest.approx(100.0)
    assert "Docker" in helper_result["missing"]

    structured = _service().compute_match(
        resume_text="Used Python and Kubernetes",
        job_text="Python required; Docker preferred",
        resume_skills=["Python", "Kubernetes"],
        required_skills=["Python"],
        preferred_skills=["Kubernetes"],
        use_semantic=False,
        structured_requirements=requirements,
    )
    legacy = _service().compute_match(
        resume_text="Used Python and Kubernetes",
        job_text="Python required; Docker preferred",
        resume_skills=["Python", "Kubernetes"],
        required_skills=["Python"],
        preferred_skills=["Kubernetes"],
        use_semantic=False,
    )

    assert legacy["preferred_skill_coverage"] == pytest.approx(100.0)
    assert structured["preferred_skill_coverage"] == pytest.approx(0.0)
    assert "Docker" in structured["missing_skills"]
    assert "Kubernetes" in structured["additional_skills"]


def test_all_group_exposes_credit_separately_from_satisfaction():
    requirements = [
        _group("ALL", ["Docker", "Kubernetes", "AWS"]),
        _requirement("Python", "OPTIONAL"),
        {
            "requirement_type": "EXPERIENCE",
            "data": {"min_years": 5, "experience_type": "any"},
            "original_text": "5+ years experience",
        },
    ]
    result = _service().compute_match(
        resume_text="Docker, Kubernetes",
        job_text="Docker, Kubernetes and AWS required",
        resume_skills=["Docker", "Kubernetes"],
        required_skills=[],
        preferred_skills=[],
        use_semantic=False,
        structured_requirements=requirements,
    )

    group = result["group_evaluation"][0]
    assert group["match_mode"] == "ALL"
    assert group["is_satisfied"] is False

    assert group["credit"] == pytest.approx(0.6667, abs=1e-4)
    assert len(group["member_credits"]) == 3
    assert result["required_skill_coverage"] == pytest.approx(66.67, abs=0.01)
    assert "AWS" in result["missing_skills"]
    assert "fully matched 0 of 1" in result["explanation"]
    assert "partially matched 1" in result["explanation"]
    assert "not counted as fully matched" in result["explanation"]
    assert "satisfy 1 of 1" not in result["explanation"]

    metadata_only = _service().compute_match(
        resume_text="Docker, Kubernetes",
        job_text="Docker, Kubernetes and AWS required",
        resume_skills=["Docker", "Kubernetes"],
        required_skills=[],
        preferred_skills=[],
        use_semantic=False,
        structured_requirements=requirements[:1],
    )
    assert metadata_only["overall_score"] == pytest.approx(result["overall_score"])
    assert metadata_only["required_skill_coverage"] == pytest.approx(
        result["required_skill_coverage"]
    )



# --- Phase 11.4 preservation of Phase 11.3 invariants --------------------------


class _TokenizerStub:
    model_max_length = 32

    def __call__(self, text, add_special_tokens=True, **kwargs):
        pieces = str(text).split()
        if add_special_tokens:
            pieces = ["[CLS]", *pieces, "[SEP]"]
        return {"input_ids": pieces}


class NewApiSemanticStub:
    def is_available(self):
        return True

    def get_error_info(self):
        return None

    def get_model_context(self):
        return {
            "tokenizer": _TokenizerStub(),
            "max_seq_length": 32,
            "model_name": "stub",
            "model_revision": "stub",
        }

    def compute_similarity_matrix(self, queries, chunks):
        return [[0.75 for _ in chunks] for _ in queries]


def test_phase11_4_keeps_configured_weights_exact():
    config = ScoringConfig()
    assert config.required_skill_weight == 0.35
    assert config.preferred_skill_weight == 0.15
    assert config.semantic_weight == 0.30
    assert config.evidence_weight == 0.20
    assert config.tfidf_weight == 0.0


def test_phase11_4_keeps_the_existing_status_vocabulary():
    disabled = _service().compute_match("resume", "job", [], [], [], use_semantic=False)
    unavailable = _service().compute_match(
        "resume", "job", [], [], [], use_semantic=True
    )
    empty = _service(
        semantic=FakeSemanticService(available=True, score=0.5)
    ).compute_match("", "job", [], [], [], use_semantic=True)
    failed = _service(
        semantic=FakeSemanticService(available=True, raises=True)
    ).compute_match("resume", "job", [], [], [], use_semantic=True)
    used = _service(semantic=NewApiSemanticStub()).compute_match(
        "EXPERIENCE: Built Python APIs",
        "Required: Python",
        ["Python"],
        ["Python"],
        [],
        use_semantic=True,
        structured_requirements=[_requirement("Python")],
    )

    assert disabled["scoring_strategy"]["semantic_status"] == "disabled"
    assert unavailable["scoring_strategy"]["semantic_status"] == "model_unavailable"
    assert empty["scoring_strategy"]["semantic_status"] == "empty_text"
    assert failed["scoring_strategy"]["semantic_status"] == "inference_failed"
    assert used["scoring_strategy"]["semantic_status"] == "used"
    assert {
        result["scoring_strategy"]["semantic_status"]
        for result in (disabled, unavailable, empty, failed, used)
    } == {"disabled", "model_unavailable", "empty_text", "inference_failed", "used"}


def test_phase11_4_semantic_does_not_change_non_semantic_outputs():
    requirements = [_requirement("Python"), _group("ANY", ["AWS", "Azure"])]
    evidence = {
        "Python": [_evidence("Python")],
        "AWS": [_evidence("AWS")],
    }
    semantic = NewApiSemanticStub()
    service = ScoringService(config=ScoringConfig(), semantic_service=semantic)
    service.evidence_service.extract_skill_evidence = lambda *args, **kwargs: evidence

    kwargs = dict(
        resume_text="EXPERIENCE: Built Python APIs with AWS",
        job_text="Required: Python or AWS",
        resume_skills=["Python", "AWS"],
        required_skills=["Python"],
        preferred_skills=[],
        structured_requirements=requirements,
    )
    disabled = service.compute_match(**kwargs, use_semantic=False)
    used = service.compute_match(**kwargs, use_semantic=True)

    invariant_keys = (
        "required_skill_coverage",
        "preferred_skill_coverage",
        "evidence_score",
        "matched_skills",
        "additional_skills",
        "skill_evidence",
        "requirement_evaluations",
        "strengths",
        "gaps",
        "group_evaluation",
    )
    for key in invariant_keys:
        assert disabled[key] == used[key]

    assert [
        group["is_satisfied"] for group in disabled["group_evaluation"]
    ] == [group["is_satisfied"] for group in used["group_evaluation"]]
    assert used["semantic_score"] is not None


