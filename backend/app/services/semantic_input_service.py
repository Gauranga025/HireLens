"""Deterministic semantic input primitives for Phase 11.4.

This module builds requirement-aware query units and tokenizer-verified,
section-aware resume chunks. It never embeds text and never changes any
Phase 11.3 coverage, evidence, group, or status behaviour.
"""
from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from app.services.section_detection_service import SectionDetectionService, SectionType
from app.utils.text_processor import segment_sentences

SEMANTIC_ALGORITHM = "requirement_chunk_v1"
OVERFLOW_POLICY = "tail_and_section_anchors_v1"

RELEVANCE_THRESHOLD = 0.25
TOP_K = 3
RANK_WEIGHTS: Tuple[float, ...] = (1.00, 0.50, 0.25)

MAX_RESUME_CHUNKS = 64
MAX_TAIL_CHUNKS = 8
MAX_CONTEXT_REQUIREMENTS = 8
MAX_SEMANTIC_DIAGNOSTICS = 8
MAX_METADATA_TEXT_CHARS = 120
MAX_METADATA_SNIPPET_CHARS = 120

# Positive reserve for section prefixes, separators, and tokenizer special
# tokens. The final assembled text is still measured with the real tokenizer.
TOKEN_RESERVE = 16
_MIN_TINY_TOKENS = 6
_MAX_TOKEN_SPLIT_OVERLAP = 8

SECTION_BETA: Dict[str, float] = {
    SectionType.EXPERIENCE.value: 1.0,
    SectionType.PROJECTS.value: 1.0,
    SectionType.SKILLS.value: 0.8,
    SectionType.SUMMARY.value: 0.6,
    SectionType.UNCATEGORIZED.value: 0.5,
    SectionType.EDUCATION.value: 0.4,
    SectionType.CERTIFICATIONS.value: 0.4,
    SectionType.ACHIEVEMENTS.value: 0.4,
    SectionType.PUBLICATIONS.value: 0.4,
    SectionType.AWARDS.value: 0.4,
    SectionType.PERSONAL_INFO.value: 0.0,
}

_BULLET_PREFIX_RE = re.compile(r"^\s*(?:[-*\u2022]\s*|\(?\d+[.)]?\s+)")
_HEADING_RE = re.compile(
    r"^(?:required(?:\s+skills)?|preferred(?:\s+skills)?|optional(?:\s+skills)?|"
    r"nice\s+to\s+have|bonus(?:\s+points)?|responsibilities|qualifications|"
    r"experience|employment\s+history|skills|about\s+the\s+role|job\s+description)$",
    re.IGNORECASE,
)
_SKIPPED_CONTEXT_HEADINGS = {
    "optional",
    "optional skills",
    "nice to have",
    "bonus",
    "bonus points",
    "experience",
    "employment history",
}


class SemanticInputError(RuntimeError):
    """Raised when a semantic input cannot be verified safely."""


@dataclass
class SemanticUnit:
    """One top-level semantic scoring unit."""

    unit_id: str
    requirement_type: str
    text: str
    alpha: float
    source_index: int
    kind: str
    label: str
    scored: bool = True
    is_group: bool = False
    match_mode: Optional[str] = None
    group_name: Optional[str] = None
    member_texts: List[str] = field(default_factory=list)
    query_texts: List[str] = field(default_factory=list)
    member_query_texts: List[List[str]] = field(default_factory=list)


@dataclass(frozen=True)
class ResumeChunk:
    """A token-verified resume chunk with stable ordering metadata."""

    chunk_id: str
    section_type: str
    section_key: str
    section_index: int
    offset: int
    text: str
    token_count: int
    beta: float


@dataclass
class SemanticInputs:
    """All verified inputs required for requirement-to-chunk scoring."""

    units: List[SemanticUnit]
    chunks: List[ResumeChunk]
    chunk_stats: Dict[str, Any]
    max_seq_length: int
    token_limit: int
    context_unit_count: int = 0


