"""
Analyze semantic matching errors and edge cases.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.semantic_matching_service import SemanticMatchingService

print("=== Semantic Matching Error Analysis ===\n")

semantic_service = SemanticMatchingService()

# Test 1: Genuine semantic matches
print("Test 1: Genuine Semantic Matches")
print("-" * 50)
pairs = [
    ("REST API development", "Built RESTful web services"),
    ("Python developer with FastAPI", "Developed APIs using FastAPI framework"),
    ("Object-Oriented Programming", "Strong understanding of OOP principles"),
    ("PostgreSQL database", "Worked with Postgres databases"),
]
for a, b in pairs:
    sim = semantic_service.compute_similarity(a, b)
    print(f"'{a}' vs '{b}'")
    print(f"  Similarity: {sim:.4f}")
    print(f"  Assessment: {'VALID MATCH' if sim > 0.6 else 'UNCERTAIN' if sim > 0.4 else 'WEAK'}")
    print()

# Test 2: Similar wording with different meanings
print("Test 2: Similar Wording, Different Meanings")
print("-" * 50)
pairs = [
    ("Python programming language", "Monty Python comedy group"),
    ("Java backend development", "JavaScript frontend development"),
    ("React framework", "React chemical reaction"),
    ("Docker containers", "Docker clothing brand"),
]
for a, b in pairs:
    sim = semantic_service.compute_similarity(a, b)
    print(f"'{a}' vs '{b}'")
    print(f"  Similarity: {sim:.4f}")
    print(f"  Assessment: {'FALSE POSITIVE RISK' if sim > 0.5 else 'SAFE'}")
    print()

# Test 3: Related but non-equivalent technologies
print("Test 3: Related but Non-Equivalent Technologies")
print("-" * 50)
pairs = [
    ("PostgreSQL database", "MySQL database"),
    ("MongoDB NoSQL", "PostgreSQL SQL"),
    ("React frontend", "Vue.js frontend"),
    ("Docker containerization", "Kubernetes orchestration"),
    ("TensorFlow ML", "PyTorch ML"),
]
for a, b in pairs:
    sim = semantic_service.compute_similarity(a, b)
    print(f"'{a}' vs '{b}'")
    print(f"  Similarity: {sim:.4f}")
    print(f"  Assessment: {'RELATED (not equivalent)' if sim > 0.5 else 'DISTINCT'}")
    print()

# Test 4: Keyword stuffing detection
print("Test 4: Keyword Stuffing")
print("-" * 50)
keyword_stuffer = """
Skills: Python, FastAPI, PostgreSQL, REST API, Docker, AWS, TensorFlow, PyTorch, React, Angular, Vue.js, MongoDB, Redis, GraphQL, Jenkins, Git, Linux, Ansible, Terraform, Prometheus, Grafana, Elasticsearch, Kafka, Spark, Hadoop, Scala, Go, Rust, Java, C++, C#, Ruby, PHP, Swift, Kotlin, Flutter, Dart, Unity, Unreal Engine, Blender, Photoshop, Figma, Sketch, Adobe XD

Experience:
- Junior Developer at TechStartup (2023-present)
  - Learning Python
  - Basic web development

Projects:
- Hello World app: Simple Python script
"""

minimal_experience = """
Skills: Python, FastAPI

Experience:
- Senior Backend Developer at TechCorp (2020-present)
  - Built scalable REST APIs using Python and FastAPI
  - Designed PostgreSQL database schemas
  - Deployed applications using Docker on AWS

Projects:
- E-commerce API: Built RESTful services with FastAPI and PostgreSQL
"""

job_desc = "Backend Software Engineer with Python, FastAPI, PostgreSQL, REST API experience"

sim_stuffing = semantic_service.compute_similarity(job_desc, keyword_stuffer)
sim_minimal = semantic_service.compute_similarity(job_desc, minimal_experience)

print(f"Job Description vs Keyword Stuffer:")
print(f"  Similarity: {sim_stuffing:.4f}")
print(f"  Assessment: {'STUFFING DETECTED (high similarity despite low experience)' if sim_stuffing > 0.5 else 'OK'}")
print()
print(f"Job Description vs Minimal Experience:")
print(f"  Similarity: {sim_minimal:.4f}")
print(f"  Assessment: {'VALID' if sim_minimal > 0.5 else 'WEAK'}")
print()

# Test 5: Skills in different sections
print("Test 5: Skills in Different Resume Sections")
print("-" * 50)
skills_section = "Skills: Python, FastAPI, PostgreSQL, REST API"
experience_section = "Built REST APIs using Python and FastAPI framework with PostgreSQL databases"
project_section = "Developed a web application using Python, FastAPI, and PostgreSQL"

job = "Backend Software Engineer with Python, FastAPI, PostgreSQL, REST API"

sim_skills = semantic_service.compute_similarity(job, skills_section)
sim_experience = semantic_service.compute_similarity(job, experience_section)
sim_project = semantic_service.compute_similarity(job, project_section)

print(f"Job vs Skills Section:")
print(f"  Similarity: {sim_skills:.4f}")
print()
print(f"Job vs Experience Section:")
print(f"  Similarity: {sim_experience:.4f}")
print()
print(f"Job vs Project Section:")
print(f"  Similarity: {sim_project:.4f}")
print()
print("Note: Experience and project sections show higher similarity due to contextual usage")

# Test 6: Professional experience vs skills list
print("Test 6: Professional Experience vs Skills List")
print("-" * 50)
professional = "Senior Backend Developer with 5 years experience building scalable REST APIs using Python and FastAPI"
skills_list = "Python, FastAPI, REST API, PostgreSQL, Docker, AWS"

job = "Backend Software Engineer with Python, FastAPI, PostgreSQL, REST API"

sim_professional = semantic_service.compute_similarity(job, professional)
sim_list = semantic_service.compute_similarity(job, skills_list)

print(f"Job vs Professional Experience:")
print(f"  Similarity: {sim_professional:.4f}")
print()
print(f"Job vs Skills List:")
print(f"  Similarity: {sim_list:.4f}")
print()
print("Note: Professional experience shows higher semantic relevance due to context")

print("\n=== Analysis Complete ===")
