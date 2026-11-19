import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from app.utils.text_processor import normalize_skill_name, normalize_text
from app.data.skill_hierarchy import get_skill_hierarchy_registry

_SKILLS_DB_PATH = Path(__file__).parent.parent / "data" / "skills.json"

_SKILLS_DATABASE: Optional[Dict[str, List[str]]] = None


def load_skills_database() -> Dict[str, List[str]]:
    global _SKILLS_DATABASE

    if _SKILLS_DATABASE is not None:
        return _SKILLS_DATABASE

    try:
        with open(_SKILLS_DB_PATH, "r", encoding="utf-8") as f:
            _SKILLS_DATABASE = json.load(f)
    except FileNotFoundError:
        _SKILLS_DATABASE = {"technical_skills": [], "soft_skills": []}
    except json.JSONDecodeError:
        _SKILLS_DATABASE = {"technical_skills": [], "soft_skills": []}
    except Exception:
        _SKILLS_DATABASE = {"technical_skills": [], "soft_skills": []}

    return _SKILLS_DATABASE


# Aliases that need explicit extraction patterns because the canonical skill
# name contains punctuation that does not appear in the short form. The display
# name always remains the canonical entry from skills.json.
_EXTRA_SKILL_PATTERNS: Dict[str, Tuple[str, ...]] = {
    "node.js": ("Node", "NodeJS"),
}


def _skill_pattern_candidates(skills: List[str]) -> List[Tuple[str, str]]:
    """Return canonical-name/pattern pairs, longest pattern first."""
    candidates: List[Tuple[str, str]] = []
    for skill in skills:
        if not skill or not isinstance(skill, str):
            continue
        display_name = skill.strip()
        candidates.append((display_name, display_name))
        for alias in _EXTRA_SKILL_PATTERNS.get(normalize_skill_name(display_name), ()):
            candidates.append((display_name, alias))

    # Longest-first ensures C++/C#, Node.js/Node and similar pairs resolve to
    # the more specific skill before the shorter form can claim the same span.
    candidates.sort(key=lambda item: len(item[1]), reverse=True)
    return candidates


def find_skill_occurrences(text: str, skills: List[str]) -> List[Tuple[str, int, int]]:
    """Find nonduplicated skill occurrences using punctuation-safe boundaries.

    Matches are ordered by position in the text. A shorter skill contained in
    an already accepted longer match is suppressed, which prevents ``C`` from
    being extracted out of ``C++`` or ``Node`` out of ``Node.js``.
    """
    if not text or not isinstance(text, str):
        return []

    normalized_text = normalize_text(text)
    accepted_spans: List[Tuple[int, int]] = []
    results: List[Tuple[str, int, int]] = []
    seen: Set[str] = set()

    for display_name, pattern_text in _skill_pattern_candidates(skills):
        key = normalize_skill_name(display_name)
        if key in seen:
            continue

        pattern = re.compile(
            r"(?<!\w)" + re.escape(pattern_text) + r"(?!\w)",
            re.IGNORECASE,
        )
        for match in pattern.finditer(normalized_text):
            span = match.span()
            contained = any(
                span[0] >= start and span[1] <= end
                for start, end in accepted_spans
            )
            if contained:
                continue

            accepted_spans.append(span)
            seen.add(key)
            results.append((display_name, span[0], span[1]))
            break

    results.sort(key=lambda item: (item[1], item[2]))
    return results


def extract_skills(text: str) -> Dict[str, List[str]]:
    if not text or not isinstance(text, str):
        return {"technical_skills": [], "soft_skills": []}

    skills_db = load_skills_database()
    technical_skills = skills_db.get("technical_skills", [])
    soft_skills = skills_db.get("soft_skills", [])

    technical_keys = {
        normalize_skill_name(display_name)
        for display_name, _, _ in find_skill_occurrences(text, technical_skills)
    }
    soft_keys = {
        normalize_skill_name(display_name)
        for display_name, _, _ in find_skill_occurrences(text, soft_skills)
    }

    found_technical: List[str] = []
    found_soft: List[str] = []
    seen: Set[str] = set()

    # Iterate the canonical database order so existing response ordering stays
    # stable while detection itself uses the punctuation-safe matcher.
    for skill in technical_skills:
        key = normalize_skill_name(skill)
        if key in technical_keys and key not in seen:
            seen.add(key)
            found_technical.append(skill.strip())

    for skill in soft_skills:
        key = normalize_skill_name(skill)
        if key in soft_keys and key not in seen:
            seen.add(key)
            found_soft.append(skill.strip())

    return {
        "technical_skills": found_technical,
        "soft_skills": found_soft,
    }


