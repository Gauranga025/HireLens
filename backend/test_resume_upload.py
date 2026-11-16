import requests
import os

# Use an existing PDF file
pdf_path = r"f:\Nityananda\Projects\ResumeParser\intern\backend\storage\uploads\04c89079-e3fd-49c7-acda-39ce71ce7f36.pdf"

if not os.path.exists(pdf_path):
    print(f"FAIL: PDF file not found: {pdf_path}")
else:
    print(f"PASS: PDF file exists: {pdf_path}")
    
    # Try to read and validate the PDF
    try:
        with open(pdf_path, 'rb') as f:
            content = f.read()
        print(f"PASS: PDF file size: {len(content)} bytes")
        
        # Try uploading
        url = "http://127.0.0.1:8000/api/v1/resumes/upload"
        files = {"files": ("test_resume.pdf", content, "application/pdf")}
        
        response = requests.post(url, files=files)
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            if data["successful"] > 0:
                print(f"PASS: Resume uploaded successfully")
                print(f"Resume ID: {data['results'][0]['resume_id']}")
            else:
                print(f"FAIL: Upload failed")
                print(f"Error: {data['results'][0].get('error', 'Unknown')}")
        else:
            print(f"FAIL: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"FAIL: Exception during upload: {e}")
        import traceback
        traceback.print_exc()
