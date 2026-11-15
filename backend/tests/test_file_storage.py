import os
import tempfile
from pathlib import Path

import pytest

from app.core.exceptions import ValidationError
from app.services.file_storage_service import FileStorageService


@pytest.fixture
def temp_storage_dir():
    """Create a temporary directory for file storage tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def file_storage(temp_storage_dir):
    """Create a FileStorageService instance with temporary storage."""
    service = FileStorageService(storage_dir=temp_storage_dir)
    return service


def test_save_pdf_file(file_storage):
    """Test saving a PDF file."""
    content = b"%PDF-1.4\n%fake pdf content"
    filename = "resume.pdf"
    
    storage_key = file_storage.save_file(filename, content)
    
    assert storage_key
    assert storage_key.endswith(".pdf")
    assert file_storage.storage_dir.exists()
    
    saved_content = file_storage.retrieve_file(storage_key)
    assert saved_content == content


def test_save_docx_file(file_storage):
    """Test saving a DOCX file."""
    content = b"PK\x03\x04fake docx content"
    filename = "resume.docx"
    
    storage_key = file_storage.save_file(filename, content)
    
    assert storage_key
    assert storage_key.endswith(".docx")
    
    saved_content = file_storage.retrieve_file(storage_key)
    assert saved_content == content


def test_unsupported_file_extension(file_storage):
    """Test that unsupported file extensions are rejected."""
    content = b"plain text content"
    filename = "resume.txt"
    
    with pytest.raises(ValidationError) as exc_info:
        file_storage.save_file(filename, content)
    
    assert "Unsupported file type" in str(exc_info.value)


def test_empty_file(file_storage):
    """Test that empty files are rejected."""
    content = b""
    filename = "resume.pdf"
    
    with pytest.raises(ValidationError) as exc_info:
        file_storage.save_file(filename, content)
    
    assert "empty" in str(exc_info.value).lower()


def test_missing_filename(file_storage):
    """Test that missing filename is rejected."""
    content = b"some content"
    filename = ""
    
    with pytest.raises(ValidationError) as exc_info:
        file_storage.save_file(filename, content)
    
    assert "Filename is required" in str(exc_info.value)


def test_oversized_file(file_storage):
    """Test that oversized files are rejected."""
    # Create content larger than 10MB
    content = b"x" * (11 * 1024 * 1024)
    filename = "large.pdf"
    
    with pytest.raises(ValidationError) as exc_info:
        file_storage.save_file(filename, content)
    
    assert "exceeds maximum" in str(exc_info.value).lower()


def test_retrieve_file(file_storage):
    """Test retrieving a saved file."""
    content = b"test content"
    filename = "test.pdf"
    
    storage_key = file_storage.save_file(filename, content)
    retrieved = file_storage.retrieve_file(storage_key)
    
    assert retrieved == content


def test_retrieve_nonexistent_file(file_storage):
    """Test retrieving a file that doesn't exist."""
    with pytest.raises(FileNotFoundError):
        file_storage.retrieve_file("nonexistent.pdf")


def test_delete_file(file_storage):
    """Test deleting a file."""
    content = b"test content"
    filename = "test.pdf"
    
    storage_key = file_storage.save_file(filename, content)
    deleted = file_storage.delete_file(storage_key)
    
    assert deleted is True
    
    with pytest.raises(FileNotFoundError):
        file_storage.retrieve_file(storage_key)


def test_delete_nonexistent_file(file_storage):
    """Test deleting a file that doesn't exist."""
    deleted = file_storage.delete_file("nonexistent.pdf")
    assert deleted is False


def test_path_traversal_prevention(file_storage):
    """Test that path traversal attempts are prevented."""
    content = b"test content"
    
    # Try various path traversal attempts
    malicious_keys = [
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32",
        "/etc/passwd",
        "C:\\Windows\\System32",
    ]
    
    for key in malicious_keys:
        with pytest.raises(ValidationError):
            file_storage.retrieve_file(key)
        
        with pytest.raises(ValidationError):
            file_storage.delete_file(key)


def test_uuid_filename_generation(file_storage):
    """Test that storage keys are UUID-based."""
    content = b"test content"
    filename = "resume.pdf"
    
    storage_key1 = file_storage.save_file(filename, content)
    storage_key2 = file_storage.save_file(filename, content)
    
    # Both should end with .pdf
    assert storage_key1.endswith(".pdf")
    assert storage_key2.endswith(".pdf")
    
    # But should have different UUID prefixes
    assert storage_key1 != storage_key2


def test_file_cleanup_on_error(file_storage):
    """Test that files are cleaned up when database persistence would fail."""
    content = b"test content"
    filename = "test.pdf"
    
    storage_key = file_storage.save_file(filename, content)
    
    # Simulate cleanup after error
    file_storage.delete_file(storage_key)
    
    with pytest.raises(FileNotFoundError):
        file_storage.retrieve_file(storage_key)


def test_get_file_path(file_storage):
    """Test getting the absolute file path for a storage key."""
    content = b"test content"
    filename = "test.pdf"
    
    storage_key = file_storage.save_file(filename, content)
    file_path = file_storage.get_file_path(storage_key)
    
    assert file_path.is_absolute()
    assert str(storage_key) in str(file_path)


def test_get_file_path_invalid_key(file_storage):
    """Test that get_file_path rejects invalid keys."""
    with pytest.raises(ValidationError):
        file_storage.get_file_path("../../../etc/passwd")