def match_credit_to_type(credit: float) -> str:
    """Map an actual hierarchy credit to the stable match-type label."""
    if credit >= 1.0:
        return "exact"
    if credit > 0.0:
        return "related"
    return "distinct"


def _split_alternative_requirement(text: str) -> List[str]:
    """Split a legacy flat requirement string into alternative members."""
    if not text:
        return []

    words = re.split(r"\s+or\s+", text.strip(), flags=re.IGNORECASE)
    if len(words) > 1:
        return [part.strip() for part in words if part.strip()]

    # A slash is an alternative only when the complete string is not itself a
    # known skill (for example, CI/CD must remain one skill).
    known_skills = {
        normalize_skill_name(skill)
        for key in ("technical_skills", "soft_skills")
        for skill in load_skills_database().get(key, [])
    }
    if "/" in text and normalize_skill_name(text) not in known_skills:
        parts = [part.strip() for part in text.split("/") if part.strip()]
        if len(parts) > 1:
            return parts

    return [text]


def _best_skill_match(
    required_skill: str,
    candidate_skills: List[str],
    hierarchy,
    related_skill_credit_threshold: float,
) -> Tuple[float, Optional[str]]:
    """Return the actual credit and the candidate skill that produced it."""
    required_norm = normalize_skill_name(required_skill)

    for candidate_skill in candidate_skills:
        if normalize_skill_name(candidate_skill) == required_norm:
            return 1.0, candidate_skill

    best_credit = 0.0
    best_candidate: Optional[str] = None
    if hierarchy:
        for candidate_skill in candidate_skills:
            credit = hierarchy.get_match_credit(required_skill, candidate_skill)
            if credit >= related_skill_credit_threshold and credit > best_credit:
                best_credit = credit
                best_candidate = candidate_skill

    return best_credit, best_candidate


def _individual_unit(
    skill: str,
    candidate_skills: List[str],
    hierarchy,
    related_skill_credit_threshold: float,
    original_text: str = "",
) -> Dict[str, Any]:
    credit, evidence_skill = _best_skill_match(
        skill, candidate_skills, hierarchy, related_skill_credit_threshold
    )
    return {
        "kind": "individual",
        "skill": skill,
        "skills": [skill],
        "credit": credit,
        "member_credits": [credit],
        "member_evidence_skills": [evidence_skill],
        "evidence_skill": evidence_skill,
        "is_satisfied": credit > 0.0,
        "original_text": original_text,
    }


def _group_unit(
    skills: List[str],
    mode: str,
    group_name: str,
    candidate_skills: List[str],
    hierarchy,
    related_skill_credit_threshold: float,
    original_text: str = "",
) -> Dict[str, Any]:
    member_results = [
        _best_skill_match(
            skill, candidate_skills, hierarchy, related_skill_credit_threshold
        )
        for skill in skills
    ]
    member_credits = [credit for credit, _ in member_results]
    member_evidence_skills = [evidence_skill for _, evidence_skill in member_results]

    if mode == "ANY":
        credit = max(member_credits, default=0.0)
        representative_index = (
            member_credits.index(credit) if member_credits and credit > 0.0 else None
        )
        is_satisfied = credit > 0.0
    else:  # ALL
        credit = (
            sum(member_credits) / len(member_credits) if member_credits else 0.0
        )
        representative_index = None
        is_satisfied = bool(member_credits) and all(
            member_credit > 0.0 for member_credit in member_credits
        )

    evidence_skill = (
        member_evidence_skills[representative_index]
        if representative_index is not None
        else None
    )

    return {
        "kind": "all" if mode == "ALL" else "any",
        "group_name": group_name,
        "match_mode": mode,
        "skills": skills,
        "credit": credit,
        "member_credits": member_credits,
        "member_evidence_skills": member_evidence_skills,
        "evidence_skill": evidence_skill,
        "is_satisfied": is_satisfied,
        "original_text": original_text,
    }


def _add_credit_metadata(units: List[Dict[str, Any]]) -> Tuple[Dict[str, float], Dict[str, Optional[str]]]:
    credits: Dict[str, float] = {}
    evidence_skills: Dict[str, Optional[str]] = {}

    for unit in units:
        for index, skill in enumerate(unit.get("skills", [])):
            member_credit = unit.get("member_credits", [0.0] * len(unit.get("skills", [])))[index]
            member_evidence_skill = unit.get(
                "member_evidence_skills", [None] * len(unit.get("skills", []))
            )[index]
            if skill not in credits or member_credit > credits[skill]:
                credits[skill] = member_credit
                evidence_skills[skill] = member_evidence_skill

    return credits, evidence_skills


