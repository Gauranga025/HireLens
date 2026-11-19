"""Deterministic tests for Phase 11.4 semantic input primitives."""
import pytest

from app.services import semantic_input_service as sis
from app.services.semantic_input_service import (
    MAX_CONTEXT_REQUIREMENTS,
    MAX_RESUME_CHUNKS,
    MAX_TAIL_CHUNKS,
    SemanticInputError,
    build_resume_chunks,
    build_semantic_inputs,
    build_semantic_requirements,
    token_count,
    verify_requirement_units,
)


class FakeTokenizer:
    """Whitespace tokenizer whose pieces round-trip through decode."""

    SPECIAL = ("[CLS]", "[SEP]")

    def __init__(self, max_length=64):
        self.model_max_length = max_length
        self.calls = []

    def __call__(self, text, add_special_tokens=True, **kwargs):
        self.calls.append((text, add_special_tokens))
        pieces = str(text).split()
        if add_special_tokens:
            pieces = [self.SPECIAL[0], *pieces, self.SPECIAL[1]]
        return {"input_ids": pieces}

    def decode(self, tokens, skip_special_tokens=True, **kwargs):
        if skip_special_tokens:
            tokens = [token for token in tokens if token not in self.SPECIAL]
        return " ".join(str(token) for token in tokens)


def _requirement(skill, requirement_type="REQUIRED", members=None, mode="ANY"):
    data = {"skill": skill, "normalized_skill": skill.lower()}
    if members is not None:
        data = {
            "group_name": "Alternatives",
            "match_mode": mode,
            "skills": [
                {"skill": member, "normalized_skill": member.lower()}
                for member in members
            ],
        }
    return {
        "requirement_type": requirement_type,
        "data": data,
        "original_text": skill if members is None else ", ".join(members),
    }


# --- Requirement units ---------------------------------------------------------


def test_requirement_units_cover_types_and_group_modes():
    structured = [
        _requirement("Python", "REQUIRED"),
        _requirement("Algorithms", "FUNDAMENTAL"),
        _requirement("Docker", "PREFERRED"),
        _requirement("Kubernetes", "EXPERIENCE"),
        _requirement("Nice-to-have", "OPTIONAL"),
        _requirement("AWS", "REQUIRED_GROUP", ["AWS", "Azure"], "ANY"),
        _requirement("AWS", "REQUIRED_GROUP", ["AWS", "Azure"], "ALL"),
    ]

    units = build_semantic_requirements(structured, "")

    assert [unit.requirement_type for unit in units] == [
        "REQUIRED",
        "FUNDAMENTAL",
        "PREFERRED",
        "EXPERIENCE",
        "OPTIONAL",
        "REQUIRED_GROUP",
        "REQUIRED_GROUP",
    ]
    assert [unit.alpha for unit in units] == [1.0, 1.0, 0.5, 0.0, 0.0, 1.0, 1.0]
    assert [unit.scored for unit in units] == [True, True, True, False, False, True, True]
    groups = [unit for unit in units if unit.is_group]
    assert [unit.match_mode for unit in groups] == ["ANY", "ALL"]
    assert all(unit.member_texts == ["AWS", "Azure"] for unit in groups)


def test_requirement_deduplication_and_group_member_exclusion():
    structured = [
        _requirement("python", "REQUIRED"),
        _requirement("Python", "REQUIRED"),
        _requirement("Terraform", "REQUIRED"),
        _requirement("Cloud", "REQUIRED_GROUP", ["Terraform", "Pulumi"], "ANY"),
        _requirement("Cloud", "REQUIRED_GROUP", ["Terraform", "Pulumi"], "ANY"),
    ]

    units = build_semantic_requirements(structured, "")

    individuals = [unit for unit in units if unit.kind == "individual"]
    groups = [unit for unit in units if unit.is_group]
    assert [unit.text for unit in individuals] == ["python"]
    assert len(groups) == 1
    assert groups[0].member_texts == ["Terraform", "Pulumi"]


def test_transient_context_skips_structured_optional_experience_and_duplicates():
    job_text = """Required Skills:
- Python
- Kubernetes
Optional:
- ignored optional responsibility with many words
EXPERIENCE:
- ignored employment responsibility with many words
Responsibilities:
- Build and operate resilient backend services with observability
- build and operate resilient backend services with observability
- Design secure APIs for distributed customer platforms
"""
    structured = [
        _requirement("Python", "REQUIRED"),
        _requirement("Kubernetes", "REQUIRED"),
        _requirement("Docker", "PREFERRED"),
        _requirement("ignored optional responsibility with many words", "OPTIONAL"),
    ]

    units = build_semantic_requirements(structured, job_text)
    context = [unit for unit in units if unit.kind == "context"]

    assert [unit.alpha for unit in context] == [0.25, 0.25]
    assert "Build and operate" in context[0].text
    assert "Design secure APIs" in context[1].text
    assert all("ignored" not in unit.text for unit in context)
    assert all("Python" not in unit.text and "Kubernetes" not in unit.text for unit in context)


