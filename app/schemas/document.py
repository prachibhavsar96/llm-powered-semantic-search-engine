from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class DocumentCreate(BaseModel):
    """
    Data the client must send when creating a document.
    """

    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)

    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "FastAPI Notes",
                "content": "FastAPI is a Python framework for building APIs quickly.",
            }
        }
    }


class DocumentResponse(BaseModel):
    """
    Data the API sends back to the client for a document.
    """

    id: int
    title: str
    content: str
    created_at: datetime
    source_filename: Optional[str] = None
    chunk_index: Optional[int] = None

    # from_attributes lets Pydantic read data from SQLAlchemy model objects.
    model_config = ConfigDict(from_attributes=True)
