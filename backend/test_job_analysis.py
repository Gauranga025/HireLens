import requests

job_description = """
Backend Software Engineer

Required Skills:
- Python
- FastAPI
- SQLAlchemy
- PostgreSQL
- REST APIs
- Object-Oriented Programming
- Data Structures and Algorithms

Preferred Skills:
- Docker
- AWS
- Kubernetes
- Redis
- Microservices
- CI/CD
"""

url = "http://127.0.0.1:8000/api/v1/jobs/analyze"
payload = {"job_description": job_description}

response = requests.post(url, json=payload)

print(f"Response status: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    print(f"PASS: Job analysis successful")
    print(f"Job ID: {data['job_id']}")
    print(f"\nTitle: {data['analysis']['title']}")
    print(f"\nRequired Skills ({len(data['analysis']['required_skills'])}):")
    for skill in data['analysis']['required_skills']:
        print(f"  - {skill}")
    print(f"\nPreferred Skills ({len(data['analysis']['preferred_skills'])}):")
    for skill in data['analysis']['preferred_skills']:
        print(f"  - {skill}")
    print(f"\nQualifications: {data['analysis']['qualifications']}")
    print(f"Experience: {data['analysis']['experience_required']}")
    
    # Verify no mixing
    required_set = set(data['analysis']['required_skills'])
    preferred_set = set(data['analysis']['preferred_skills'])
    overlap = required_set.intersection(preferred_set)
    if overlap:
        print(f"\nWARNING: Skills in both required and preferred: {overlap}")
    else:
        print(f"\nPASS: No mixing between required and preferred skills")
        
    # Verify no empty lists
    if not data['analysis']['required_skills']:
        print(f"\nFAIL: Required skills list is empty")
    else:
        print(f"\nPASS: Required skills list is not empty")
        
    if not data['analysis']['preferred_skills']:
        print(f"WARNING: Preferred skills list is empty (may be expected)")
    else:
        print(f"PASS: Preferred skills list is not empty")
        
    # Save job ID for matching test
    print(f"\nJob ID for matching: {data['job_id']}")
    
else:
    print(f"FAIL: HTTP {response.status_code}")
    print(f"Response: {response.text}")
