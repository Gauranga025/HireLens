import logging
from typing import Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DocumentProcessingError, UnsupportedFileTypeError, ValidationError
from app.db.session import get_db
from app.repositories.resume_repository import ResumeRepository
from app.schemas.api import BatchResumeUploadResponse, ResumeRetrieveResponse, ResumeUploadResponse
from app.schemas.resume import DocumentExtractionResult, ExtractedResumeInfo
from app.services.document_service import extract_text, validate_file
from app.services.file_storage_service import file_storage_service
from app.services.resume_parser_service import extract_all
from app.services.skill_service import extract_skills

router = APIRouter(prefix="/resumes", tags=["resumes"])
logger = logging.getLogger(__name__)

MAX_FILE_SIZE_MB = 10


@router.post("/upload", response_model=BatchResumeUploadResponse, status_code=status.HTTP_200_OK)
async def upload_resumes(
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
) -> BatchResumeUploadResponse:
    """
    Upload and process multiple resume files (PDF or DOCX).
    
    Each file is processed independently. Invalid files do not stop processing of valid files.
    Returns extraction results, candidate information, and extracted skills.
    """
    results: List[ResumeUploadResponse] = []
    successful = 0
    failed = 0
    resume_repo = ResumeRepository()

    for file in files:
        storage_key = None
        try:
            if not file.filename:
                raise ValidationError("Filename is required")

            file_content = await file.read()

            if not file_content:
                raise ValidationError("File is empty")

            is_valid, error_msg = validate_file(file_content, file.filename, max_size_mb=MAX_FILE_SIZE_MB)
            if not is_valid:
                raise ValidationError(error_msg)

            storage_key = file_storage_service.save_file(file.filename, file_content)

            extraction_dict = extract_text(file_content, file.filename)
            extraction = DocumentExtractionResult(**extraction_dict)

            extracted_info = extract_all(extraction.text)
            skills_data = extract_skills(extraction.text)
            
            extracted_info["skills"] = skills_data.get("technical_skills", []) + skills_data.get("soft_skills", [])
            
            candidate_info = ExtractedResumeInfo(**extracted_info)

            file_ext = extraction.source_format
            resume = await resume_repo.create(
                db=db,
                original_filename=file.filename,
                file_type=file_ext,
                candidate_name=candidate_info.name,
                email=candidate_info.email,
                phone=candidate_info.phone,
                candidate_info=candidate_info.model_dump(),
                extracted_text=extraction.text,
                skills=candidate_info.skills,
                storage_key=storage_key,
                processing_status="completed",
            )
            await db.commit()

            results.append(
                ResumeUploadResponse(
                    resume_id=str(resume.id),
                    filename=file.filename,
                    status="success",
                    message="Resume processed successfully",
                    extraction=extraction,
                    candidate_info=candidate_info,
                    error=None,
                )
            )
            successful += 1

        except UnsupportedFileTypeError as e:
            if storage_key:
                file_storage_service.delete_file(storage_key)
            failed += 1
            results.append(
                ResumeUploadResponse(
                    resume_id="",
                    filename=file.filename or "unknown",
                    status="error",
                    message="Unsupported file type",
                    extraction=None,
                    candidate_info=None,
                    error=str(e),
                )
            )
            logger.warning(f"Unsupported file type: {file.filename} - {e}")

        except ValidationError as e:
            if storage_key:
                file_storage_service.delete_file(storage_key)
            failed += 1
            results.append(
                ResumeUploadResponse(
                    resume_id="",
                    filename=file.filename or "unknown",
                    status="error",
                    message="Validation failed",
                    extraction=None,
                    candidate_info=None,
                    error=str(e),
                )
            )
            logger.warning(f"Validation failed for {file.filename}: {e}")

        except DocumentProcessingError as e:
            if storage_key:
                file_storage_service.delete_file(storage_key)
            failed += 1
            results.append(
                ResumeUploadResponse(
                    resume_id="",
                    filename=file.filename or "unknown",
                    status="error",
                    message="Document processing failed",
                    extraction=None,
                    candidate_info=None,
                    error=str(e),
                )
            )
            logger.error(f"Document processing failed for {file.filename}: {e}")

        except Exception as e:
            if storage_key:
                file_storage_service.delete_file(storage_key)
            await db.rollback()
            failed += 1
            results.append(
                ResumeUploadResponse(
                    resume_id="",
                    filename=file.filename or "unknown",
                    status="error",
                    message="Unexpected error during processing",
                    extraction=None,
                    candidate_info=None,
                    error="An unexpected error occurred",
                )
            )
            logger.error(f"Unexpected error processing {file.filename}: {e}")

    return BatchResumeUploadResponse(
        total_files=len(files),
        successful=successful,
        failed=failed,
        results=results,
    )


@router.get("/{resume_id}", response_model=ResumeRetrieveResponse, status_code=status.HTTP_200_OK)
async def get_resume(
    resume_id: str,
    db: AsyncSession = Depends(get_db),
) -> ResumeRetrieveResponse:
    """
    Retrieve a processed resume by its ID.
    
    Returns the document extraction result and extracted candidate information.
    """
    try:
        resume_uuid = UUID(resume_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid resume ID format: '{resume_id}'",
        )

    resume_repo = ResumeRepository()
    resume = await resume_repo.get_by_id(db, resume_uuid)

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resume with ID '{resume_id}' not found",
        )

    extraction = DocumentExtractionResult(
        text=resume.extracted_text,
        source_format=resume.file_type,
        num_pages=resume.candidate_info.get("num_pages", 0),
        is_scanned=resume.candidate_info.get("is_scanned", False),
        metadata=resume.candidate_info.get("metadata", {}),
    )
    
    candidate_info = ExtractedResumeInfo(**resume.candidate_info)

    return ResumeRetrieveResponse(
        resume_id=str(resume.id),
        filename=resume.original_filename,
        extraction=extraction,
        candidate_info=candidate_info,
    )
