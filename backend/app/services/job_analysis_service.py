import re
from typing import Any, List, Set, Dict, Optional

from app.services.skill_service import (
    extract_skills,
    find_skill_occurrences,
    normalize_skill_name,
)
from app.schemas.job import (
    RequirementType,
    MatchMode,
    ExperienceType,
    SkillRequirement,
    RequirementGroup,
    ExperienceRequirement,
    FundamentalRequirement,
    StructuredRequirement,
)


def extract_job_title(text: str) -> str:
    if not text or not isinstance(text, str):
        return "Not found"

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return "Not found"

    title_keywords = [
        "engineer",
        "developer",
        "manager",
        "analyst",
        "scientist",
        "architect",
        "consultant",
        "specialist",
        "director",
        "lead",
        "intern",
        "coordinator",
        "officer",
        "administrator",
        "designer",
        "representative",
        "assistant",
        "associate",
    ]

    for line in lines[:10]:
        if "@" in line or "http" in line.lower():
            continue

        if len(line.split()) > 8:
            continue

        lower_line = line.lower()
        if any(kw in lower_line for kw in title_keywords):
            return line.strip()

    return lines[0] if lines else "Not found"


def extract_required_experience(text: str) -> str:
    if not text or not isinstance(text, str):
        return "Not specified"

    patterns = [
        r"(\d+\+?\s*(?:years?|yrs?)\s*(?:of\s*)?(?:experience|exp))",
        r"(\d+\s*[-–—to]+\s*\d+\s*(?:years?|yrs?)\s*(?:of\s*)?(?:experience|exp))",
        r"(minimum\s+(\d+)\s*(?:years?|yrs?))",
        r"((?:at\s*least|minimum)\s+(\d+)\s*(?:years?|yrs?))",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0).strip()

    return "Not specified"


def detect_alternative_skills(line: str, skills: List[str]) -> List[str]:
    """
    Detect if a line contains alternative skills (e.g., "Python, Java, or JavaScript").
    Returns the list of alternative skills found, or empty list if not an alternative pattern.
    """
    if " or " not in line.lower() and "/" not in line:
        return []

    found_skills = [
        skill for skill, _, _ in find_skill_occurrences(line, skills)
    ]
    return found_skills if len(found_skills) >= 2 else []


def parse_alternative_group(line: str, skills: List[str], group_name: str = "Alternative Skills") -> Optional[RequirementGroup]:
    """
    Parse an alternative skill group from a line.

    Example: "Proficiency in at least one of Python, Java, JavaScript or TypeScript"
    Returns a RequirementGroup with match_mode=ANY.
    """
    alternatives = detect_alternative_skills(line, skills)
    if not alternatives or len(alternatives) < 2:
        return None

    skill_requirements = [
        SkillRequirement(
            skill=skill,
            normalized_skill=normalize_skill_name(skill),
            original_text=line
        )
        for skill in alternatives
    ]

    return RequirementGroup(
        group_name=group_name,
        match_mode=MatchMode.ANY,
        skills=skill_requirements,
        original_text=line
    )


def parse_experience_requirement(line: str) -> Optional[ExperienceRequirement]:
    """
    Parse an experience requirement from a line.

    Examples:
    - "2+ years of experience" -> min_years=2
    - "3-5 years of professional experience" -> min_years=3, max_years=5, experience_type=PROFESSIONAL
    - "Internship experience" -> experience_type=INTERNSHIP
    """
    # Check for experience type keywords
    exp_type = ExperienceType.ANY
    if "professional" in line.lower() or "full-time" in line.lower():
        exp_type = ExperienceType.PROFESSIONAL
    elif "internship" in line.lower() or "intern" in line.lower():
        exp_type = ExperienceType.INTERNSHIP

    # Parse year ranges
    min_years = None
    max_years = None

    # Pattern: "X+ years" or "X+ years of experience"
    plus_match = re.search(r"(\d+)\+\s*(?:years?|yrs?)", line, re.IGNORECASE)
    if plus_match:
        min_years = int(plus_match.group(1))

    # Pattern: "X-Y years" or "X to Y years"
    range_match = re.search(r"(\d+)\s*[-–—to]+\s*(\d+)\s*(?:years?|yrs?)", line, re.IGNORECASE)
    if range_match:
        min_years = int(range_match.group(1))
        max_years = int(range_match.group(2))

    # Pattern: "minimum X years" or "at least X years"
    min_match = re.search(r"(?:minimum|at\s*least)\s+(\d+)\s*(?:years?|yrs?)", line, re.IGNORECASE)
    if min_match and min_years is None:
        min_years = int(min_match.group(1))

    # Only create requirement if we found some year information
    if min_years is not None or max_years is not None or exp_type != ExperienceType.ANY:
        return ExperienceRequirement(
            min_years=min_years,
            max_years=max_years,
            experience_type=exp_type,
            original_text=line
        )

    return None


