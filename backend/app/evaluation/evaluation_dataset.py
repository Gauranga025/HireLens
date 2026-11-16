"""
Synthetic evaluation dataset for ranking evaluation.
Contains labeled resume-job pairs with expected relevance.
"""
from typing import List, Dict, Any
from enum import Enum


class RelevanceLabel(Enum):
    """Relevance labels for evaluation."""
    HIGHLY_RELEVANT = 3
    PARTIALLY_RELEVANT = 2
    WEAKLY_RELEVANT = 1
    NOT_RELEVANT = 0


class EvaluationExample:
    """A single evaluation example."""
    
    def __init__(
        self,
        resume_id: str,
        candidate_name: str,
        resume_text: str,
        job_id: str,
        job_title: str,
        job_description: str,
        required_skills: List[str],
        preferred_skills: List[str],
        expected_relevance: RelevanceLabel,
        reasoning: str,
    ):
        self.resume_id = resume_id
        self.candidate_name = candidate_name
        self.resume_text = resume_text
        self.job_id = job_id
        self.job_title = job_title
        self.job_description = job_description
        self.required_skills = required_skills
        self.preferred_skills = preferred_skills
        self.expected_relevance = expected_relevance
        self.reasoning = reasoning
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "resume_id": self.resume_id,
            "candidate_name": self.candidate_name,
            "resume_text": self.resume_text,
            "job_id": self.job_id,
            "job_title": self.job_title,
            "job_description": self.job_description,
            "required_skills": self.required_skills,
            "preferred_skills": self.preferred_skills,
            "expected_relevance": self.expected_relevance.value,
            "reasoning": self.reasoning,
        }


# Backend Developer Job
BACKEND_JOB = {
    "job_id": "job_backend_001",
    "job_title": "Senior Backend Developer",
    "job_description": """
    We are seeking a Senior Backend Developer to join our team.
    
    Required Skills:
    - Python or Java
    - REST API development
    - SQL database experience (PostgreSQL or MySQL)
    - Docker containerization
    
    Preferred Skills:
    - Kubernetes
    - Redis caching
    - AWS cloud services
    - Microservices architecture
    
    Responsibilities:
    - Design and implement scalable REST APIs
    - Optimize database queries and performance
    - Deploy and manage containerized applications
    """,
    "required_skills": ["Python", "Java", "REST API", "PostgreSQL", "MySQL", "Docker"],
    "preferred_skills": ["Kubernetes", "Redis", "AWS", "Microservices"],
}

# Frontend Developer Job
FRONTEND_JOB = {
    "job_id": "job_frontend_001",
    "job_title": "Frontend Developer",
    "job_description": """
    We are looking for a Frontend Developer to build modern web applications.
    
    Required Skills:
    - React or Vue.js
    - TypeScript
    - CSS/Tailwind
    
    Preferred Skills:
    - Next.js
    - State management (Redux, MobX)
    - Testing frameworks
    """,
    "required_skills": ["React", "Vue.js", "TypeScript", "CSS", "Tailwind"],
    "preferred_skills": ["Next.js", "Redux", "MobX", "Testing"],
}

# Data Engineer Job
DATA_ENGINEER_JOB = {
    "job_id": "job_data_001",
    "job_title": "Data Engineer",
    "job_description": """
    Seeking a Data Engineer to build data pipelines and analytics infrastructure.
    
    Required Skills:
    - Python
    - SQL
    - ETL processes
    - Data warehousing
    
    Preferred Skills:
    - Apache Spark
    - Airflow
    - Cloud platforms (AWS/GCP)
    """,
    "required_skills": ["Python", "SQL", "ETL", "Data warehousing"],
    "preferred_skills": ["Apache Spark", "Airflow", "AWS", "GCP"],
}


