import requests

resume_id = "e3357f64-3994-4ef3-87b5-b25273568f10"

url = f"http://127.0.0.1:8000/api/v1/resumes/{resume_id}"

response = requests.get(url)

print(f"Response status: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    print(f"PASS: Resume retrieved successfully")
    print(f"Resume ID: {data['resume_id']}")
    print(f"Filename: {data['filename']}")
    print(f"Candidate Name: {data['candidate_info']['name']}")
    print(f"Email: {data['candidate_info']['email']}")
    print(f"Skills: {data['candidate_info']['skills']}")
    print(f"Extraction source format: {data['extraction']['source_format']}")
    print(f"Extracted text length: {len(data['extraction']['text'])} characters")
else:
    print(f"FAIL: HTTP {response.status_code}")
    print(f"Response: {response.text}")
