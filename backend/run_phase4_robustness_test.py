"""
Phase 4 Robustness Testing
Test the matching engine with various resume formats and edge cases.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.scoring_service import ScoringService, ScoringConfig
from app.services.skill_service import extract_skills

print("=== Phase 4 Robustness Testing ===\n")

# Test job
job_description = """
We are looking for a Backend Software Engineer to join our team.

Required Skills:
- Python
- FastAPI
- PostgreSQL
- REST API development

Preferred Skills:
- Docker
- AWS
- Kubernetes

The ideal candidate has experience building scalable REST APIs using Python and FastAPI,
with strong database skills in PostgreSQL. Experience with containerization and cloud deployment is a plus.
""".strip()

required_skills = ["Python", "FastAPI", "PostgreSQL", "REST API"]
preferred_skills = ["Docker", "AWS", "Kubernetes"]

# Test cases
test_cases = [
    {
        "name": "Resume with missing sections",
        "content": """
John Smith
Backend Developer

Experience: Built APIs with Python and PostgreSQL.
        """.strip(),
    },
    {
        "name": "Resume with long project descriptions",
        "content": """
John Smith
Backend Developer

Skills: Python, FastAPI, PostgreSQL, REST API, Docker, AWS

Experience:
- Senior Backend Developer at TechCorp (2020-present)
  - Built scalable REST APIs using Python and FastAPI
  - Designed PostgreSQL database schemas
  - Deployed applications using Docker on AWS
  - Implemented CI/CD pipelines
  - Led team of 5 developers
  - Reduced API response time by 40%
  - Implemented caching layer using Redis
  - Migrated monolithic architecture to microservices
  - Set up monitoring and alerting
  - Conducted code reviews and mentored junior developers

Projects:
- E-commerce API: Built RESTful services with FastAPI and PostgreSQL
  - Designed database schema with proper indexing
  - Implemented JWT authentication
  - Added rate limiting
  - Created comprehensive API documentation
  - Wrote unit tests with 90% coverage
  - Deployed to AWS using Docker
  - Set up CI/CD pipeline with GitHub Actions
  - Implemented logging and monitoring
  - Optimized database queries reducing response time by 50%
        """.strip(),
    },
    {
        "name": "Resume with abbreviated skills",
        "content": """
John Smith
Backend Dev

Skills: Py, FastAPI, Postgres, REST, Docker, AWS

Experience: Built REST APIs using Python and PostgreSQL with Docker on AWS.
        """.strip(),
    },
    {
        "name": "Resume with inconsistent formatting",
        "content": """
John Smith
Backend Developer

Skills:
Python
FastAPI
PostgreSQL
REST API
Docker
AWS

Experience:
Senior Backend Developer at TechCorp (2020-present)
Built scalable REST APIs using Python and FastAPI
Designed PostgreSQL database schemas
Deployed applications using Docker on AWS

Projects:
E-commerce API
Built RESTful services with FastAPI and PostgreSQL
        """.strip(),
    },
    {
        "name": "Resume with experience but no skills section",
        "content": """
John Smith
Backend Developer

Experience:
- Senior Backend Developer at TechCorp (2020-present)
  - Built scalable REST APIs using Python and FastAPI
  - Designed PostgreSQL database schemas
  - Deployed applications using Docker on AWS

Projects:
- E-commerce API: Built RESTful services with FastAPI and PostgreSQL
        """.strip(),
    },
    {
        "name": "Fresh graduate resume",
        "content": """
Jane Doe
Recent Graduate

Education:
BS Computer Science (2022-2026)
GPA: 3.8
Coursework: Database Systems, Web Development, Algorithms

Projects:
- Personal API project: Built REST API using Python and FastAPI
- Database project: PostgreSQL database design with Python
- Web scraper: Python-based data extraction

Skills: Python, FastAPI, PostgreSQL, REST API
        """.strip(),
    },
    {
        "name": "Experienced candidate resume",
        "content": """
John Smith
Senior Backend Developer

Experience:
- Senior Backend Developer at TechCorp (2020-present)
  - Led team of 5 developers
  - Built scalable REST APIs using Python and FastAPI
  - Designed PostgreSQL database schemas
  - Deployed applications using Docker on AWS
  - Reduced API response time by 40%
- Backend Developer at Startup (2018-2020)
  - Developed REST APIs using Python
  - PostgreSQL database administration
  - AWS deployment

Skills: Python, FastAPI, PostgreSQL, REST API, Docker, AWS, Kubernetes
        """.strip(),
    },
    {
        "name": "Empty resume",
        "content": "",
    },
    {
        "name": "Resume with only contact info",
        "content": """
John Smith
Email: john@example.com
Phone: 555-1234
        """.strip(),
    },
]

scoring_service = ScoringService(config=ScoringConfig())

print(f"Testing {len(test_cases)} resume variations\n")
print("="*60)

results = []

for i, test_case in enumerate(test_cases):
    print(f"\nTest {i+1}: {test_case['name']}")
    print("-"*60)
    
    try:
        # Extract skills
        skills = extract_skills(test_case["content"])["technical_skills"]
        print(f"Technical skills: {skills}")
        
        # Score
        result = scoring_service.compute_match(
            resume_text=test_case["content"],
            job_text=job_description,
            resume_skills=skills,
            required_skills=required_skills,
            preferred_skills=preferred_skills,
            use_semantic=True,
        )
        
        print(f"Overall score: {result['overall_score']:.2f}%")
        print(f"Required coverage: {result['required_skill_coverage']:.2f}%")
        print(f"Evidence score: {result['evidence_score']:.2f}%")
        
        results.append({
            "name": test_case["name"],
            "success": True,
            "score": result["overall_score"],
            "skills": skills,
        })
        
    except Exception as e:
        print(f"ERROR: {e}")
        results.append({
            "name": test_case["name"],
            "success": False,
            "error": str(e),
        })

print(f"\n{'='*60}")
print("Summary")
print(f"{'='*60}")

successful = sum(1 for r in results if r["success"])
failed = len(results) - successful

print(f"Successful: {successful}/{len(results)}")
print(f"Failed: {failed}/{len(results)}")

print(f"\nDetailed Results:")
for r in results:
    status = "✓" if r["success"] else "✗"
    score = f"{r['score']:.2f}%" if r["success"] else "N/A"
    print(f"  {status} {r['name']}: {score}")

print(f"\n=== Phase 4 Robustness Testing Complete ===")
