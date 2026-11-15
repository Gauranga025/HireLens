import re
from typing import Any, List, Set, Dict

from app.services.skill_service import extract_skills, load_skills_database


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

    required_skills: List[str] = []
    preferred_skills: List[str] = []

    lines = [line.strip().lower() for line in text.splitlines() if line.strip()]
    current_section = None

    for line in lines:
        if any(kw in line for kw in required_keywords):
            current_section = "required"
        elif any(kw in line for kw in preferred_keywords):
            current_section = "preferred"
        elif current_section == "required":
            for skill in technical_skills:
                if skill.lower() in line and skill not in required_skills:
                    required_skills.append(skill)
        elif current_section == "preferred":
            for skill in technical_skills:
                if skill.lower() in line and skill not in preferred_skills:
                    preferred_skills.append(skill)

    if not required_skills and not preferred_skills:
        required_skills = technical_skills

    return {
        "title": extract_job_title(text),
        "required_skills": required_skills,
        "preferred_skills": preferred_skills,
        "qualifications": extract_qualifications(text),
        "experience_required": extract_required_experience(text),
        "raw_text": text,
    }
