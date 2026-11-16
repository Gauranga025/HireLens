import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

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


def extract_skills(text: str) -> Dict[str, List[str]]:
    if not text or not isinstance(text, str):
        return {"technical_skills": [], "soft_skills": []}

    skills_db = load_skills_database()
    technical_skills = skills_db.get("technical_skills", [])
    soft_skills = skills_db.get("soft_skills", [])

    normalized_text = normalize_text(text)
    found_technical: List[str] = []
    found_soft: List[str] = []
    seen: set = set()

    for skill in technical_skills:
        if not skill or not isinstance(skill, str):
            continue
        normalized_skill = normalize_skill_name(skill)
        if normalized_skill in seen:
            continue

        pattern = r"\b" + re.escape(skill) + r"\b"
        if re.search(pattern, normalized_text, re.IGNORECASE):
            seen.add(normalized_skill)
            found_technical.append(skill.strip())

    for skill in soft_skills:
        if not skill or not isinstance(skill, str):
            continue
        normalized_skill = normalize_skill_name(skill)
        if normalized_skill in seen:
            continue

        pattern = r"\b" + re.escape(skill) + r"\b"
        if re.search(pattern, normalized_text, re.IGNORECASE):
            seen.add(normalized_skill)
            found_soft.append(skill.strip())

    return {
        "technical_skills": found_technical,
        "soft_skills": found_soft,
    }


def match_skills_to_requirements(
    candidate_skills: List[str], required_skills: List[str], use_hierarchy: bool = True
) -> Dict[str, Any]:
    if not candidate_skills:
        candidate_skills = []
    if not required_skills:
        required_skills = []

    normalized_candidate = [normalize_skill_name(s) for s in candidate_skills if s]
    normalized_required = [normalize_skill_name(s) for s in required_skills if s]

    matched: List[str] = []
    missing: List[str] = []
    additional: List[str] = []
    
    # Track matched required skills to prevent duplicates
    matched_required_indices = set()

    # Get skill hierarchy registry if enabled
    hierarchy = get_skill_hierarchy_registry() if use_hierarchy else None

    # Group alternative skills (skills separated by " or " or "/" in original JD)
    # This is a simple heuristic - if consecutive skills in required_skills list
    # appear to be alternatives, treat them as a group
    alternative_groups: List[List[str]] = []
    current_group: List[str] = []
    
    for i, req_skill in enumerate(required_skills):
        if i < len(normalized_required):
            norm_req = normalized_required[i]
            # Check if this skill might be part of an alternative group
            # by looking at the original skill name for "or" or "/"
            if " or " in req_skill.lower() or "/" in req_skill:
                current_group.append(req_skill)
            else:
                if current_group:
                    alternative_groups.append(current_group)
                    current_group = []
                
                # Check for exact match first
                if norm_req in normalized_candidate:
                    matched.append(req_skill)
                    matched_required_indices.add(i)
                # Check for hierarchy matches if enabled (only full credit)
                elif hierarchy and i not in matched_required_indices:
                    for cand_skill in candidate_skills:
                        credit = hierarchy.get_match_credit(req_skill, cand_skill)
                        if credit >= 1.0:  # Only full credit (aliases/equivalents)
                            matched.append(req_skill)
                            matched_required_indices.add(i)
                            break
                    if i not in matched_required_indices:
                        missing.append(req_skill)
                else:
                    missing.append(req_skill)
    
    # Handle any remaining group
    if current_group:
        alternative_groups.append(current_group)
    
    # Process alternative groups - candidate needs at least one from each group
    for group in alternative_groups:
        group_matched = False
        for skill in group:
            norm_skill = normalize_skill_name(skill)
            if norm_skill in normalized_candidate:
                matched.append(skill)
                group_matched = True
                break
            # Check hierarchy for alternatives
            elif hierarchy:
                for cand_skill in candidate_skills:
                    credit = hierarchy.get_match_credit(skill, cand_skill)
                    if credit > 0:
                        matched.append(skill)
                        group_matched = True
                        break
        if not group_matched:
            missing.extend(group)

    for i, cand_skill in enumerate(candidate_skills):
        if i < len(normalized_candidate):
            norm_cand = normalized_candidate[i]
            if norm_cand not in normalized_required:
                additional.append(cand_skill)
        else:
            additional.append(cand_skill)

    if not required_skills:
        match_percentage = 0.0
    else:
        match_percentage = (len(matched) / len(required_skills)) * 100

    return {
        "matched": matched,
        "missing": missing,
        "additional": additional,
        "match_percentage": round(match_percentage, 2),
    }
