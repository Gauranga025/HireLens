import io
from typing import AsyncGenerator

import pytest
from httpx import AsyncClient

try:
    import pymupdf as fitz
    import docx
    HAS_PARSING = True
except ImportError:
    HAS_PARSING = False


@pytest.fixture
async def client(disposable_api_client) -> AsyncGenerator[AsyncClient, None]:
    """ASGI client backed by the disposable, rollback-only test database."""
    yield disposable_api_client


def _create_sample_pdf(content: str = "Test resume content") -> bytes:
    if not HAS_PARSING:
        return b"mock pdf content"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), content)
    pdf_bytes: bytes = doc.write()
    doc.close()
    return pdf_bytes


def _create_sample_docx(content: str = "Test resume content") -> bytes:
    if not HAS_PARSING:
        return b"PK\x03\x04 mock docx"
    doc = docx.Document()
    doc.add_paragraph(content)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


@pytest.mark.skipif(not HAS_PARSING, reason="Document parsing libraries not installed")
@pytest.mark.asyncio
async def test_single_pdf_upload(client: AsyncClient) -> None:
    """Test uploading a single PDF file."""
    pdf_content = _create_sample_pdf("Arjun Sharma\narjun@example.com\nPython Developer")
    files = {"files": ("resume.pdf", pdf_content, "application/pdf")}

    response = await client.post("/api/v1/resumes/upload", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["total_files"] == 1
    assert data["successful"] == 1
    assert data["failed"] == 0
    assert len(data["results"]) == 1
    assert data["results"][0]["status"] == "success"
    assert data["results"][0]["resume_id"]
    assert data["results"][0]["filename"] == "resume.pdf"


@pytest.mark.skipif(not HAS_PARSING, reason="Document parsing libraries not installed")
@pytest.mark.asyncio
async def test_multiple_files_upload(client: AsyncClient) -> None:
    """Test uploading multiple PDF and DOCX files."""
    pdf_content = _create_sample_pdf("Candidate 1\nPython Developer")
    docx_content = _create_sample_docx("Candidate 2\nJava Developer")
    
    files = [
        ("files", ("resume1.pdf", pdf_content, "application/pdf")),
        ("files", ("resume2.docx", docx_content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
    ]

    response = await client.post("/api/v1/resumes/upload", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["total_files"] == 2
    assert data["successful"] == 2
    assert data["failed"] == 0
    assert len(data["results"]) == 2


@pytest.mark.asyncio
async def test_unsupported_file_extension(client: AsyncClient) -> None:
    """Test uploading an unsupported file type."""
    files = {"files": ("resume.txt", b"Plain text resume", "text/plain")}

    response = await client.post("/api/v1/resumes/upload", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["total_files"] == 1
    assert data["successful"] == 0
    assert data["failed"] == 1
    assert data["results"][0]["status"] == "error"
    assert "unsupported" in data["results"][0]["error"].lower()


@pytest.mark.asyncio
async def test_empty_file(client: AsyncClient) -> None:
    """Test uploading an empty file."""
    files = {"files": ("empty.pdf", b"", "application/pdf")}

    response = await client.post("/api/v1/resumes/upload", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["total_files"] == 1
    assert data["successful"] == 0
    assert data["failed"] == 1
    assert data["results"][0]["status"] == "error"
    assert "empty" in data["results"][0]["error"].lower()


@pytest.mark.skipif(not HAS_PARSING, reason="Document parsing libraries not installed")
@pytest.mark.asyncio
async def test_invalid_document_handling(client: AsyncClient) -> None:
    """Test handling of corrupted/invalid document."""
    corrupt_pdf = b"Not a real PDF"
    files = {"files": ("corrupt.pdf", corrupt_pdf, "application/pdf")}

    response = await client.post("/api/v1/resumes/upload", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["total_files"] == 1
    assert data["successful"] == 0
    assert data["failed"] == 1
    assert data["results"][0]["status"] == "error"


@pytest.mark.skipif(not HAS_PARSING, reason="Document parsing libraries not installed")
@pytest.mark.asyncio
async def test_one_failed_file_does_not_stop_others(client: AsyncClient) -> None:
    """Test that one invalid file doesn't prevent processing of valid files."""
    valid_pdf = _create_sample_pdf("Valid Candidate\nPython Developer")
    corrupt_pdf = b"Not a real PDF"
    
    files = [
        ("files", ("valid.pdf", valid_pdf, "application/pdf")),
        ("files", ("corrupt.pdf", corrupt_pdf, "application/pdf")),
    ]

    response = await client.post("/api/v1/resumes/upload", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["total_files"] == 2
    assert data["successful"] == 1
    assert data["failed"] == 1


@pytest.mark.skipif(not HAS_PARSING, reason="Document parsing libraries not installed")
@pytest.mark.asyncio
async def test_resume_retrieve(client: AsyncClient) -> None:
    """Test retrieving a processed resume by ID."""
    pdf_content = _create_sample_pdf("Arjun Sharma\narjun@example.com\nPython Developer")
    files = {"files": ("resume.pdf", pdf_content, "application/pdf")}

    upload_response = await client.post("/api/v1/resumes/upload", files=files)
    resume_id = upload_response.json()["results"][0]["resume_id"]

    retrieve_response = await client.get(f"/api/v1/resumes/{resume_id}")

    assert retrieve_response.status_code == 200
    data = retrieve_response.json()
    assert data["resume_id"] == resume_id
    assert data["filename"] == "resume.pdf"
    assert "extraction" in data
    assert "candidate_info" in data


@pytest.mark.asyncio
async def test_resume_retrieve_not_found(client: AsyncClient) -> None:
    """Test retrieving a non-existent resume."""
    response = await client.get("/api/v1/resumes/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_resume_retrieve_invalid_id(client: AsyncClient) -> None:
    """Test retrieving a resume with invalid ID format."""
    response = await client.get("/api/v1/resumes/invalid-uuid-format")

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_job_analysis(client: AsyncClient) -> None:
    """Test analyzing a job description."""
    job_description = """
    Senior Python Developer
    
    Required Skills:
    - Python
    - Django
    - PostgreSQL
    
    Experience: 5+ years
    """

    response = await client.post(
        "/api/v1/jobs/analyze",
        json={"job_description": job_description}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["job_id"]
    assert "analysis" in data
    assert data["analysis"]["title"]
    assert "required_skills" in data["analysis"]


@pytest.mark.asyncio
async def test_job_analysis_empty_input(client: AsyncClient) -> None:
    """Test job analysis with empty input."""
    response = await client.post(
        "/api/v1/jobs/analyze",
        json={"job_description": ""}
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_job_retrieve(client: AsyncClient) -> None:
    """Test retrieving an analyzed job by ID."""
    job_description = "Python Developer with Django experience"
    
    analyze_response = await client.post(
        "/api/v1/jobs/analyze",
        json={"job_description": job_description}
    )
    job_id = analyze_response.json()["job_id"]

    retrieve_response = await client.get(f"/api/v1/jobs/{job_id}")

    assert retrieve_response.status_code == 200
    data = retrieve_response.json()
    assert data["job_id"] == job_id
    assert "analysis" in data


@pytest.mark.asyncio
async def test_job_retrieve_not_found(client: AsyncClient) -> None:
    """Test retrieving a non-existent job."""
    response = await client.get("/api/v1/jobs/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_job_retrieve_invalid_id(client: AsyncClient) -> None:
    """Test retrieving a job with invalid ID format."""
    response = await client.get("/api/v1/jobs/invalid-uuid-format")

    assert response.status_code == 400


@pytest.mark.skipif(not HAS_PARSING, reason="Document parsing libraries not installed")
@pytest.mark.asyncio
async def test_matching_successful_candidates(client: AsyncClient) -> None:
    """Test matching resumes against a job."""
    job_description = "Python Developer with Django and PostgreSQL experience"
    
    job_response = await client.post(
        "/api/v1/jobs/analyze",
        json={"job_description": job_description}
    )
    job_id = job_response.json()["job_id"]

    pdf_content = _create_sample_pdf("Python Developer with Django and PostgreSQL skills")
    files = {"files": ("resume.pdf", pdf_content, "application/pdf")}
    
    resume_response = await client.post("/api/v1/resumes/upload", files=files)
    resume_id = resume_response.json()["results"][0]["resume_id"]

    match_response = await client.post(
        "/api/v1/matching/evaluate",
        json={"job_id": job_id, "resume_ids": [resume_id], "use_semantic": False}
    )

    assert match_response.status_code == 200
    data = match_response.json()
    assert data["job_id"] == job_id
    assert data["total_candidates"] == 1
    assert data["successful"] == 1
    assert data["failed"] == 0
    assert len(data["results"]) == 1
    assert data["results"][0]["resume_id"] == resume_id
    assert data["results"][0]["match_result"]["overall_score"] >= 0


@pytest.mark.asyncio
async def test_matching_missing_job_id(client: AsyncClient) -> None:
    """Test matching with a non-existent job ID."""
    response = await client.post(
        "/api/v1/matching/evaluate",
        json={"job_id": "00000000-0000-0000-0000-000000000000", "resume_ids": ["some-id"], "use_semantic": False}
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_matching_invalid_job_id(client: AsyncClient) -> None:
    """Test matching with invalid job ID format."""
    response = await client.post(
        "/api/v1/matching/evaluate",
        json={"job_id": "invalid-uuid", "resume_ids": ["some-id"], "use_semantic": False}
    )

    assert response.status_code == 400


@pytest.mark.skipif(not HAS_PARSING, reason="Document parsing libraries not installed")
@pytest.mark.asyncio
async def test_matching_missing_resume_id(client: AsyncClient) -> None:
    """Test matching with a non-existent resume ID."""
    job_description = "Python Developer"
    
    job_response = await client.post(
        "/api/v1/jobs/analyze",
        json={"job_description": job_description}
    )
    job_id = job_response.json()["job_id"]

    response = await client.post(
        "/api/v1/matching/evaluate",
        json={"job_id": job_id, "resume_ids": ["00000000-0000-0000-0000-000000000000"], "use_semantic": False}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_candidates"] == 1
    assert data["successful"] == 0
    assert data["failed"] == 1
    assert data["results"][0]["error"] == "Resume not found"


@pytest.mark.skipif(not HAS_PARSING, reason="Document parsing libraries not installed")
@pytest.mark.asyncio
async def test_multiple_candidate_ranking(client: AsyncClient) -> None:
    """Test that candidates are ranked by match score descending."""
    job_description = "Python Developer with Django and PostgreSQL"
    
    job_response = await client.post(
        "/api/v1/jobs/analyze",
        json={"job_description": job_description}
    )
    job_id = job_response.json()["job_id"]

    pdf1 = _create_sample_pdf("Python Developer with Django")
    pdf2 = _create_sample_pdf("Python Developer with Django and PostgreSQL and Docker")
    
    files = [
        ("files", ("resume1.pdf", pdf1, "application/pdf")),
        ("files", ("resume2.pdf", pdf2, "application/pdf")),
    ]
    
    resume_response = await client.post("/api/v1/resumes/upload", files=files)
    resume_ids = [r["resume_id"] for r in resume_response.json()["results"]]

    match_response = await client.post(
        "/api/v1/matching/evaluate",
        json={"job_id": job_id, "resume_ids": resume_ids, "use_semantic": False}
    )

    assert match_response.status_code == 200
    data = match_response.json()
    assert data["total_candidates"] == 2
    
    scores = [r["match_result"]["overall_score"] for r in data["results"]]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.skipif(not HAS_PARSING, reason="Document parsing libraries not installed")
@pytest.mark.asyncio
async def test_report_generation_json(client: AsyncClient) -> None:
    """Test generating a JSON report."""
    job_description = "Python Developer"
    
    job_response = await client.post(
        "/api/v1/jobs/analyze",
        json={"job_description": job_description}
    )
    job_id = job_response.json()["job_id"]

    pdf_content = _create_sample_pdf("Python Developer")
    files = {"files": ("resume.pdf", pdf_content, "application/pdf")}
    
    resume_response = await client.post("/api/v1/resumes/upload", files=files)
    resume_id = resume_response.json()["results"][0]["resume_id"]

    report_response = await client.post(
        f"/api/v1/reports/generate?format=json&job_id={job_id}&resume_id={resume_id}"
    )

    assert report_response.status_code == 200
    data = report_response.json()
    assert data["report_id"]
    assert data["format"] == "json"
    assert data["content"]


@pytest.mark.skipif(not HAS_PARSING, reason="Document parsing libraries not installed")
@pytest.mark.asyncio
async def test_report_generation_csv(client: AsyncClient) -> None:
    """Test generating a CSV report."""
    job_description = "Python Developer"
    
    job_response = await client.post(
        "/api/v1/jobs/analyze",
        json={"job_description": job_description}
    )
    job_id = job_response.json()["job_id"]

    pdf_content = _create_sample_pdf("Python Developer")
    files = {"files": ("resume.pdf", pdf_content, "application/pdf")}
    
    resume_response = await client.post("/api/v1/resumes/upload", files=files)
    resume_id = resume_response.json()["results"][0]["resume_id"]

    report_response = await client.post(
        f"/api/v1/reports/generate?format=csv&job_id={job_id}&resume_id={resume_id}"
    )

    assert report_response.status_code == 200
    data = report_response.json()
    assert data["report_id"]
    assert data["format"] == "csv"
    assert "Category,Metric / Field,Value" in data["content"]


@pytest.mark.asyncio
async def test_report_generation_invalid_format(client: AsyncClient) -> None:
    """Test report generation with invalid format."""
    response = await client.post(
        "/api/v1/reports/generate?format=xml&job_id=some-id&resume_id=some-id"
    )

    assert response.status_code == 400


@pytest.mark.skipif(not HAS_PARSING, reason="Document parsing libraries not installed")
@pytest.mark.asyncio
async def test_report_generation_invalid_job_id(client: AsyncClient) -> None:
    """Test report generation with invalid job ID format."""
    response = await client.post(
        "/api/v1/reports/generate?format=json&job_id=invalid-id&resume_id=some-id"
    )

    assert response.status_code == 400


@pytest.mark.skipif(not HAS_PARSING, reason="Document parsing libraries not installed")
@pytest.mark.asyncio
async def test_report_generation_invalid_resume_id(client: AsyncClient) -> None:
    """Test report generation with invalid resume ID format."""
    response = await client.post(
        "/api/v1/reports/generate?format=json&job_id=some-id&resume_id=invalid-id"
    )

    assert response.status_code == 400


@pytest.mark.skipif(not HAS_PARSING, reason="Document parsing libraries not installed")
@pytest.mark.asyncio
async def test_report_retrieve(client: AsyncClient) -> None:
    """Test retrieving a generated report."""
    job_description = "Python Developer"
    
    job_response = await client.post(
        "/api/v1/jobs/analyze",
        json={"job_description": job_description}
    )
    job_id = job_response.json()["job_id"]

    pdf_content = _create_sample_pdf("Python Developer")
    files = {"files": ("resume.pdf", pdf_content, "application/pdf")}
    
    resume_response = await client.post("/api/v1/resumes/upload", files=files)
    resume_id = resume_response.json()["results"][0]["resume_id"]

    generate_response = await client.post(
        f"/api/v1/reports/generate?format=json&job_id={job_id}&resume_id={resume_id}"
    )
    report_id = generate_response.json()["report_id"]

    retrieve_response = await client.get(f"/api/v1/reports/{report_id}")

    assert retrieve_response.status_code == 200
    data = retrieve_response.json()
    assert data["report_id"] == report_id


@pytest.mark.asyncio
async def test_report_retrieve_not_found(client: AsyncClient) -> None:
    """Test retrieving a non-existent report."""
    response = await client.get("/api/v1/reports/nonexistent-id")

    assert response.status_code == 404
