"""Serialization utilities for converting Pydantic models to JSON-compatible structures."""
from typing import Any, Dict, List, Union
from uuid import UUID
from datetime import datetime, date
from enum import Enum


def serialize_for_jsonb(value: Any) -> Any:
    """
    Recursively convert Pydantic models and other objects to JSON-serializable structures.
    
    Args:
        value: Any value to serialize.
        
    Returns:
        JSON-serializable version of the value.
    """
    if value is None:
        return None
    
    # Handle Pydantic models (v2)
    if hasattr(value, 'model_dump'):
        return value.model_dump(mode='json')
    
    # Handle dataclasses
    if hasattr(value, '__dataclass_fields__'):
        import dataclasses
        return dataclasses.asdict(value)
    
    # Handle dictionaries recursively
    if isinstance(value, dict):
        return {k: serialize_for_jsonb(v) for k, v in value.items()}
    
    # Handle lists recursively
    if isinstance(value, (list, tuple)):
        return [serialize_for_jsonb(item) for item in value]
    
    # Handle UUID
    if isinstance(value, UUID):
        return str(value)
    
    # Handle datetime and date
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    
    # Handle enums
    if isinstance(value, Enum):
        return value.value
    
    # Handle primitive types (str, int, float, bool) - return as-is
    if isinstance(value, (str, int, float, bool)):
        return value
    
    # Fallback: try to convert to string
    return str(value)
