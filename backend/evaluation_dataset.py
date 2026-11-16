"""
Evaluation dataset for HireLens matching quality assessment.
Contains job descriptions, resumes, and human relevance labels.
"""

EVALUATION_DATASET = {
    "job_descriptions": [
        {
            "id": "jd_001",
            "title": "Backend Software Engineer",
            "description": """
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
            """.strip(),
            "required_skills": ["Python", "FastAPI", "PostgreSQL", "REST API"],
            "preferred_skills": ["Docker", "AWS", "Kubernetes"]
        },
        {
            "id": "jd_002",
            "title": "Full Stack Developer",
            "description": """
We need a Full Stack Developer for our web application.

Required Skills:
- React
- Node.js
- TypeScript
- MongoDB

Preferred Skills:
- GraphQL
- AWS
- Docker

The candidate should be proficient in React frontend development with TypeScript,
Node.js backend, and MongoDB database experience.
            """.strip(),
            "required_skills": ["React", "Node.js", "TypeScript", "MongoDB"],
            "preferred_skills": ["GraphQL", "AWS", "Docker"]
        },
        {
            "id": "jd_003",
            "title": "Machine Learning Engineer",
            "description": """
We are seeking a Machine Learning Engineer to build production ML systems.

Required Skills:
- Python
- TensorFlow
- scikit-learn
- SQL

Preferred Skills:
- PyTorch
- AWS SageMaker
- Docker

Experience with building and deploying machine learning models in production is required.
Strong SQL skills for data extraction and feature engineering.
            """.strip(),
            "required_skills": ["Python", "TensorFlow", "scikit-learn", "SQL"],
            "preferred_skills": ["PyTorch", "AWS SageMaker", "Docker"]
        },
        {
            "id": "jd_004",
            "title": "DevOps Engineer",
            "description": """
We need a DevOps Engineer to manage our cloud infrastructure.

Required Skills:
- Docker
- Kubernetes
- AWS
- CI/CD

Preferred Skills:
- Terraform
- Ansible
- Linux

Experience with container orchestration, cloud platforms, and automated deployment pipelines is essential.
            """.strip(),
            "required_skills": ["Docker", "Kubernetes", "AWS", "CI/CD"],
            "preferred_skills": ["Terraform", "Ansible", "Linux"]
        },
        {
            "id": "jd_005",
            "title": "Data Engineer",
            "description": """
We are looking for a Data Engineer to build data pipelines.

Required Skills:
- Python
- SQL
- Apache Spark
- PostgreSQL

Preferred Skills:
- Airflow
- AWS
- Docker

Experience with ETL pipelines, data warehousing, and big data processing is required.
            """.strip(),
            "required_skills": ["Python", "SQL", "Apache Spark", "PostgreSQL"],
            "preferred_skills": ["Airflow", "AWS", "Docker"]
        }
    ],
    "resumes": [
        # JD_001 (Backend Engineer) - Strong matches
        {
            "id": "resume_001",
            "name": "Strong Backend Match",
            "content": """
John Smith
Backend Software Engineer

Skills: Python, FastAPI, PostgreSQL, REST API, Docker, AWS

Experience:
- Senior Backend Developer at TechCorp (2020-present)
  - Built scalable REST APIs using Python and FastAPI
  - Designed PostgreSQL database schemas
  - Deployed applications using Docker on AWS
  - Implemented CI/CD pipelines

Projects:
- E-commerce API: Built RESTful services with FastAPI and PostgreSQL
- Microservices architecture: Designed and implemented using FastAPI
            """.strip(),
            "for_job": "jd_001",
            "relevance": "high",
            "skill_matches": {
                "Python": "matched",
                "FastAPI": "matched",
                "PostgreSQL": "matched",
                "REST API": "matched",
                "Docker": "matched",
                "AWS": "matched"
            }
        },
        {
            "id": "resume_002",
            "name": "Backend with RESTful",
            "content": """
Jane Doe
Backend Developer

Skills: Python, PostgreSQL, RESTful services, Docker

Experience:
- Backend Developer at DataFlow (2019-2023)
  - Developed RESTful web services using Python
  - Worked with PostgreSQL databases
  - Used Docker for containerization

Projects:
- API Gateway: Built RESTful services with Python Flask
- Data pipeline: PostgreSQL-based data processing
            """.strip(),
            "for_job": "jd_001",
            "relevance": "high",
            "skill_matches": {
                "Python": "matched",
                "FastAPI": "missing",
                "PostgreSQL": "matched",
                "REST API": "matched (as RESTful services)",
                "Docker": "matched",
                "AWS": "missing"
            }
        },
        {
            "id": "resume_003",
            "name": "Backend OOP Focus",
            "content": """
Bob Johnson
Software Engineer

Skills: Python, Object-Oriented Programming, PostgreSQL, REST API

Experience:
- Software Engineer at SoftSol (2021-present)
  - Developed Python applications using OOP principles
  - Built REST APIs
  - PostgreSQL database development

Projects:
- Library System: OOP-based Python application with REST API
- Inventory Management: PostgreSQL-backed REST services
            """.strip(),
            "for_job": "jd_001",
            "relevance": "high",
            "skill_matches": {
                "Python": "matched",
                "FastAPI": "missing",
                "PostgreSQL": "matched",
                "REST API": "matched",
                "Docker": "missing",
                "AWS": "missing"
            }
        },
        # JD_001 - Moderate matches
        {
            "id": "resume_004",
            "name": "Backend Partial Match",
            "content": """
Alice Brown
Python Developer

Skills: Python, Django, PostgreSQL

Experience:
- Python Developer at WebCo (2020-2022)
  - Built Django web applications
  - PostgreSQL database work
  - REST API development using Django REST framework

Projects:
- Blog platform: Django-based with PostgreSQL
            """.strip(),
            "for_job": "jd_001",
            "relevance": "medium",
            "skill_matches": {
                "Python": "matched",
                "FastAPI": "missing",
                "PostgreSQL": "matched",
                "REST API": "matched",
                "Docker": "missing",
                "AWS": "missing"
            }
        },
        {
            "id": "resume_005",
            "name": "Backend SQL Only",
            "content": """
Charlie Davis
Database Developer

Skills: SQL, PostgreSQL, MySQL

Experience:
- Database Developer at DataCorp (2019-present)
  - SQL query optimization
  - PostgreSQL administration
  - MySQL database management

Projects:
- Data warehouse: PostgreSQL-based
- Migration tool: SQL-based data migration
            """.strip(),
            "for_job": "jd_001",
            "relevance": "medium",
            "skill_matches": {
                "Python": "missing",
                "FastAPI": "missing",
                "PostgreSQL": "matched",
                "REST API": "missing",
                "Docker": "missing",
                "AWS": "missing"
            }
        },
        # JD_001 - Weak matches
        {
            "id": "resume_006",
            "name": "Backend Weak Match",
            "content": """
Eve Wilson
Junior Developer

Skills: Python, HTML, CSS

Experience:
- Junior Developer at Startup (2022-present)
  - Basic Python scripting
  - Frontend development with HTML/CSS
  - Learning web development

Projects:
- Personal website: HTML/CSS with Python backend
            """.strip(),
            "for_job": "jd_001",
            "relevance": "low",
            "skill_matches": {
                "Python": "matched",
                "FastAPI": "missing",
                "PostgreSQL": "missing",
                "REST API": "missing",
                "Docker": "missing",
                "AWS": "missing"
            }
        },
        # JD_001 - Irrelevant
        {
            "id": "resume_007",
            "name": "Frontend Developer",
            "content": """
Frank Miller
Frontend Developer

Skills: React, JavaScript, TypeScript, CSS

Experience:
- Frontend Developer at WebAgency (2020-present)
  - React application development
  - TypeScript implementation
  - UI/UX design

Projects:
- E-commerce frontend: React-based
- Dashboard: TypeScript and React
            """.strip(),
            "for_job": "jd_001",
            "relevance": "low",
            "skill_matches": {
                "Python": "missing",
                "FastAPI": "missing",
                "PostgreSQL": "missing",
                "REST API": "missing",
                "Docker": "missing",
                "AWS": "missing"
            }
        },
        # JD_001 - Keyword stuffing
        {
            "id": "resume_008",
            "name": "Keyword Stuffer",
            "content": """
Grace Lee
Developer

Skills: Python, FastAPI, PostgreSQL, REST API, Docker, AWS, Kubernetes, TensorFlow, PyTorch, React, Angular, Vue.js, MongoDB, Redis, GraphQL, Jenkins, Git, Linux, Ansible, Terraform, Prometheus, Grafana, Elasticsearch, Kafka, Spark, Hadoop, Scala, Go, Rust, Java, C++, C#, Ruby, PHP, Swift, Kotlin, Flutter, Dart, Unity, Unreal Engine, Blender, Photoshop, Figma, Sketch, Adobe XD

Experience:
- Junior Developer at TechStartup (2023-present)
  - Learning Python
  - Basic web development

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
            }
        },
        # JD_002 (Full Stack) - Strong match
        {
            "id": "resume_009",
            "content": """
Henry Clark
Full Stack Developer

Skills: React, Node.js, TypeScript, MongoDB, GraphQL, Docker

Experience:
- Full Stack Developer at FullStackCo (2020-present)
  - React frontend development with TypeScript
  - Node.js backend APIs
  - MongoDB database design
  - GraphQL API implementation
  - Docker containerization

Projects:
- Social media app: React, Node.js, MongoDB stack
- E-commerce platform: GraphQL API with React frontend
            """.strip(),
            "for_job": "jd_002",
            "relevance": "high",
            "skill_matches": {
                "React": "matched",
                "Node.js": "matched",
                "TypeScript": "matched",
                "MongoDB": "matched",
                "GraphQL": "matched",
                "AWS": "missing",
                "Docker": "matched"
            }
        },
        # JD_002 - Moderate match
        {
            "id": "resume_010",
            "content": """
Ivy Chen
Web Developer

Skills: React, JavaScript, Node.js, MongoDB

Experience:
- Web Developer at WebDev (2021-present)
  - React application development
  - Node.js backend
  - MongoDB integration

Projects:
- Task manager: React and Node.js with MongoDB
            """.strip(),
            "for_job": "jd_002",
            "relevance": "medium",
            "skill_matches": {
                "React": "matched",
                "Node.js": "matched",
                "TypeScript": "missing",
                "MongoDB": "matched",
                "GraphQL": "missing",
                "AWS": "missing",
                "Docker": "missing"
            }
        },
        # JD_003 (ML Engineer) - Strong match
        {
            "id": "resume_011",
            "content": """
Jack Robinson
Machine Learning Engineer

Skills: Python, TensorFlow, scikit-learn, SQL, PyTorch, AWS SageMaker

Experience:
- ML Engineer at MLCorp (2020-present)
  - Built production ML models using TensorFlow
  - Data preprocessing with scikit-learn
  - SQL for data extraction
  - PyTorch for research projects
  - Deployed models on AWS SageMaker

Projects:
- Fraud detection: TensorFlow-based model with SQL data pipeline
- Recommendation system: scikit-learn with PyTorch neural networks
            """.strip(),
            "for_job": "jd_003",
            "relevance": "high",
            "skill_matches": {
                "Python": "matched",
                "TensorFlow": "matched",
                "scikit-learn": "matched",
                "SQL": "matched",
                "PyTorch": "matched",
                "AWS SageMaker": "matched",
                "Docker": "missing"
            }
        },
        # JD_003 - Moderate match
        {
            "id": "resume_012",
            "content": """
Kate Anderson
Data Scientist

Skills: Python, scikit-learn, SQL, Pandas, NumPy

Experience:
- Data Scientist at DataSci (2021-present)
  - Machine learning models with scikit-learn
  - SQL data analysis
  - Data manipulation with Pandas

Projects:
- Customer churn prediction: scikit-learn with SQL data
- Sales forecasting: Python-based ML models
            """.strip(),
            "for_job": "jd_003",
            "relevance": "medium",
            "skill_matches": {
                "Python": "matched",
                "TensorFlow": "missing",
                "scikit-learn": "matched",
                "SQL": "matched",
                "PyTorch": "missing",
                "AWS SageMaker": "missing",
                "Docker": "missing"
            }
        },
        # JD_004 (DevOps) - Strong match
        {
            "id": "resume_013",
            "content": """
Leo Martinez
DevOps Engineer

Skills: Docker, Kubernetes, AWS, CI/CD, Terraform, Ansible, Linux

Experience:
- DevOps Engineer at CloudOps (2020-present)
  - Container orchestration with Kubernetes
  - Docker containerization
  - AWS infrastructure management
  - CI/CD pipeline setup with Jenkins
  - Infrastructure as Code with Terraform
  - Configuration management with Ansible
  - Linux system administration

Projects:
- Infrastructure migration: AWS with Kubernetes and Terraform
- CI/CD pipeline: Docker-based deployment automation
            """.strip(),
            "for_job": "jd_004",
            "relevance": "high",
            "skill_matches": {
                "Docker": "matched",
                "Kubernetes": "matched",
                "AWS": "matched",
                "CI/CD": "matched",
                "Terraform": "matched",
                "Ansible": "matched",
                "Linux": "matched"
            }
        },
        # JD_004 - Moderate match
        {
            "id": "resume_014",
            "content": """
Mia Thompson
System Administrator

Skills: Linux, Docker, AWS, Jenkins

Experience:
- System Administrator at SysAdmin (2021-present)
  - Linux server administration
  - Docker container deployment
  - AWS cloud management
  - Jenkins CI/CD setup

Projects:
- Server migration: Linux to AWS with Docker
            """.strip(),
            "for_job": "jd_004",
            "relevance": "medium",
            "skill_matches": {
                "Docker": "matched",
                "Kubernetes": "missing",
                "AWS": "matched",
                "CI/CD": "matched",
                "Terraform": "missing",
                "Ansible": "missing",
                "Linux": "matched"
            }
        },
        # JD_005 (Data Engineer) - Strong match
        {
            "id": "resume_015",
            "content": """
Nathan White
Data Engineer

Skills: Python, SQL, Apache Spark, PostgreSQL, Airflow, AWS, Docker

Experience:
- Data Engineer at DataEng (2020-present)
  - ETL pipeline development with Apache Spark
  - SQL data extraction and transformation
  - PostgreSQL data warehousing
  - Airflow workflow orchestration
  - AWS data platform
  - Docker for pipeline containerization

Projects:
- Real-time analytics: Apache Spark with Airflow on AWS
- Data warehouse: PostgreSQL-based with Airflow ETL
            """.strip(),
            "for_job": "jd_005",
            "relevance": "high",
            "skill_matches": {
                "Python": "matched",
                "SQL": "matched",
                "Apache Spark": "matched",
                "PostgreSQL": "matched",
                "Airflow": "matched",
                "AWS": "matched",
                "Docker": "matched"
            }
        },
        # JD_005 - Moderate match
        {
            "id": "resume_016",
            "content": """
Olivia Harris
Data Analyst

Skills: Python, SQL, PostgreSQL, Pandas

Experience:
- Data Analyst at DataAnalyst (2021-present)
  - SQL data analysis
  - PostgreSQL database queries
  - Python data processing with Pandas

Projects:
- Sales dashboard: SQL-based with PostgreSQL
- Customer analytics: Python with Pandas
            """.strip(),
            "for_job": "jd_005",
            "relevance": "medium",
            "skill_matches": {
                "Python": "matched",
                "SQL": "matched",
                "Apache Spark": "missing",
                "PostgreSQL": "matched",
                "Airflow": "missing",
                "AWS": "missing",
                "Docker": "missing"
            }
        },
        # Additional resumes for JD_001 to reach 30 total
        {
            "id": "resume_017",
            "content": """
Peter Garcia
Software Developer

Skills: Java, Spring Boot, MySQL

Experience:
- Java Developer at JavaCo (2020-present)
  - Spring Boot application development
  - MySQL database work

Projects:
- Banking system: Java Spring Boot with MySQL
            """.strip(),
            "for_job": "jd_001",
            "relevance": "low",
            "skill_matches": {
                "Python": "missing",
                "FastAPI": "missing",
                "PostgreSQL": "missing",
                "REST API": "missing",
                "Docker": "missing",
                "AWS": "missing"
            }
        },
        {
            "id": "resume_018",
            "content": """
Quinn Roberts
Python Developer

Skills: Python, Flask, SQLite

Experience:
- Python Developer at PyDev (2022-present)
  - Flask web applications
  - SQLite database

Projects:
- Todo app: Flask with SQLite
            """.strip(),
            "for_job": "jd_001",
            "relevance": "medium",
            "skill_matches": {
                "Python": "matched",
                "FastAPI": "missing",
                "PostgreSQL": "missing",
                "REST API": "matched",
                "Docker": "missing",
                "AWS": "missing"
            }
        },
        {
            "id": "resume_019",
            "content": """
Rachel Kim
Backend Developer

Skills: Python, Django, PostgreSQL, Docker

Experience:
- Backend Developer at BackEndCo (2021-present)
  - Django REST framework
  - PostgreSQL databases
  - Docker deployment

Projects:
- API platform: Django REST with PostgreSQL
            """.strip(),
            "for_job": "jd_001",
            "relevance": "medium",
            "skill_matches": {
                "Python": "matched",
                "FastAPI": "missing",
                "PostgreSQL": "matched",
                "REST API": "matched",
                "Docker": "matched",
                "AWS": "missing"
            }
        },
        {
            "id": "resume_020",
            "content": """
Sam Lewis
Full Stack Developer

Skills: JavaScript, Node.js, MongoDB, React

Experience:
- Full Stack Developer at FullStack (2020-present)
  - Node.js backend
  - MongoDB database
  - React frontend

Projects:
- Social app: MERN stack
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
            }
        },
        {
            "id": "resume_021",
            "content": """
Tina Walker
Data Scientist

Skills: Python, R, SQL, Machine Learning

Experience:
- Data Scientist at DataSciCo (2020-present)
  - Python and R for data analysis
  - SQL queries
  - Machine learning models

Projects:
- Predictive analytics: Python ML models
            """.strip(),
            "for_job": "jd_001",
            "relevance": "low",
            "skill_matches": {
                "Python": "matched",
                "FastAPI": "missing",
                "PostgreSQL": "missing",
                "REST API": "missing",
                "Docker": "missing",
                "AWS": "missing"
            }
        },
        {
            "id": "resume_022",
            "content": """
Umar Hall
Cloud Engineer

Skills: AWS, Docker, Kubernetes, Terraform

Experience:
- Cloud Engineer at CloudEng (2021-present)
  - AWS infrastructure
  - Kubernetes orchestration
  - Terraform IaC

Projects:
- Cloud migration: AWS with Kubernetes
            """.strip(),
            "for_job": "jd_001",
            "relevance": "low",
            "skill_matches": {
                "Python": "missing",
                "FastAPI": "missing",
                "PostgreSQL": "missing",
                "REST API": "missing",
                "Docker": "matched",
                "AWS": "matched"
            }
        },
        {
            "id": "resume_023",
            "content": """
Victoria Young
Software Engineer

Skills: C++, Python, SQL

Experience:
- Software Engineer at SoftEng (2020-present)
  - C++ application development
  - Python scripting
  - SQL database work

Projects:
- Performance tool: C++ with Python and SQL
            """.strip(),
            "for_job": "jd_001",
            "relevance": "low",
            "skill_matches": {
                "Python": "matched",
                "FastAPI": "missing",
                "PostgreSQL": "missing",
                "REST API": "missing",
                "Docker": "missing",
                "AWS": "missing"
            }
        },
        {
            "id": "resume_024",
            "content": """
William King
Backend Developer

Skills: Python, FastAPI, MongoDB, REST API

Experience:
- Backend Developer at BackDev (2022-present)
  - FastAPI development
  - MongoDB database
  - REST API design

Projects:
- User service: FastAPI with MongoDB
            """.strip(),
            "for_job": "jd_001",
            "relevance": "medium",
            "skill_matches": {
                "Python": "matched",
                "FastAPI": "matched",
                "PostgreSQL": "missing",
                "REST API": "matched",
                "Docker": "missing",
                "AWS": "missing"
            }
        },
        {
            "id": "resume_025",
            "content": """
Xavier Scott
DevOps Engineer

Skills: Docker, Kubernetes, CI/CD, Linux

Experience:
- DevOps Engineer at DevOpsCo (2021-present)
  - Docker containers
  - Kubernetes clusters
  - CI/CD pipelines
  - Linux administration

Projects:
- Deployment pipeline: Docker and Kubernetes CI/CD
            """.strip(),
            "for_job": "jd_001",
            "relevance": "low",
            "skill_matches": {
                "Python": "missing",
                "FastAPI": "missing",
                "PostgreSQL": "missing",
                "REST API": "missing",
                "Docker": "matched",
                "AWS": "missing"
            }
        },
        {
            "id": "resume_026",
            "content": """
Yara Green
Python Developer

Skills: Python, Django, PostgreSQL

Experience:
- Python Developer at PyCo (2020-present)
  - Django web development
  - PostgreSQL databases

Projects:
- CMS platform: Django with PostgreSQL
            """.strip(),
            "for_job": "jd_001",
            "relevance": "medium",
            "skill_matches": {
                "Python": "matched",
                "FastAPI": "missing",
                "PostgreSQL": "matched",
                "REST API": "matched",
                "Docker": "missing",
                "AWS": "missing"
            }
        },
        {
            "id": "resume_027",
            "content": """
Zach Adams
Software Engineer

Skills: Java, Spring, SQL

Experience:
- Software Engineer at SoftCo (2021-present)
  - Java Spring applications
  - SQL databases

Projects:
- Enterprise app: Java Spring with SQL
            """.strip(),
            "for_job": "jd_001",
            "relevance": "low",
            "skill_matches": {
                "Python": "missing",
                "FastAPI": "missing",
                "PostgreSQL": "missing",
                "REST API": "missing",
                "Docker": "missing",
                "AWS": "missing"
            }
        },
        {
            "id": "resume_028",
            "content": """
Amy Nelson
Full Stack Developer

Skills: Python, JavaScript, React, PostgreSQL

Experience:
- Full Stack Developer at FullStack (2020-present)
  - React frontend
  - Python backend
  - PostgreSQL database

Projects:
- Web application: React, Python, PostgreSQL
            """.strip(),
            "for_job": "jd_001",
            "relevance": "medium",
            "skill_matches": {
                "Python": "matched",
                "FastAPI": "missing",
                "PostgreSQL": "matched",
                "REST API": "matched",
                "Docker": "missing",
                "AWS": "missing"
            }
        },
        {
            "id": "resume_029",
            "content": """
Brian Hill
Backend Developer

Skills: Python, FastAPI, PostgreSQL, Docker, AWS

Experience:
- Backend Developer at BackEnd (2021-present)
  - FastAPI API development
  - PostgreSQL databases
  - Docker deployment
  - AWS hosting

Projects:
- SaaS platform: FastAPI with PostgreSQL on AWS
            """.strip(),
            "for_job": "jd_001",
            "relevance": "high",
            "skill_matches": {
                "Python": "matched",
                "FastAPI": "matched",
                "PostgreSQL": "matched",
                "REST API": "matched",
                "Docker": "matched",
                "AWS": "matched"
            }
        },
        {
            "id": "resume_030",
            "content": """
Carol Baker
Data Engineer

Skills: Python, SQL, Spark, Airflow

Experience:
- Data Engineer at DataEng (2020-present)
  - Spark data processing
  - SQL queries
  - Airflow workflows

Projects:
- Data pipeline: Spark with Airflow
            """.strip(),
            "for_job": "jd_001",
            "relevance": "low",
            "skill_matches": {
                "Python": "matched",
                "FastAPI": "missing",
                "PostgreSQL": "missing",
                "REST API": "missing",
                "Docker": "missing",
                "AWS": "missing"
            }
        }
    ]
}