def _empty_match_result(candidate_skills: Optional[List[str]] = None) -> Dict[str, Any]:
    return {
        "matched": [],
        "missing": [],
        "additional": list(candidate_skills or []),
        "match_percentage": 0.0,
        "group_evaluation": [],
        "required_units": [],
        "preferred_units": [],
        "requirement_credits": {},
        "evidence_skills": {},
    }


def collect_structured_preferred_skills(
    structured_requirements: List[Dict],
) -> List[str]:
    """Collect deduplicated preferred skills from structured requirements."""
    preferred: List[str] = []
    seen: Set[str] = set()

    for req in structured_requirements or []:
        if req.get("requirement_type") != "PREFERRED":
            continue
        skill = (req.get("data") or {}).get("skill")
        if not skill:
            continue
        normalized = normalize_skill_name(skill)
        if normalized and normalized not in seen:
            seen.add(normalized)
            preferred.append(skill)

    return preferred


def match_skills_to_requirements(
    candidate_skills: List[str], required_skills: List[str], use_hierarchy: bool = True, related_skill_credit_threshold: float = 1.0
) -> Dict[str, Any]:
    """
    Match candidate skills to requirements (legacy function for backward compatibility).

    Actual hierarchy credit is preserved in coverage and in the additive
    ``required_units`` metadata used by evidence scoring.
    """
    if not candidate_skills:
        candidate_skills = []
    if not required_skills:
        return _empty_match_result(candidate_skills)

    hierarchy = get_skill_hierarchy_registry() if use_hierarchy else None

    required_units: List[Dict[str, Any]] = []
    for requirement in required_skills:
        members = _split_alternative_requirement(requirement)
        if len(members) > 1:
            required_units.append(
                _group_unit(
                    members,
                    "ANY",
                    "Legacy Alternatives",
                    candidate_skills,
                    hierarchy,
                    related_skill_credit_threshold,
                    requirement,
                )
            )
        else:
            required_units.append(
                _individual_unit(
                    requirement,
                    candidate_skills,
                    hierarchy,
                    related_skill_credit_threshold,
                    requirement,
                )
            )

    matched: List[str] = []
    missing: List[str] = []
    additional: List[str] = []

    for unit in required_units:
        if unit["kind"] == "individual":
            if unit["credit"] > 0.0:
                matched.append(unit["skill"])
            else:
                missing.append(unit["skill"])
            continue

        if unit["credit"] > 0.0:
            for index, credit in enumerate(unit["member_credits"]):
                if credit > 0.0:
                    matched.append(unit["skills"][index])
        else:
            missing.extend(unit["skills"])

    requirement_names = {
        normalize_skill_name(skill)
        for unit in required_units
        for skill in unit["skills"]
    }
    for candidate_skill in candidate_skills:
        if normalize_skill_name(candidate_skill) not in requirement_names:
            additional.append(candidate_skill)

    credits, evidence_skills = _add_credit_metadata(required_units)
    match_percentage = (
        sum(unit["credit"] for unit in required_units) / len(required_units) * 100.0
        if required_units
        else 0.0
    )

    return {
        "matched": matched,
        "missing": missing,
        "additional": additional,
        "match_percentage": round(match_percentage, 2),
        "group_evaluation": [],
        "required_units": required_units,
        "preferred_units": [],
        "requirement_credits": credits,
        "evidence_skills": evidence_skills,
    }