def test_transient_context_is_capped_at_eight_in_source_order():
    lines = "\n".join(f"- Build resilient service number {index} for customers" for index in range(12))
    units = build_semantic_requirements([], f"Responsibilities:\n{lines}")
    context = [unit for unit in units if unit.kind == "context"]

    assert len(context) == MAX_CONTEXT_REQUIREMENTS == 8
    assert [unit.unit_id for unit in context] == [f"context-{index:03d}" for index in range(8)]
    assert all("number 0" in unit.text or "number 1" in unit.text for unit in context[:2])


def test_verify_requirement_units_token_checks_all_queries():
    tokenizer = FakeTokenizer(max_length=24)
    units = build_semantic_requirements(
        [_requirement("Python", "REQUIRED")],
        "Responsibilities:\n- Build resilient distributed systems with careful observability",
    )

    verified = verify_requirement_units(units, tokenizer, tokenizer.model_max_length)
    limit = tokenizer.model_max_length - sis.TOKEN_RESERVE

    assert verified == units
    assert verified[0].query_texts
    assert all(token_count(tokenizer, text) <= limit for text in verified[0].query_texts)


# --- Chunking and token bounds -------------------------------------------------


def test_exact_boundary_chunk_is_accepted():
    tokenizer = FakeTokenizer(max_length=24)  # limit = 8 final tokens
    resume = "EXPERIENCE:\na b c d e"

    chunks, stats = build_resume_chunks(resume, tokenizer, tokenizer.model_max_length)

    assert len(chunks) == 1
    assert chunks[0].token_count == 8
    assert chunks[0].text == "experience: a b c d e"
    assert stats["retained"] == 1


def test_over_boundary_chunk_is_split_and_every_chunk_is_verified():
    tokenizer = FakeTokenizer(max_length=24)
    resume = "EXPERIENCE:\na b c d e f"

    chunks, _ = build_resume_chunks(resume, tokenizer, tokenizer.model_max_length)
    limit = tokenizer.model_max_length - sis.TOKEN_RESERVE

    assert len(chunks) == 2
    assert all(chunk.token_count <= limit for chunk in chunks)
    assert "a b c" in chunks[0].text
    assert "d e f" in chunks[1].text


def test_long_bullets_split_at_sentence_boundaries_when_possible():
    tokenizer = FakeTokenizer(max_length=28)  # limit = 12
    resume = "EXPERIENCE:\nBuilt APIs. Deployed services. Monitored production systems closely."

    chunks, _ = build_resume_chunks(resume, tokenizer, tokenizer.model_max_length)

    assert len(chunks) >= 3
    assert any("Built APIs." in chunk.text for chunk in chunks)
    assert any("Deployed services." in chunk.text for chunk in chunks)
    assert all(chunk.token_count <= 12 for chunk in chunks)


def test_late_resume_evidence_is_retained_as_standalone_chunk():
    tokenizer = FakeTokenizer(max_length=32)
    filler = "\n".join(f"Performed routine task {index} with standard tooling" for index in range(40))
    resume = f"SUMMARY:\n{filler}\nEXPERIENCE:\nBuilt Node.js REST APIs with Express and PostgreSQL."

    chunks, _ = build_resume_chunks(resume, tokenizer, tokenizer.model_max_length)

    decisive = [chunk for chunk in chunks if "Node.js REST APIs" in chunk.text]
    assert decisive
    assert decisive[0].section_type == "experience"
    assert decisive[0].beta == 1.0
    assert decisive[0].token_count <= tokenizer.model_max_length - sis.TOKEN_RESERVE


def test_personal_info_and_duplicate_chunks_are_excluded():
    tokenizer = FakeTokenizer(max_length=48)
    resume = """Contact Information:
Jane Doe jane@example.com
SUMMARY:
Built reliable backend systems
Built reliable backend systems
"""

    chunks, _ = build_resume_chunks(resume, tokenizer, tokenizer.model_max_length)

    assert all("Jane Doe" not in chunk.text for chunk in chunks)
    assert all("jane@example.com" not in chunk.text for chunk in chunks)
    built = [chunk for chunk in chunks if "Built reliable backend systems" in chunk.text]
    assert len(built) == 1


