import os
import shutil
import uuid
from pathlib import Path
from typing import Final

from app.core.exceptions import ValidationError


class FileStorageService:
    """Service for managing local file storage for uploaded resumes."""
    
    SUPPORTED_EXTENSIONS: Final = {".pdf", ".docx"}
    MAX_FILE_SIZE_MB: Final = 10
    
    def __init__(self, storage_dir: str = "storage/uploads") -> None:
        """Initialize the file storage service.
        
        Args:
            storage_dir: Directory for storing uploaded files (relative to project root).
        """
        self.storage_dir = Path(storage_dir)
        self._ensure_storage_dir()
    
    def _ensure_storage_dir(self) -> None:
        """Create storage directory if it doesn't exist."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    def _validate_file(self, filename: str, content: bytes) -> None:
        """Validate file extension and size.
        
        Args:
            filename: Original filename.
            content: File content as bytes.
        
        Raises:
            ValidationError: If file is invalid.
        """
        if not filename:
            raise ValidationError("Filename is required")
        
        if not content:
            raise ValidationError("File is empty")
        
        file_ext = Path(filename).suffix.lower()
        if file_ext not in self.SUPPORTED_EXTENSIONS:
            raise ValidationError(
                f"Unsupported file type: {file_ext}. "
                f"Supported types: {', '.join(self.SUPPORTED_EXTENSIONS)}"
            )
        
        file_size_mb = len(content) / (1024 * 1024)
        if file_size_mb > self.MAX_FILE_SIZE_MB:
            raise ValidationError(
                f"File size exceeds maximum of {self.MAX_FILE_SIZE_MB}MB"
            )
    
    def _generate_storage_key(self, original_filename: str) -> str:
        """Generate a unique storage key based on UUID and original extension.
        
        Args:
            original_filename: Original filename.
        
        Returns:
            Unique storage key (e.g., "abc123.pdf").
        """
        ext = Path(original_filename).suffix.lower()
        return f"{uuid.uuid4()}{ext}"
    
    def save_file(self, filename: str, content: bytes) -> str:
        """Save a file to storage and return its storage key.
        
        Args:
            filename: Original filename.
            content: File content as bytes.
        
        Returns:
            Storage key for the saved file.
        
        Raises:
            ValidationError: If file validation fails.
            IOError: If file storage fails.
        """
        self._validate_file(filename, content)
        
        storage_key = self._generate_storage_key(filename)
        file_path = self.storage_dir / storage_key
        
        try:
            file_path.write_bytes(content)
        except Exception as e:
            raise IOError(f"Failed to save file: {e}")
        
        return storage_key
    
    def retrieve_file(self, storage_key: str) -> bytes:
        """Retrieve a file from storage by its storage key.
        
        Args:
            storage_key: Storage key of the file.
        
        Returns:
            File content as bytes.
        
        Raises:
            FileNotFoundError: If file doesn't exist.
            ValidationError: If storage key is invalid (path traversal attempt).
        """
        if not storage_key or "/" in storage_key or "\\" in storage_key:
            raise ValidationError("Invalid storage key")
        
        file_path = self.storage_dir / storage_key
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {storage_key}")
        
        if not file_path.is_file():
            raise ValidationError(f"Invalid file reference: {storage_key}")
        
        try:
            return file_path.read_bytes()
        except Exception as e:
            raise IOError(f"Failed to read file: {e}")
    
    def delete_file(self, storage_key: str) -> bool:
        """Delete a file from storage by its storage key.
        
        Args:
            storage_key: Storage key of the file.
        
        Returns:
            True if file was deleted, False if it didn't exist.
        
        Raises:
            ValidationError: If storage key is invalid (path traversal attempt).
        """
        if not storage_key or "/" in storage_key or "\\" in storage_key:
            raise ValidationError("Invalid storage key")
        
        file_path = self.storage_dir / storage_key
        
        if not file_path.exists():
            return False
        
        try:
            file_path.unlink()
            return True
        except Exception as e:
            raise IOError(f"Failed to delete file: {e}")
    
    def get_file_path(self, storage_key: str) -> Path:
        """Get the absolute file path for a storage key (internal use only).
        
        Args:
            storage_key: Storage key of the file.
        
        Returns:
            Absolute path to the file.
        
        Raises:
            ValidationError: If storage key is invalid.
        """
        if not storage_key or "/" in storage_key or "\\" in storage_key:
            raise ValidationError("Invalid storage key")
        
        return self.storage_dir.resolve() / storage_key


# Global file storage service instance
file_storage_service = FileStorageService()