def match_structured_requirements(
    candidate_skills: List[str],
    structured_requirements: List[Dict],
    use_hierarchy: bool = True,
    related_skill_credit_threshold: float = 1.0,
) -> Dict[str, Any]:
    """
    Match candidate skills to structured requirements (Phase 10.2).

    Actual hierarchy credit, not binary membership, drives coverage, group
    metadata, and evidence eligibility. Preferred matches remain in the display
    list but never contribute to required coverage or required evidence.
    """
    if not candidate_skills:
        candidate_skills = []
    if not structured_requirements:
        return _empty_match_result(candidate_skills)

    hierarchy = get_skill_hierarchy_registry() if use_hierarchy else None

    group_skills_set: Set[str] = set()
    for req in structured_requirements:
        if req.get("requirement_type") == "REQUIRED_GROUP":
            for skill_data in (req.get("data") or {}).get("skills", []):
                skill = skill_data.get("skill")
                if skill:
                    group_skills_set.add(normalize_skill_name(skill))

    required_units: List[Dict[str, Any]] = []
    preferred_units: List[Dict[str, Any]] = []
    seen_individuals: Set[str] = set()
    seen_preferred: Set[str] = set()

    for req in structured_requirements:
        req_type = req.get("requirement_type")
        data = req.get("data") or {}
        original_text = req.get("original_text", "")

        if req_type in ("REQUIRED", "FUNDAMENTAL"):
            skill = data.get("skill")
            if not skill:
                continue
            normalized = normalize_skill_name(skill)
            if normalized in group_skills_set or normalized in seen_individuals:
                continue
            seen_individuals.add(normalized)
            required_units.append(
                _individual_unit(
                    skill,
                    candidate_skills,
                    hierarchy,
                    related_skill_credit_threshold,
                    original_text,
                )
            )

        elif req_type == "REQUIRED_GROUP":
            skills = [
                skill_data.get("skill")
                for skill_data in data.get("skills", [])
                if skill_data.get("skill")
            ]
            required_units.append(
                _group_unit(
                    skills,
                    data.get("match_mode", "ANY"),
                    data.get("group_name", "Alternative Skills"),
                    candidate_skills,
                    hierarchy,
                    related_skill_credit_threshold,
                    original_text,
                )
            )

        elif req_type == "PREFERRED":
            skill = data.get("skill")
            if not skill:
                continue
            normalized = normalize_skill_name(skill)
            if normalized in seen_preferred:
                continue
            seen_preferred.add(normalized)
            preferred_units.append(
                _individual_unit(
                    skill,
                    candidate_skills,
                    hierarchy,
                    related_skill_credit_threshold,
                    original_text,
                )
            )

        # OPTIONAL and EXPERIENCE requirements are metadata only.

    matched_flat: List[str] = []
    missing_flat: List[str] = []
    additional_flat: List[str] = []
    group_evaluation: List[Dict[str, Any]] = []

    for unit in required_units:
        if unit["kind"] == "individual":
            if unit["credit"] > 0.0:
                matched_flat.append(unit["skill"])
            else:
                missing_flat.append(unit["skill"])
            continue

        for index, credit in enumerate(unit["member_credits"]):
            if credit > 0.0:
                matched_flat.append(unit["skills"][index])
            elif not unit["is_satisfied"]:
                # Unmatched alternatives are not gaps when ANY/ALL is satisfied.
                missing_flat.append(unit["skills"][index])

        group_evaluation.append({
            "requirement_type": "REQUIRED_GROUP",
            "match_mode": unit["match_mode"],
            "group_name": unit["group_name"],
            "required_skills": unit["skills"],
            "matched_skills": [
                skill
                for skill, credit in zip(unit["skills"], unit["member_credits"])
                if credit > 0.0
            ],
            "is_satisfied": unit["is_satisfied"],
            "credit": round(unit["credit"], 4),
            "member_credits": [
                {"skill": skill, "credit": round(credit, 4)}
                for skill, credit in zip(unit["skills"], unit["member_credits"])
            ],
            "original_text": unit["original_text"],
        })

    # Preferred matches are intentionally display-only here; ScoringService
    # computes preferred coverage from the dedicated preferred units.
    for unit in preferred_units:
        if unit["credit"] > 0.0:
            matched_flat.append(unit["skill"])
        else:
            missing_flat.append(unit["skill"])

    requirement_names = {
        normalize_skill_name(skill)
        for unit in required_units + preferred_units
        for skill in unit["skills"]
    }
    for candidate_skill in candidate_skills:
        if normalize_skill_name(candidate_skill) not in requirement_names:
            additional_flat.append(candidate_skill)

    required_credits, required_evidence_skills = _add_credit_metadata(required_units)
    preferred_credits, preferred_evidence_skills = _add_credit_metadata(preferred_units)
    requirement_credits = {**preferred_credits, **required_credits}
    evidence_skills = {**preferred_evidence_skills, **required_evidence_skills}

    match_percentage = (
        sum(unit["credit"] for unit in required_units) / len(required_units) * 100.0
        if required_units
        else 0.0
    )

    return {
        "matched": matched_flat,
        "missing": missing_flat,
        "additional": additional_flat,
        "match_percentage": round(match_percentage, 2),
        "group_evaluation": group_evaluation,
        "required_units": required_units,
        "preferred_units": preferred_units,
        "requirement_credits": requirement_credits,
        "evidence_skills": evidence_skills,
    }