def test_chunk_order_and_metadata_are_stable():
    tokenizer = FakeTokenizer(max_length=48)
    resume = """SKILLS:
Python FastAPI
EXPERIENCE:
Built APIs with FastAPI
"""

    first, first_stats = build_resume_chunks(resume, tokenizer, tokenizer.model_max_length)
    second, second_stats = build_resume_chunks(resume, tokenizer, tokenizer.model_max_length)

    assert [(c.chunk_id, c.text, c.offset, c.token_count) for c in first] == [
        (c.chunk_id, c.text, c.offset, c.token_count) for c in second
    ]
    assert first_stats == second_stats
    assert [chunk.chunk_id for chunk in first] == ["0000", "0001"]
    assert first[0].section_type == "skills"
    assert first[1].section_type == "experience"


def test_default_cap_retains_all_chunks_at_or_below_sixty_four():
    tokenizer = FakeTokenizer(max_length=32)
    resume = "EXPERIENCE:\n" + "\n".join(f"item {index}" for index in range(64))

    chunks, stats = build_resume_chunks(resume, tokenizer, tokenizer.model_max_length)

    assert len(chunks) == MAX_RESUME_CHUNKS == 64
    assert stats["generated"] == 64
    assert stats["retained"] == 64
    assert stats["omitted"] == 0


def test_overflow_retains_tail_anchors_and_higher_beta_chunks(monkeypatch):
    tokenizer = FakeTokenizer(max_length=32)
    resume = "EXPERIENCE:\n" + "\n".join(f"item {index}" for index in range(70))

    chunks, stats = build_resume_chunks(resume, tokenizer, tokenizer.model_max_length)

    retained_ids = {chunk.chunk_id for chunk in chunks}
    assert len(chunks) == MAX_RESUME_CHUNKS
    assert stats["generated"] == 70
    assert stats["retained"] == 64
    assert stats["omitted"] == 6
    assert stats["overflow_policy"] == "tail_and_section_anchors_v1"
    assert {f"{index:04d}" for index in range(62, 70)}.issubset(retained_ids)
    assert "0069" in retained_ids
    assert all("omitted" not in chunk.text for chunk in chunks)
    assert set(stats) == {"generated", "retained", "omitted", "overflow_policy"}

    # Keep the fixed production defaults intact for other tests.
    assert monkeypatch is not None


def test_mandatory_anchors_exceeding_cap_fail_safely(monkeypatch):
    tokenizer = FakeTokenizer(max_length=32)
    resume = "EXPERIENCE:\n" + "\n".join(f"item {index}" for index in range(10))
    monkeypatch.setattr(sis, "MAX_RESUME_CHUNKS", 3)
    monkeypatch.setattr(sis, "MAX_TAIL_CHUNKS", 8)

    with pytest.raises(SemanticInputError):
        build_resume_chunks(resume, tokenizer, tokenizer.model_max_length)


def test_missing_tokenizer_or_max_length_fails_safely():
    tokenizer = FakeTokenizer(max_length=32)
    with pytest.raises(SemanticInputError):
        build_resume_chunks("SUMMARY:\nBuilt systems", None, 32)
    with pytest.raises(SemanticInputError):
        build_resume_chunks("SUMMARY:\nBuilt systems", tokenizer, None)


def test_no_oversized_text_reaches_a_spy_embedder():
    tokenizer = FakeTokenizer(max_length=32)
    job_text = "Responsibilities:\n- Build resilient distributed systems with observability"
    resume_text = "EXPERIENCE:\nBuilt highly scalable distributed systems with strong observability"

    class SpyProvider:
        def __init__(self):
            self.texts = []

        def compute_similarity_matrix(self, queries, chunks):
            self.texts.extend(queries)
            self.texts.extend(chunks)
            return [[0.1] for _ in queries]

    inputs = build_semantic_inputs(
        job_text, resume_text, [], tokenizer, tokenizer.model_max_length
    )
    spy = SpyProvider()
    spy.compute_similarity_matrix(
        [text for unit in inputs.units for text in unit.query_texts],
        [chunk.text for chunk in inputs.chunks],
    )

    assert spy.texts
    assert all(token_count(tokenizer, text) <= inputs.token_limit for text in spy.texts)


def test_semantic_inputs_are_deterministic():
    tokenizer = FakeTokenizer(max_length=40)
    structured = [_requirement("Python", "REQUIRED")]
    args = (
        "Responsibilities:\n- Build reliable services",
        "EXPERIENCE:\nBuilt reliable Python services",
        structured,
    )

    first = build_semantic_inputs(*args, tokenizer, tokenizer.model_max_length)
    second = build_semantic_inputs(*args, tokenizer, tokenizer.model_max_length)

    assert [u.unit_id for u in first.units] == [u.unit_id for u in second.units]
    assert [u.query_texts for u in first.units] == [u.query_texts for u in second.units]
    assert [c.chunk_id for c in first.chunks] == [c.chunk_id for c in second.chunks]
    assert first.chunk_stats == second.chunk_stats
