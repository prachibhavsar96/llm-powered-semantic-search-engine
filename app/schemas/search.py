from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """
    Data the client sends when searching documents by meaning.
    """

    query: str = Field(..., min_length=1)
    top_k: int = Field(default=3, ge=1, le=20)

    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "How can caching improve performance?",
                "top_k": 3,
            }
        }
    }


class SearchResult(BaseModel):
    """
    One document returned from semantic search.
    """

    id: int
    title: str
    content: str
    created_at: datetime
    similarity_score: float
    final_score: float
    source_filename: Optional[str] = None
    chunk_index: Optional[int] = None
    answer_summary: Optional[str] = None


class SearchResponse(BaseModel):
    """
    Search results plus lightweight performance metadata.
    """

    results: list[SearchResult]
    answer_summary: str
    execution_time_ms: float
    total_documents_scanned: int
    cache_hit: bool


class SearchHistoryResponse(BaseModel):
    """
    A recent query saved for the logged-in user.
    """

    id: int
    query: str
    created_at: datetime

    model_config = {"from_attributes": True}