def normalize_requirement_text(text: Any) -> str:
    """Normalize a requirement line for deterministic deduplication."""
    if not isinstance(text, str):
        return ""
    cleaned = _BULLET_PREFIX_RE.sub("", text)
    return re.sub(r"\s+", " ", cleaned).strip().casefold()


def _text_hash(text: str) -> str:
    return hashlib.sha256(normalize_requirement_text(text).encode("utf-8")).hexdigest()


def _validate_token_context(tokenizer: Any, max_seq_length: Any) -> Tuple[int, int]:
    if not callable(tokenizer):
        raise SemanticInputError("A model-compatible tokenizer is required.")
    if max_seq_length is None:
        raise SemanticInputError("The model maximum sequence length is unavailable.")
    try:
        max_len = int(max_seq_length)
    except (TypeError, ValueError) as exc:
        raise SemanticInputError("The model maximum sequence length is invalid.") from exc
    limit = max_len - TOKEN_RESERVE
    if limit <= 0:
        raise SemanticInputError("The token reserve leaves no usable input length.")
    return max_len, limit


def _call_tokenizer(tokenizer: Any, text: str, add_special_tokens: bool) -> Any:
    try:
        return tokenizer(text, add_special_tokens=add_special_tokens)
    except TypeError:
        return tokenizer(text)


def _token_ids_from_result(result: Any) -> Optional[List[Any]]:
    if isinstance(result, bool):
        return None
    if isinstance(result, int):
        return list(range(result))
    if isinstance(result, dict):
        for key in ("input_ids", "ids", "tokens", "token_ids"):
            if key in result:
                value = result[key]
                if isinstance(value, (list, tuple)):
                    if value and isinstance(value[0], (list, tuple)):
                        return list(value[0])
                    return list(value)
                if isinstance(value, int):
                    return list(range(value))
        return None
    if hasattr(result, "input_ids"):
        return _token_ids_from_result({"input_ids": getattr(result, "input_ids")})
    if hasattr(result, "tokens"):
        return _token_ids_from_result({"tokens": getattr(result, "tokens")})
    if isinstance(result, (list, tuple)):
        if result and isinstance(result[0], (list, tuple)):
            return list(result[0])
        return list(result)
    return None


def token_count(tokenizer: Any, text: str) -> int:
    """Count exact tokenizer tokens for the final assembled text."""
    if not isinstance(text, str):
        return 0
    try:
        result = _call_tokenizer(tokenizer, text, add_special_tokens=True)
    except Exception as exc:  # tokenizer failure must fail the semantic path
        raise SemanticInputError(f"Tokenizer verification failed: {exc}") from exc
    ids = _token_ids_from_result(result)
    if ids is None:
        raise SemanticInputError("Tokenizer did not expose token identifiers.")
    return len(ids)


def _token_pieces(tokenizer: Any, text: str) -> List[Any]:
    """Return token pieces suitable for deterministic span splitting."""
    try:
        result = _call_tokenizer(tokenizer, text, add_special_tokens=False)
        ids = _token_ids_from_result(result)
    except Exception:
        ids = None
    decode = getattr(tokenizer, "decode", None)
    if ids and callable(decode):
        return ids
    # Word pieces are only a split heuristic; every emitted text is verified
    # again with the tokenizer before it can be embedded.
    return re.findall(r"\S+", text)


def _decode_pieces(tokenizer: Any, pieces: List[Any]) -> str:
    if not pieces:
        return ""
    if isinstance(pieces[0], int):
        decode = getattr(tokenizer, "decode", None)
        if callable(decode):
            try:
                decoded = decode(pieces, skip_special_tokens=True)
            except TypeError:
                decoded = decode(pieces)
            if isinstance(decoded, str) and decoded.strip():
                return decoded.strip()
        return " ".join(f"token_{piece}" for piece in pieces)
    return " ".join(str(piece) for piece in pieces)


