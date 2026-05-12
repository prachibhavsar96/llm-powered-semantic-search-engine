from pydantic import BaseModel


class DashboardStatsResponse(BaseModel):
    """
    Simple dashboard numbers for the logged-in user.
    """

    total_uploaded_files: int
    total_indexed_chunks: int
    total_searches: int
    average_search_time_ms: float
