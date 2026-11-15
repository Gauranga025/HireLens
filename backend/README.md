# AI Resume Screening Backend

FastAPI-based backend for AI-powered resume parsing and job matching.

## Prerequisites

- Python 3.10 or higher
- Windows, macOS, or Linux

## Setup Instructions

### 1. Create Virtual Environment (Windows)

```powershell
# Navigate to the backend directory
cd backend

# Create virtual environment
python -m venv .venv

# Activate virtual environment
.venv\Scripts\activate
```

### 2. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 3. Run the Backend

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### 4. Access API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Environment Variables

Create a `.env` file in the backend directory to override default settings:

```env
APP_NAME=AI Resume Screening Backend
APP_VERSION=0.1.0
DEBUG=false
API_PREFIX=/api/v1
CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]
```

## Running Tests

```powershell
# From project root (not backend directory)
$env:PYTHONPATH="backend"; .venv\Scripts\python -m pytest backend/tests/ -v

# Run specific test file
$env:PYTHONPATH="backend"; .venv\Scripts\python -m pytest backend/tests/test_document_service.py -v

# Run tests without semantic matching (if torch DLL issues occur)
$env:PYTHONPATH="backend"; .venv\Scripts\python -m pytest backend/tests/test_document_service.py backend/tests/test_resume_parser_service.py backend/tests/test_matching_service.py::test_tfidf_similarity_identical backend/tests/test_matching_service.py::test_compute_match_without_semantic -v
```

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── api/
│   │   └── routes/          # API route handlers
│   ├── core/
│   │   ├── config.py        # Configuration management
│   │   └── exceptions.py    # Custom exceptions
│   ├── models/              # SQLAlchemy models (future)
│   ├── schemas/             # Pydantic schemas
│   ├── services/            # Business logic services
│   │   ├── document_service.py      # PDF/DOCX text extraction
│   │   ├── resume_parser_service.py # Resume information extraction
│   │   ├── skill_service.py         # Skill extraction and matching
│   │   ├── job_analysis_service.py  # Job description analysis
│   │   ├── matching_service.py      # Resume-job matching algorithms
│   │   └── report_service.py        # Report generation (JSON/CSV)
│   ├── utils/
│   │   └── text_processor.py        # Text preprocessing utilities
│   └── data/
│       └── skills.json              # Skills database for extraction
├── tests/                   # Test suite
│   ├── test_main.py         # FastAPI app tests
│   ├── test_config.py       # Configuration tests
│   ├── test_schemas.py      # Pydantic schema tests
│   ├── test_document_service.py     # Document extraction tests
│   ├── test_resume_parser_service.py # Resume parsing tests
│   ├── test_matching_service.py     # Matching algorithm tests
│   └── test_bug_fixes.py            # Regression tests for bug fixes
└── requirements.txt         # Python dependencies
```

## AI Processing Pipeline

The backend implements the following AI processing pipeline:

1. **Document Extraction** (`document_service.py`)
   - Extracts text from PDF and DOCX files
   - Detects scanned documents
   - Validates file size and format

2. **Resume Parsing** (`resume_parser_service.py`)
   - Extracts candidate name, email, phone
   - Parses education, experience, certifications, projects
   - Uses regex patterns and heuristics

3. **Skill Extraction** (`skill_service.py`)
   - Matches skills against a curated database
   - Separates technical and soft skills
   - Normalizes skill names for matching

4. **Job Analysis** (`job_analysis_service.py`)
   - Extracts job title and requirements
   - Identifies required vs preferred skills
   - Parses experience requirements

5. **Matching** (`matching_service.py`)
   - TF-IDF keyword similarity (lexical matching)
   - Semantic similarity using sentence-transformers (contextual matching)
   - Skill-based matching with percentage calculation
   - Weighted overall score (30% TF-IDF, 40% semantic, 30% skills when available)
   - Fallback to 50% TF-IDF + 50% skills when semantic unavailable

6. **Report Generation** (`report_service.py`)
   - Generates JSON and CSV reports
   - Provides improvement suggestions
   - Includes match summary and detailed breakdown

## Service Responsibilities

- **document_service.py**: Handles file validation and text extraction from PDF/DOCX
- **resume_parser_service.py**: Extracts structured information from resume text
- **skill_service.py**: Extracts and matches skills against requirements
- **job_analysis_service.py**: Analyzes job descriptions for requirements
- **matching_service.py**: Computes similarity scores between resumes and jobs
- **report_service.py**: Generates structured reports with recommendations
- **text_processor.py**: Provides text normalization and preprocessing utilities

## Dependencies

### Web Framework
- fastapi>=0.104.0
- uvicorn[standard]>=0.24.0

### Data Validation
- pydantic>=2.5.0
- pydantic-settings>=2.1.0

### Document Parsing
- PyMuPDF==1.24.10 (PDF text extraction)
- python-docx==1.1.2 (DOCX text extraction)

### Machine Learning / NLP
- sentence-transformers==2.2.2 (Semantic similarity)
- scikit-learn==1.3.2 (TF-IDF vectorization)
- numpy==1.24.4 (Numerical operations)
- torch>=1.6.0 (Required by sentence-transformers)

### Testing
- pytest==8.3.3
- httpx>=0.25.0

## Model Download and Caching

The `sentence-transformers` library automatically downloads the `all-MiniLM-L6-v2` model on first use:

- Model size: ~120MB
- Download location: User's cache directory (e.g., `~/.cache/torch/sentence_transformers/`)
- The model is cached locally after first download
- Model loading is cached in-memory using `functools.lru_cache` to avoid repeated loading

**Note**: If torch DLL loading fails (common on some Windows systems), the service automatically falls back to TF-IDF + skill-based matching without semantic similarity.

## API Endpoints

### Health Check

**GET** `/health`

Returns application status and version information.

**Response:**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "app_name": "AI Resume Screening Backend"
}
```

