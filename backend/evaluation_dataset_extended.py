"""
Extended evaluation dataset for Phase 3 evidence intelligence testing.
Adds test cases for skill hierarchy, contextual evidence, and keyword stuffing.
"""
from evaluation_dataset import EVALUATION_DATASET

# Extended resumes for Phase 3 testing
PHASE3_RESUMES = [
    # Skill alias cases
    {
        "id": "resume_031",
        "name": "RESTful Services Alias",
        "content": """
Alex Turner
Backend Developer

Skills: Python, RESTful services, PostgreSQL

Experience:
- Backend Developer at WebAPI (2021-present)
  - Built RESTful web services using Python
  - PostgreSQL database design
  - API development and documentation

Projects:
- E-commerce API: RESTful services with Python
        """.strip(),
        "for_job": "jd_001",
        "relevance": "high",
        "skill_matches": {
            "Python": "matched",
            "FastAPI": "missing",
            "PostgreSQL": "matched",
            "REST API": "matched (as RESTful services)",
            "Docker": "missing",
            "AWS": "missing"
        },
        "test_category": "skill_alias"
    },
    {
        "id": "resume_032",
        "name": "Postgres Alias",
        "content": """
Brenda Lee
Database Developer

Skills: Python, FastAPI, Postgres

Experience:
- Database Developer at DataCo (2020-present)
  - Python application development
  - Postgres database administration
  - API development with FastAPI

Projects:
- Data migration tool: Python with Postgres
        """.strip(),
        "for_job": "jd_001",
        "relevance": "high",
        "skill_matches": {
            "Python": "matched",
            "FastAPI": "matched",
            "PostgreSQL": "matched (as Postgres)",
            "REST API": "missing",
            "Docker": "missing",
            "AWS": "missing"
        },
        "test_category": "skill_alias"
    },
    
    # Related technology cases (should NOT match)
    {
        "id": "resume_033",
        "name": "MySQL instead of PostgreSQL",
        "content": """
Chris Martin
Backend Developer

Skills: Python, FastAPI, MySQL, REST API

Experience:
- Backend Developer at SQLCo (2021-present)
  - Python and FastAPI development
  - MySQL database design
  - REST API development

Projects:
- User management API: FastAPI with MySQL
        """.strip(),
        "for_job": "jd_001",
        "relevance": "medium",
        "skill_matches": {
            "Python": "matched",
            "FastAPI": "matched",
            "PostgreSQL": "missing (has MySQL - related but not equivalent)",
            "REST API": "matched",
            "Docker": "missing",
            "AWS": "missing"
        },
        "test_category": "related_technology"
    },
    {
        "id": "resume_034",
        "name": "JavaScript instead of Java",
        "content": """
Diana Ross
Software Developer

Skills: JavaScript, React, Node.js

Experience:
- Frontend Developer at WebDev (2020-present)
  - JavaScript development
  - React applications
  - Node.js backend

Projects:
- E-commerce frontend: JavaScript with React
        """.strip(),
        "for_job": "jd_001",
        "relevance": "low",
        "skill_matches": {
            "Python": "missing",
            "FastAPI": "missing",
            "PostgreSQL": "missing",
            "REST API": "matched",
            "Docker": "missing",
            "AWS": "missing"
        },
        "test_category": "related_technology"
    },
    
    # Project vs professional experience
    {
        "id": "resume_035",
        "name": "Project Only Experience",
        "content": """
Eric Wright
Student Developer

Skills: Python, FastAPI, PostgreSQL, REST API

Projects:
- Personal API project: Built REST API using Python and FastAPI
- Database project: PostgreSQL database design with Python
- Web scraper: Python-based data extraction

Education:
- BS Computer Science (2022-2026)
        """.strip(),
        "for_job": "jd_001",
        "relevance": "medium",
        "skill_matches": {
            "Python": "matched",
            "FastAPI": "matched",
            "PostgreSQL": "matched",
            "REST API": "matched",
            "Docker": "missing",
            "AWS": "missing"
        },
        "test_category": "project_vs_professional"
    },
    {
        "id": "resume_036",
        "name": "Professional Experience",
        "content": """
Fiona Green
Senior Backend Developer

Skills: Python, FastAPI, PostgreSQL, REST API, Docker

Experience:
- Senior Backend Developer at TechCorp (2019-present)
  - Led team of 5 developers
  - Built scalable REST APIs using Python and FastAPI
  - PostgreSQL database architecture
  - Docker containerization
  - Reduced API response time by 40%

Projects:
- Microservices platform: FastAPI with PostgreSQL and Docker
        """.strip(),
        "for_job": "jd_001",
        "relevance": "high",
        "skill_matches": {
            "Python": "matched",
            "FastAPI": "matched",
            "PostgreSQL": "matched",
            "REST API": "matched",
            "Docker": "matched",
            "AWS": "missing"
        },
        "test_category": "project_vs_professional"
    },
    
    # Claimed vs demonstrated skills
    {
        "id": "resume_037",
        "name": "Claimed Skills Only",
        "content": """
George Hall
Junior Developer

Skills: Python, FastAPI, PostgreSQL, REST API, Docker, AWS, Kubernetes, TensorFlow, PyTorch, React, Angular, Vue.js, MongoDB, Redis, GraphQL, Jenkins, Git, Linux, Ansible, Terraform, Prometheus, Grafana

Experience:
- Junior Developer at Startup (2023-present)
  - Learning Python
  - Basic web development tasks

Projects:
- Hello World app: Simple Python script
        """.strip(),
        "for_job": "jd_001",
        "relevance": "low",
        "skill_matches": {
            "Python": "matched (claimed only)",
            "FastAPI": "matched (claimed only)",
            "PostgreSQL": "matched (claimed only)",
            "REST API": "matched (claimed only)",
            "Docker": "matched (claimed only)",
            "AWS": "matched (claimed only)"
        },
        "test_category": "claimed_vs_demonstrated"
    },
    {
        "id": "resume_038",
        "name": "Demonstrated Skills",
        "content": """
Hannah Clark
Backend Developer

Skills: Python, FastAPI, PostgreSQL

Experience:
- Backend Developer at APICompany (2020-present)
  - Developed production REST APIs using Python and FastAPI
  - Designed and implemented PostgreSQL database schemas
  - Optimized database queries reducing response time by 50%
  - Implemented Docker-based deployment pipeline

Projects:
- Customer data API: FastAPI with PostgreSQL, serving 1M+ requests/day
        """.strip(),
        "for_job": "jd_001",
        "relevance": "high",
        "skill_matches": {
            "Python": "matched (demonstrated)",
            "FastAPI": "matched (demonstrated)",
            "PostgreSQL": "matched (demonstrated)",
            "REST API": "matched (demonstrated)",
            "Docker": "matched (demonstrated)",
            "AWS": "missing"
        },
        "test_category": "claimed_vs_demonstrated"
    },
    
    # Internship experience
    {
        "id": "resume_039",
        "name": "Internship Experience",
        "content": """
Ian Scott
Software Engineering Intern

Skills: Python, FastAPI, PostgreSQL

Experience:
- Software Engineering Intern at TechStartup (Summer 2024)
  - Assisted with FastAPI API development
  - Worked on PostgreSQL database queries
  - Learned Python best practices

Projects:
- Intern project: Built simple API with FastAPI
        """.strip(),
        "for_job": "jd_001",
        "relevance": "medium",
        "skill_matches": {
            "Python": "matched (internship)",
            "FastAPI": "matched (internship)",
            "PostgreSQL": "matched (internship)",
            "REST API": "matched (internship)",
            "Docker": "missing",
            "AWS": "missing"
        },
        "test_category": "internship"
    },
    
    # Undated experience
    {
        "id": "resume_040",
        "name": "Undated Experience",
        "content": """
Julia Adams
Backend Developer

Skills: Python, FastAPI, PostgreSQL, REST API

Experience:
- Backend Developer at Company A
  - Built REST APIs using Python and FastAPI
  - PostgreSQL database work
- Backend Developer at Company B
  - API development with FastAPI
  - Database design with PostgreSQL

Projects:
- API Gateway: FastAPI with PostgreSQL
        """.strip(),
        "for_job": "jd_001",
        "relevance": "medium",
        "skill_matches": {
            "Python": "matched",
            "FastAPI": "matched",
            "PostgreSQL": "matched",
            "REST API": "matched",
            "Docker": "missing",
            "AWS": "missing"
        },
        "test_category": "undated_experience"
    },
    
    # Measurable outcomes
    {
        "id": "resume_041",
        "name": "Measurable Outcomes",
        "content": """
Kevin Brown
Senior Backend Developer

Skills: Python, FastAPI, PostgreSQL, REST API

Experience:
- Senior Backend Developer at ScaleUp (2019-present)
  - Built REST APIs serving 10M+ daily requests
  - Optimized PostgreSQL queries reducing latency by 60%
  - Implemented caching reducing database load by 40%
  - Led migration to FastAPI improving developer productivity by 30%

Projects:
- High-performance API: FastAPI with PostgreSQL, 99.9% uptime
        """.strip(),
        "for_job": "jd_001",
        "relevance": "high",
        "skill_matches": {
            "Python": "matched (measurable)",
            "FastAPI": "matched (measurable)",
            "PostgreSQL": "matched (measurable)",
            "REST API": "matched (measurable)",
            "Docker": "missing",
            "AWS": "missing"
        },
        "test_category": "measurable_outcomes"
    },
    
    # Education-based skills
    {
        "id": "resume_042",
        "name": "Education Skills Only",
        "content": """
Laura Davis
Recent Graduate

Skills: Python, FastAPI, PostgreSQL

Education:
- BS Computer Science (2022-2026)
  - Coursework: Database Systems (PostgreSQL), Web Development (Python, FastAPI)
  - Capstone: Built REST API using FastAPI and PostgreSQL
  - GPA: 3.8

Projects:
- Capstone project: Course-based API development
        """.strip(),
        "for_job": "jd_001",
        "relevance": "medium",
        "skill_matches": {
            "Python": "matched (education)",
            "FastAPI": "matched (education)",
            "PostgreSQL": "matched (education)",
            "REST API": "matched (education)",
            "Docker": "missing",
            "AWS": "missing"
        },
        "test_category": "education_skills"
    },
]

# Merge with existing dataset
EXTENDED_EVALUATION_DATASET = {
    "job_descriptions": EVALUATION_DATASET["job_descriptions"],
    "resumes": EVALUATION_DATASET["resumes"] + PHASE3_RESUMES,
}