# Synthetic Resumes for Backend Job
BACKEND_RESUMES = [
    EvaluationExample(
        resume_id="resume_be_001",
        candidate_name="Alice Johnson",
        resume_text="""
        Alice Johnson
        alice@example.com
        
        Professional Summary
        Senior Backend Developer with 5 years of experience building scalable APIs.
        
        Work Experience
        Senior Backend Developer at TechCorp
        - Developed RESTful APIs using Python and FastAPI
        - Designed PostgreSQL database schemas with optimized queries
        - Containerized applications using Docker
        - Implemented microservices architecture
        
        Skills
        Python, FastAPI, PostgreSQL, Docker, REST APIs, Microservices
        """,
        **BACKEND_JOB,
        expected_relevance=RelevanceLabel.HIGHLY_RELEVANT,
        reasoning="Candidate has all required skills (Python, REST API, PostgreSQL, Docker) and demonstrates them in work experience.",
    ),
    EvaluationExample(
        resume_id="resume_be_002",
        candidate_name="Bob Smith",
        resume_text="""
        Bob Smith
        bob@example.com
        
        Skills
        Java, Spring Boot, MySQL, REST API
        
        Experience
        Java Developer at ABC Corp
        - Built REST APIs with Spring Boot
        - Worked with MySQL databases
        """,
        **BACKEND_JOB,
        expected_relevance=RelevanceLabel.HIGHLY_RELEVANT,
        reasoning="Candidate satisfies required skills with Java alternative, has REST API and SQL experience.",
    ),
    EvaluationExample(
        resume_id="resume_be_003",
        candidate_name="Carol Davis",
        resume_text="""
        Carol Davis
        carol@example.com
        
        Skills
        Python, JavaScript, HTML, CSS
        
        Projects
        Built a web application with Python and Flask.
        """,
        **BACKEND_JOB,
        expected_relevance=RelevanceLabel.PARTIALLY_RELEVANT,
        reasoning="Candidate has Python but lacks REST API, SQL, and Docker experience. Only basic web development.",
    ),
    EvaluationExample(
        resume_id="resume_be_004",
        candidate_name="David Wilson",
        resume_text="""
        David Wilson
        david@example.com
        
        Skills
        Python, Machine Learning, Data Science
        
        Experience
        Data Scientist at XYZ Inc
        - Worked on ML models using Python
        - Used pandas and numpy for data analysis
        """,
        **BACKEND_JOB,
        expected_relevance=RelevanceLabel.WEAKLY_RELEVANT,
        reasoning="Candidate has Python but experience is in data science, not backend development. Lacks API, SQL, Docker.",
    ),
    EvaluationExample(
        resume_id="resume_be_005",
        candidate_name="Eva Brown",
        resume_text="""
        Eva Brown
        eva@example.com
        
        Skills
        C++, JavaScript, React
        
        Experience
        Full Stack Developer
        - Built frontend with React
        - Some backend work with Node.js
        """,
        **BACKEND_JOB,
        expected_relevance=RelevanceLabel.WEAKLY_RELEVANT,
        reasoning="Candidate lacks Python/Java, SQL, and Docker. Has some backend experience but not with required stack.",
    ),
]

# Synthetic Resumes for Frontend Job
FRONTEND_RESUMES = [
    EvaluationExample(
        resume_id="resume_fe_001",
        candidate_name="Frank Miller",
        resume_text="""
        Frank Miller
        frank@example.com
        
        Work Experience
        Frontend Developer at WebCorp
        - Built React applications with TypeScript
        - Styled components using Tailwind CSS
        - Implemented state management with Redux
        
        Skills
        React, TypeScript, Tailwind, Redux, Next.js
        """,
        **FRONTEND_JOB,
        expected_relevance=RelevanceLabel.HIGHLY_RELEVANT,
        reasoning="Candidate has all required skills (React, TypeScript, CSS/Tailwind) and preferred skills (Redux, Next.js).",
    ),
    EvaluationExample(
        resume_id="resume_fe_002",
        candidate_name="Grace Lee",
        resume_text="""
        Grace Lee
        grace@example.com
        
        Skills
        Vue.js, TypeScript, CSS
        
        Projects
        Built SPA with Vue.js and TypeScript.
        Styled with custom CSS.
        """,
        **FRONTEND_JOB,
        expected_relevance=RelevanceLabel.HIGHLY_RELEVANT,
        reasoning="Candidate satisfies required skills with Vue.js alternative, has TypeScript and CSS.",
    ),
    EvaluationExample(
        resume_id="resume_fe_003",
        candidate_name="Henry Chen",
        resume_text="""
        Henry Chen
        henry@example.com
        
        Skills
        JavaScript, HTML, CSS
        
        Experience
        Web Developer
        - Built websites with vanilla JavaScript
        - Used Bootstrap for styling
        """,
        **FRONTEND_JOB,
        expected_relevance=RelevanceLabel.PARTIALLY_RELEVANT,
        reasoning="Candidate has CSS but lacks React/Vue and TypeScript. Uses vanilla JS instead of frameworks.",
    ),
]

# Synthetic Resumes for Data Engineer Job
DATA_ENGINEER_RESUMES = [
    EvaluationExample(
        resume_id="resume_de_001",
        candidate_name="Ivy Martinez",
        resume_text="""
        Ivy Martinez
        ivy@example.com
        
        Work Experience
        Data Engineer at DataCorp
        - Built ETL pipelines using Python
        - Designed data warehouse schemas
        - Optimized SQL queries for analytics
        - Used Apache Spark for big data processing
        
        Skills
        Python, SQL, ETL, Data Warehousing, Apache Spark, Airflow
        """,
        **DATA_ENGINEER_JOB,
        expected_relevance=RelevanceLabel.HIGHLY_RELEVANT,
        reasoning="Candidate has all required skills and multiple preferred skills (Spark, Airflow).",
    ),
    EvaluationExample(
        resume_id="resume_de_002",
        candidate_name="Jack Thompson",
        resume_text="""
        Jack Thompson
        jack@example.com
        
        Skills
        Python, SQL
        
        Experience
        Software Developer
        - Wrote Python scripts for data processing
        - Used SQL for database queries
        """,
        **DATA_ENGINEER_JOB,
        expected_relevance=RelevanceLabel.PARTIALLY_RELEVANT,
        reasoning="Candidate has Python and SQL but lacks ETL and data warehousing experience.",
    ),
]


def get_all_examples() -> List[EvaluationExample]:
    """Get all evaluation examples."""
    return BACKEND_RESUMES + FRONTEND_RESUMES + DATA_ENGINEER_RESUMES


def get_examples_by_job(job_id: str) -> List[EvaluationExample]:
    """Get evaluation examples for a specific job."""
    all_examples = get_all_examples()
    return [ex for ex in all_examples if ex.job_id == job_id]
