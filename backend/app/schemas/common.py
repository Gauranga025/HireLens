from typing import Optional, Dict
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str = Field(..., description="Application status")
    version: str = Field(..., description="Application version")
    app_name: str = Field(..., description="Application name")


class ErrorResponse(BaseModel):
    """Standard error response schema."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict] = Field(default=None, description="Additional error details")