FUNDAMENTAL_SKILLS = {
    "data structures",
    "algorithms",
    "object-oriented programming",
    "oop",
    "database management systems",
    "dbms",
    "operating systems",
    "computer networks",
    "problem solving",
    "problem-solving",
}


def is_fundamental_skill(skill: str) -> bool:
    """Check if a skill is a fundamental engineering requirement."""
    normalized = skill.lower()
    return any(fundamental in normalized for fundamental in FUNDAMENTAL_SKILLS)


def parse_fundamental_requirement(skill: str, original_text: str) -> FundamentalRequirement:
    """Parse a fundamental engineering requirement."""
    return FundamentalRequirement(
        skill=skill,
        normalized_skill=normalize_skill_name(skill),
        original_text=original_text
    )


def extract_qualifications(text: str) -> List[str]:
    if not text or not isinstance(text, str):
        return []

    qualification_keywords = [
        "bachelor",
        "master",
        "phd",
        "doctorate",
        "degree",
        "diploma",
        "certification",
        "certified",
        "b.tech",
        "m.tech",
        "b.e",
        "m.e",
        "b.sc",
        "m.sc",
        "mba",
        "cse",
        "computer science",
        "engineering",
        "graduate",
        "postgraduate",
    ]

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    qualifications: List[str] = []
    seen: Set[str] = set()

    for line in lines:
        lower_line = line.lower()
        if any(kw in lower_line for kw in qualification_keywords):
            clean = re.sub(r"^[\s*•▪\-–—\d.)]+", "", line).strip()
            if clean and len(clean) >= 3:
                normalized = clean.lower()
                if normalized not in seen:
                    seen.add(normalized)
                    qualifications.append(clean)

    return qualifications