### Resume Upload

**POST** `/api/v1/resumes/upload`

Upload and process multiple resume files (PDF or DOCX). Each file is processed independently.

**Request (multipart/form-data):**
```bash
curl -X POST "http://localhost:8000/api/v1/resumes/upload" \
  -F "files=@resume1.pdf" \
  -F "files=@resume2.docx"
```

**Response:**
```json
{
  "total_files": 2,
  "successful": 2,
  "failed": 0,
  "results": [
    {
      "resume_id": "uuid-1",
      "filename": "resume1.pdf",
      "status": "success",
      "message": "Resume processed successfully",
      "extraction": {
        "text": "...",
        "source_format": "pdf",
        "num_pages": 2,
        "is_scanned": false,
        "metadata": {}
      },
      "candidate_info": {
        "name": "Arjun Sharma",
        "email": "arjun@example.com",
        "phone": "+91-9876543210",
        "education": [...],
        "experience": [...],
        "certifications": [...],
        "projects": [...],
        "skills": ["Python", "Django", "PostgreSQL"]
      },
      "error": null
    }
  ]
}
```

### Resume Retrieve

**GET** `/api/v1/resumes/{resume_id}`

Retrieve a processed resume by its ID.

**Response:**
```json
{
  "resume_id": "uuid-1",
  "filename": "resume1.pdf",
  "extraction": { ... },
  "candidate_info": { ... }
}
```

### Job Analysis

**POST** `/api/v1/jobs/analyze`

Analyze a job description to extract requirements.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/jobs/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "job_description": "Senior Python Developer with Django and PostgreSQL experience. Required skills: Python, Django, PostgreSQL, Docker. 5+ years experience."
  }'
```

**Response:**
```json
{
  "job_id": "uuid-job-1",
  "analysis": {
    "title": "Senior Python Developer",
    "required_skills": ["Python", "Django", "PostgreSQL", "Docker"],
    "preferred_skills": [],
    "qualifications": [],
    "experience_required": "5+ years",
    "raw_text": "..."
  }
}
```

### Job Retrieve

**GET** `/api/v1/jobs/{job_id}`

Retrieve an analyzed job description by its ID.

### Matching Evaluation

**POST** `/api/v1/matching/evaluate`

Evaluate resume-job matching for multiple candidates against a job.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/matching/evaluate" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "uuid-job-1",
    "resume_ids": ["uuid-1", "uuid-2"],
    "use_semantic": false
  }'
```

**Response:**
```json
{
  "job_id": "uuid-job-1",
  "total_candidates": 2,
  "successful": 2,
  "failed": 0,
  "results": [
    {
      "resume_id": "uuid-1",
      "filename": "resume1.pdf",
      "candidate_name": "Arjun Sharma",
      "match_result": {
        "overall_score": 85.5,
        "tfidf_score": 78.2,
        "semantic_score": null,
        "skill_match_score": 100.0,
        "matched_skills": ["Python", "Django", "PostgreSQL", "Docker"],
        "missing_skills": [],
        "additional_skills": ["Git", "AWS"],
        "explanation": "..."
      },
      "error": null
    }
  ]
}
```

### Report Generation

**POST** `/api/v1/reports/generate`

Generate a match report for a specific resume and job (JSON or CSV format).

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/reports/generate?format=json&job_id=uuid-job-1&resume_id=uuid-1"
```

**Response:**
```json
{
  "report_id": "uuid-report-1",
  "format": "json",
  "content": "{...}"
}
```

### Report Retrieve

**GET** `/api/v1/reports/{report_id}`

Retrieve a generated report by its ID.

## Bug Fixes (Stage 2)

The following bugs were fixed during service migration:

1. **Empty Skill Lists**: Empty candidate and job skill lists now return 0% match instead of misleading 100%
2. **Semantic Model Failure**: Semantic similarity now returns `None` on failure, distinguishable from a genuine 0.0 score
3. **Fallback Scoring**: When semantic scoring is unavailable, the system correctly uses 50% TF-IDF + 50% skills weights

## Development Notes

- This is Stage 3 of the migration. REST API layer is now implemented.
- Data is stored in-memory for this stage; PostgreSQL integration will be added in a future stage.
- The original Streamlit application in the root directory remains unchanged.
- Original source files in `src/` are preserved and not modified.
- Tests are migrated from `tests/` to `backend/tests/` with adaptations for the new package structure.