def _merge_tiny_fragments(
    fragments: List[str], tokenizer: Any, limit: int, prefix: str
) -> List[str]:
    merged: List[str] = []
    for fragment in fragments:
        fragment = fragment.strip()
        if not fragment:
            continue
        if merged:
            previous_count = token_count(tokenizer, f"{prefix}{merged[-1]}".strip())
            current_count = token_count(tokenizer, f"{prefix}{fragment}".strip())
            combined = f"{merged[-1]} {fragment}".strip()
            combined_count = token_count(tokenizer, f"{prefix}{combined}".strip())
            if (
                previous_count <= _MIN_TINY_TOKENS
                and current_count <= _MIN_TINY_TOKENS
                and combined_count <= limit
            ):
                merged[-1] = combined
                continue
        merged.append(fragment)
    return merged


def _split_text(text: str, tokenizer: Any, limit: int, prefix: str = "") -> List[str]:
    """Split text until every final prefixed text is within ``limit`` tokens."""
    cleaned = text.strip()
    if not cleaned:
        return []
    if token_count(tokenizer, f"{prefix}{cleaned}".strip()) <= limit:
        return [cleaned]

    prefix_count = token_count(tokenizer, prefix.strip() or "x")
    fragments: List[str] = []
    for sentence in segment_sentences(cleaned) or [cleaned]:
        sentence = sentence.strip()
        if not sentence:
            continue
        if token_count(tokenizer, f"{prefix}{sentence}".strip()) <= limit:
            fragments.append(sentence)
            continue

        pieces = _token_pieces(tokenizer, sentence)
        if not pieces:
            pieces = [sentence]
        window = max(1, limit - prefix_count - 2)
        overlap = min(_MAX_TOKEN_SPLIT_OVERLAP, max(0, window // 4))
        if overlap >= window:
            overlap = 0

        start = 0
        while start < len(pieces):
            end = min(len(pieces), start + window)
            candidate = _decode_pieces(tokenizer, pieces[start:end])
            count = token_count(tokenizer, f"{prefix}{candidate}".strip())
            while count > limit and end > start + 1:
                reduction = max(1, int(math.ceil((count - limit) / 2)))
                end = max(start + 1, end - reduction)
                candidate = _decode_pieces(tokenizer, pieces[start:end])
                count = token_count(tokenizer, f"{prefix}{candidate}".strip())
            if not candidate or count > limit:
                break
            fragments.append(candidate)
            if end >= len(pieces):
                break
            start = max(end - overlap, start + 1)

    verified = [
        fragment
        for fragment in _merge_tiny_fragments(fragments, tokenizer, limit, prefix)
        if token_count(tokenizer, f"{prefix}{fragment}".strip()) <= limit
    ]
    return verified


def _strip_section_heading(
    line: str,
    detector: SectionDetectionService,
) -> str:
    """Remove a leading detected section heading while keeping trailing text."""
    stripped = line.strip()
    compiled = getattr(detector, "_compiled_patterns", None)
    if not isinstance(compiled, dict):
        return stripped
    for patterns in compiled.values():
        for pattern in patterns:
            match = pattern.match(stripped)
            if match:
                return stripped[match.end():].strip(" :\t-")
    return stripped


def _is_heading_only(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    normalized = normalize_requirement_text(stripped).rstrip(":")
    if not normalized:
        return True
    if normalized in _SKIPPED_CONTEXT_HEADINGS:
        return True
    if len(normalized.split()) <= 4 and stripped.rstrip().endswith(":"):
        return True
    return bool(_HEADING_RE.fullmatch(normalized))


def _structured_represented_texts(structured_requirements: List[Dict[str, Any]]) -> List[str]:
    represented: List[str] = []
    for req in structured_requirements or []:
        if req.get("original_text"):
            represented.append(str(req["original_text"]))
        data = req.get("data") or {}
        if data.get("skill"):
            represented.append(str(data["skill"]))
        if data.get("group_name"):
            represented.append(str(data["group_name"]))
        for member in data.get("skills") or []:
            if isinstance(member, dict) and member.get("skill"):
                represented.append(str(member["skill"]))
    return represented


def _extract_transient_context(
    job_text: str,
    structured_requirements: List[Dict[str, Any]],
) -> List[SemanticUnit]:
    represented = [
        normalize_requirement_text(text)
        for text in _structured_represented_texts(structured_requirements)
    ]
    represented = [text for text in represented if text]
    seen = set()
    context_units: List[SemanticUnit] = []
    in_skipped_section = False

    for line_index, raw_line in enumerate((job_text or "").splitlines()):
        stripped = raw_line.strip()
        normalized = normalize_requirement_text(stripped)
        if not normalized:
            continue

        heading_key = normalized.rstrip(":")
        if _HEADING_RE.fullmatch(heading_key):
            if heading_key in _SKIPPED_CONTEXT_HEADINGS:
                in_skipped_section = True
                continue
            in_skipped_section = False
            continue
        if in_skipped_section or _is_heading_only(stripped):
            continue
        if len(normalized.split()) < 3:
            continue
        if any(normalized == rep or normalized in rep for rep in represented):
            continue
        if normalized in seen:
            continue

        seen.add(normalized)
        index = len(context_units)
        context_units.append(
            SemanticUnit(
                unit_id=f"context-{index:03d}",
                requirement_type="CONTEXT",
                text=stripped,
                label=f"context requirement {index + 1}",
                alpha=0.25,
                source_index=len(structured_requirements) + line_index,
                kind="context",
                scored=True,
            )
        )
        if len(context_units) >= MAX_CONTEXT_REQUIREMENTS:
            break

    return context_units


def build_semantic_requirements(
    structured_requirements: Optional[List[Dict[str, Any]]],
    job_text: str,
) -> List[SemanticUnit]:
    """Build deterministic top-level units from persisted JD data and raw lines."""
    requirements = list(structured_requirements or [])
    group_members = set()
    for req in requirements:
        if req.get("requirement_type") == "REQUIRED_GROUP":
            for member in (req.get("data") or {}).get("skills") or []:
                if isinstance(member, dict) and member.get("skill"):
                    normalized = normalize_requirement_text(member["skill"])
                    if normalized:
                        group_members.add(normalized)

    units: List[SemanticUnit] = []
    seen_individuals = set()
    seen_groups = set()

    for index, req in enumerate(requirements):
        req_type = req.get("requirement_type")
        data = req.get("data") or {}
        original_text = str(req.get("original_text") or "")

        if req_type in ("REQUIRED", "FUNDAMENTAL", "PREFERRED"):
            skill = data.get("skill")
            normalized = normalize_requirement_text(skill)
            if not normalized or normalized in group_members or normalized in seen_individuals:
                continue
            seen_individuals.add(normalized)
            alpha = 0.5 if req_type == "PREFERRED" else 1.0
            units.append(
                SemanticUnit(
                    unit_id=f"structured-{index:03d}",
                    requirement_type=str(req_type),
                    text=str(skill),
                    label=str(skill),
                    alpha=alpha,
                    source_index=index,
                    kind="individual",
                )
            )
            continue

        if req_type == "REQUIRED_GROUP":
            members = [
                str(member.get("skill"))
                for member in (data.get("skills") or [])
                if isinstance(member, dict) and member.get("skill")
            ]
            mode = str(data.get("match_mode") or "ANY").upper()
            group_name = str(data.get("group_name") or "Alternative Skills")
            dedupe_key = (
                req_type,
                mode,
                tuple(sorted(normalize_requirement_text(member) for member in members)),
            )
            if dedupe_key in seen_groups:
                continue
            seen_groups.add(dedupe_key)
            units.append(
                SemanticUnit(
                    unit_id=f"group-{index:03d}",
                    requirement_type=str(req_type),
                    text=original_text or group_name,
                    label=group_name,
                    alpha=1.0,
                    source_index=index,
                    kind="group",
                    is_group=True,
                    match_mode=mode,
                    group_name=group_name,
                    member_texts=members,
                )
            )
            continue

        if req_type in ("OPTIONAL", "EXPERIENCE"):
            units.append(
                SemanticUnit(
                    unit_id=f"diagnostic-{index:03d}",
                    requirement_type=str(req_type),
                    text=original_text,
                    label=f"{str(req_type).lower()} requirement {index + 1}",
                    alpha=0.0,
                    source_index=index,
                    kind="diagnostic",
                    scored=False,
                )
            )

    units.extend(_extract_transient_context(job_text, requirements))
    return units


def verify_requirement_units(
    units: List[SemanticUnit],
    tokenizer: Any,
    max_seq_length: int,
) -> List[SemanticUnit]:
    """Attach token-verified query segments to every scored unit."""
    _, limit = _validate_token_context(tokenizer, max_seq_length)
    verified: List[SemanticUnit] = []
    context_count = 0

    for unit in units:
        if not unit.scored or unit.alpha <= 0.0:
            unit.query_texts = []
            unit.member_query_texts = []
            verified.append(unit)
            continue

        if unit.is_group:
            member_queries: List[List[str]] = []
            for member in unit.member_texts:
                segments = _split_text(member, tokenizer, limit)
                member_queries.append(segments)
            unit.member_query_texts = member_queries
            flattened: List[str] = []
            seen = set()
            for segments in member_queries:
                for segment in segments:
                    key = normalize_requirement_text(segment)
                    if key and key not in seen:
                        seen.add(key)
                        flattened.append(segment)
            unit.query_texts = flattened
        else:
            unit.member_query_texts = []
            unit.query_texts = _split_text(unit.text, tokenizer, limit)

        for text in unit.query_texts:
            if token_count(tokenizer, text) > limit:
                raise SemanticInputError("An oversized requirement query survived verification.")

        if unit.kind == "context":
            context_count += 1
            if context_count > MAX_CONTEXT_REQUIREMENTS:
                continue

        verified.append(unit)

    return verified


def _apply_chunk_cap(
    chunks: List[ResumeChunk],
) -> Tuple[List[ResumeChunk], Dict[str, Any]]:
    generated = len(chunks)
    if generated <= MAX_RESUME_CHUNKS:
        retained = list(chunks)
    else:
        mandatory_ids = {chunk.chunk_id for chunk in chunks[-MAX_TAIL_CHUNKS:]}
        section_anchors: Dict[str, str] = {}
        for chunk in chunks:
            if chunk.section_type != SectionType.PERSONAL_INFO.value:
                section_anchors[chunk.section_key] = chunk.chunk_id
        mandatory_ids.update(section_anchors.values())
        if len(mandatory_ids) > MAX_RESUME_CHUNKS:
            raise SemanticInputError(
                "Mandatory tail and section anchors exceed MAX_RESUME_CHUNKS."
            )

        selected = set(mandatory_ids)
        remaining = [chunk for chunk in chunks if chunk.chunk_id not in selected]
        remaining.sort(key=lambda chunk: (-chunk.beta, chunk.offset, chunk.chunk_id))
        for chunk in remaining[: MAX_RESUME_CHUNKS - len(selected)]:
            selected.add(chunk.chunk_id)
        retained = [chunk for chunk in chunks if chunk.chunk_id in selected]

    stats = {
        "generated": generated,
        "retained": len(retained),
        "omitted": generated - len(retained),
        "overflow_policy": OVERFLOW_POLICY,
    }
    return retained, stats


def build_resume_chunks(
    resume_text: str,
    tokenizer: Any,
    max_seq_length: int,
    section_detector: Optional[SectionDetectionService] = None,
) -> Tuple[List[ResumeChunk], Dict[str, Any]]:
    """Create deterministic, token-verified, section-aware resume chunks."""
    _, limit = _validate_token_context(tokenizer, max_seq_length)
    detector = section_detector or SectionDetectionService()
    sections = detector.detect_sections(resume_text or "")
    if not sections and (resume_text or "").strip():
        sections = [
            (SectionType.UNCATEGORIZED, 0, len(resume_text), resume_text)
        ]

    fragments: List[Dict[str, Any]] = []
    sequence = 0
    detect_heading = getattr(detector, "_detect_section_heading", None)

    for section_index, (section_type, start, _, section_text) in enumerate(sections):
        if section_type == SectionType.PERSONAL_INFO:
            continue
        prefix = f"{section_type.value}: "
        line_start = start
        section_key = f"{section_index}:{section_type.value}"

        for line in section_text.split("\n"):
            stripped = line.strip()
            if stripped:
                content = _strip_section_heading(stripped, detector)
                is_heading_only = not content or _is_heading_only(content)
                if detect_heading and detect_heading(stripped) and is_heading_only:
                    continue
                for sentence in segment_sentences(content) or [content]:
                    sentence = sentence.strip()
                    if not sentence:
                        continue
                    for fragment_text in _split_text(
                        sentence, tokenizer, limit, prefix=prefix
                    ):
                        final_text = f"{prefix}{fragment_text.strip()}"
                        final_count = token_count(tokenizer, final_text)
                        if final_count > limit:
                            raise SemanticInputError(
                                "An oversized resume chunk survived verification."
                            )
                        relative = section_text.find(
                            fragment_text, max(0, line_start - start)
                        )
                        offset = start + relative if relative >= 0 else line_start
                        fragments.append(
                            {
                                "sequence": sequence,
                                "section_type": section_type.value,
                                "section_key": section_key,
                                "section_index": section_index,
                                "offset": offset,
                                "text": final_text,
                                "token_count": final_count,
                            }
                        )
                        sequence += 1
            line_start += len(line) + 1

    deduplicated: List[Dict[str, Any]] = []
    seen = set()
    for fragment in fragments:
        key = (fragment["section_type"], _text_hash(fragment["text"]))
        if key in seen:
            continue
        seen.add(key)
        deduplicated.append(fragment)

    deduplicated.sort(
        key=lambda fragment: (
            fragment["section_index"],
            fragment["offset"],
            fragment["sequence"],
        )
    )
    chunks = [
        ResumeChunk(
            chunk_id=f"{index:04d}",
            section_type=fragment["section_type"],
            section_key=fragment["section_key"],
            section_index=fragment["section_index"],
            offset=fragment["offset"],
            text=fragment["text"],
            token_count=fragment["token_count"],
            beta=SECTION_BETA.get(fragment["section_type"], 0.5),
        )
        for index, fragment in enumerate(deduplicated)
    ]
    return _apply_chunk_cap(chunks)


def build_semantic_inputs(
    job_text: str,
    resume_text: str,
    structured_requirements: Optional[List[Dict[str, Any]]],
    tokenizer: Any,
    max_seq_length: int,
    section_detector: Optional[SectionDetectionService] = None,
) -> SemanticInputs:
    """Build all verified semantic inputs for one evaluation."""
    max_len, limit = _validate_token_context(tokenizer, max_seq_length)
    units = build_semantic_requirements(structured_requirements, job_text)
    chunks, chunk_stats = build_resume_chunks(
        resume_text, tokenizer, max_len, section_detector=section_detector
    )
    units = verify_requirement_units(units, tokenizer, max_len)
    context_unit_count = sum(1 for unit in units if unit.kind == "context")
    return SemanticInputs(
        units=units,
        chunks=chunks,
        chunk_stats=chunk_stats,
        max_seq_length=max_len,
        token_limit=limit,
        context_unit_count=context_unit_count,
    )
