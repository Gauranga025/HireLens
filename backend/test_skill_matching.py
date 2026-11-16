import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.skill_service import extract_skills, match_skills_to_requirements
from app.utils.text_processor import normalize_skill_name

# Test case 1: REST API vs RESTful services
print("=== Test 1: REST API vs RESTful services ===")
resume_text_1 = "Experience with RESTful services and building REST APIs"
jd_skills_1 = ["REST API"]
result_1 = extract_skills(resume_text_1)
print(f"Resume text: {resume_text_1}")
print(f"Extracted skills: {result_1['technical_skills']}")
match_1 = match_skills_to_requirements(result_1['technical_skills'], jd_skills_1)
print(f"JD requires: {jd_skills_1}")
print(f"Match result: {match_1}")
print()

# Test case 2: OOP vs object-oriented design
print("=== Test 2: OOP vs object-oriented design ===")
resume_text_2 = "Strong understanding of OOP principles and object-oriented design"
jd_skills_2 = ["Object-Oriented Programming"]
result_2 = extract_skills(resume_text_2)
print(f"Resume text: {resume_text_2}")
print(f"Extracted skills: {result_2['technical_skills']}")
match_2 = match_skills_to_requirements(result_2['technical_skills'], jd_skills_2)
print(f"JD requires: {jd_skills_2}")
print(f"Match result: {match_2}")
print()

# Test normalization
print("=== Normalization tests ===")
test_terms = ["oop", "object-oriented design", "object-oriented programming", "rest", "restful", "rest api"]
for term in test_terms:
    normalized = normalize_skill_name(term)
    print(f"{term} -> {normalized}")
print()

# Test case 3: PostgreSQL vs SQL
print("=== Test 3: PostgreSQL vs SQL ===")
resume_text_3 = "Experience with SQL databases and query optimization"
jd_skills_3 = ["PostgreSQL"]
result_3 = extract_skills(resume_text_3)
print(f"Resume text: {resume_text_3}")
print(f"Extracted skills: {result_3['technical_skills']}")
match_3 = match_skills_to_requirements(result_3['technical_skills'], jd_skills_3)
print(f"JD requires: {jd_skills_3}")
print(f"Match result: {match_3}")
print()

# Test case 4: FastAPI in different sections
print("=== Test 4: FastAPI in different sections ===")
resume_text_4 = """
Skills: Python, JavaScript
Experience: Developed web applications using FastAPI framework
Projects: Built REST APIs with FastAPI
"""
jd_skills_4 = ["FastAPI"]
result_4 = extract_skills(resume_text_4)
print(f"Resume text (multi-section): {resume_text_4}")
print(f"Extracted skills: {result_4['technical_skills']}")
match_4 = match_skills_to_requirements(result_4['technical_skills'], jd_skills_4)
print(f"JD requires: {jd_skills_4}")
print(f"Match result: {match_4}")