def analyze_job_description(text: str) -> Dict[str, Any]:
    if not text or not isinstance(text, str):
        return {
            "title": "Not found",
            "required_skills": [],
            "preferred_skills": [],
            "qualifications": [],
            "experience_required": "Not specified",
            "structured_requirements": [],
            "raw_text": "",
        }

    skills_data = extract_skills(text)
    technical_skills = skills_data.get("technical_skills", [])
    soft_skills = skills_data.get("soft_skills", [])

    required_keywords = [
        "required",
        "must have",
        "essential",
        "mandatory",
        "need",
        "should have",
    ]
    preferred_keywords = [
        "preferred",
        "nice to have",
        "bonus",
        "plus",
        "advantageous",
        "desired",
    ]
    optional_keywords = [
        "optional",
        "a plus",
        "added advantage",
    ]

    required_skills: List[str] = []
    preferred_skills: List[str] = []
    structured_requirements: List[StructuredRequirement] = []

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    current_section = None

    # Track seen fundamental skills to avoid duplicates
    seen_fundamentals: Set[str] = set()

    for line in lines:
        line_lower = line.lower()
        line_group_skills: Set[str] = set()

        # Metadata requirements are recorded, but the same line is still
        # scanned below so skills on experience/alternative lines are not lost.
        exp_req = parse_experience_requirement(line)
        if exp_req:
            structured_requirements.append(StructuredRequirement(
                requirement_type=RequirementType.EXPERIENCE,
                data=exp_req.model_dump(mode="json"),
                original_text=line
            ))

        # Check for alternative skills pattern
        alt_group = parse_alternative_group(line, technical_skills)
        if alt_group:
            if current_section == "required":
                structured_requirements.append(StructuredRequirement(
                    requirement_type=RequirementType.REQUIRED_GROUP,
                    data=alt_group.model_dump(mode="json"),
                    original_text=line
                ))
                required_skills.extend([s.skill for s in alt_group.skills])
            elif current_section == "preferred":
                preferred_skills.extend([s.skill for s in alt_group.skills])

            # Alternatives are already represented by the group. Do not emit
            # them again as individual requirements from this line.
            line_group_skills = {
                normalize_skill_name(s.skill) for s in alt_group.skills
            }

        # Check for fundamental skills
        for skill, _, _ in find_skill_occurrences(line, technical_skills):
            if is_fundamental_skill(skill) and skill not in seen_fundamentals:
                seen_fundamentals.add(skill)
                fundamental_req = parse_fundamental_requirement(skill, line)
                structured_requirements.append(StructuredRequirement(
                    requirement_type=RequirementType.FUNDAMENTAL,
                    data=fundamental_req.model_dump(mode="json"),
                    original_text=line
                ))

        # A section keyword may appear on the same line as a skill. Update the
        # section state first, then scan the line itself below.
        if any(kw in line_lower for kw in required_keywords):
            current_section = "required"
        elif any(kw in line_lower for kw in preferred_keywords):
            current_section = "preferred"
        elif any(kw in line_lower for kw in optional_keywords):
            current_section = "optional"

        line_skills = [
            skill
            for skill, _, _ in find_skill_occurrences(line, technical_skills)
            if normalize_skill_name(skill) not in line_group_skills
        ]

        if current_section == "required":
            for skill in line_skills:
                if skill not in required_skills:
                    required_skills.append(skill)
                    # A skill already emitted as FUNDAMENTAL must not be
                    # emitted again as an individual REQUIRED requirement.
                    if skill not in seen_fundamentals:
                        structured_requirements.append(StructuredRequirement(
                            requirement_type=RequirementType.REQUIRED,
                            data={"skill": skill, "normalized_skill": normalize_skill_name(skill)},
                            original_text=line
                        ))
        elif current_section == "preferred":
            for skill in line_skills:
                if skill not in preferred_skills:
                    preferred_skills.append(skill)
                    structured_requirements.append(StructuredRequirement(
                        requirement_type=RequirementType.PREFERRED,
                        data={"skill": skill, "normalized_skill": normalize_skill_name(skill)},
                        original_text=line
                    ))
        elif current_section == "optional":
            for skill in line_skills:
                structured_requirements.append(StructuredRequirement(
                    requirement_type=RequirementType.OPTIONAL,
                    data={"skill": skill, "normalized_skill": normalize_skill_name(skill)},
                    original_text=line
                ))

    if not required_skills and not preferred_skills:
        required_skills = technical_skills
        # Add all as REQUIRED for backward compatibility
        for skill in technical_skills:
            if is_fundamental_skill(skill) and skill not in seen_fundamentals:
                seen_fundamentals.add(skill)
                fundamental_req = parse_fundamental_requirement(skill, text)
                structured_requirements.append(StructuredRequirement(
                    requirement_type=RequirementType.FUNDAMENTAL,
                    data=fundamental_req.model_dump(mode="json"),
                    original_text=text
                ))
            else:
                structured_requirements.append(StructuredRequirement(
                    requirement_type=RequirementType.REQUIRED,
                    data={"skill": skill, "normalized_skill": normalize_skill_name(skill)},
                    original_text=text
                ))

    return {
        "title": extract_job_title(text),
        "required_skills": required_skills,
        "preferred_skills": preferred_skills,
        "qualifications": extract_qualifications(text),
        "experience_required": extract_required_experience(text),
        "structured_requirements": [
            req.model_dump(mode="json") for req in structured_requirements
        ],
        "raw_text": text,
    }
