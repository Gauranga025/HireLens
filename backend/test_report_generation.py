import requests

resume_id = "e3357f64-3994-4ef3-87b5-b25273568f10"
job_id = "960bdb94-c807-407f-b86d-002c1b82215a"

# Test JSON report generation
url = f"http://127.0.0.1:8000/api/v1/reports/generate?job_id={job_id}&resume_id={resume_id}&format=json"

response = requests.post(url)

print(f"Response status: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    print(f"PASS: Report generation successful")
    print(f"Report ID: {data.get('report_id', 'N/A')}")
    print(f"Format: {data.get('format', 'N/A')}")
    print(f"Content length: {len(data.get('content', ''))} characters")
    
    # Parse content if it's JSON
    content = data.get('content', '')
    if content:
        print(f"\nFirst 500 characters of content:")
        print(content[:500])
else:
    print(f"FAIL: HTTP {response.status_code}")
    print(f"Response: {response.text}")

# Test CSV report generation
url_csv = f"http://127.0.0.1:8000/api/v1/reports/generate?job_id={job_id}&resume_id={resume_id}&format=csv"

response_csv = requests.post(url_csv)

print(f"\nCSV Response status: {response_csv.status_code}")

if response_csv.status_code == 200:
    data_csv = response_csv.json()
    print(f"PASS: CSV report generation successful")
    print(f"Format: {data_csv.get('format', 'N/A')}")
    print(f"Content length: {len(data_csv.get('content', ''))} characters")
    
    content_csv = data_csv.get('content', '')
    if content_csv:
        print(f"\nFirst 500 characters of CSV content:")
        print(content_csv[:500])
else:
    print(f"FAIL: CSV HTTP {response_csv.status_code}")
    print(f"Response: {response_csv.text}")
