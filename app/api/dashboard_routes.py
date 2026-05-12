from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.database import get_db
from app.models.document import Document
from app.models.search_history import SearchHistory
from app.models.user import User
from app.schemas.dashboard import DashboardStatsResponse

router = APIRouter(tags=["Dashboard"])


@router.get("/dashboard/stats", response_model=DashboardStatsResponse)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return lightweight dashboard statistics for the logged-in user.
    """
    documents = db.query(Document).filter(Document.user_id == current_user.id).all()
    uploaded_files = {
        document.source_filename or f"document-{document.id}"
        for document in documents
    }

    total_searches = (
        db.query(SearchHistory)
        .filter(SearchHistory.user_id == current_user.id)
        .count()
    )
    average_search_time = (
        db.query(func.avg(SearchHistory.search_time_ms))
        .filter(
            SearchHistory.user_id == current_user.id,
            SearchHistory.search_time_ms.isnot(None),
        )
        .scalar()
    )

    return DashboardStatsResponse(
        total_uploaded_files=len(uploaded_files),
        total_indexed_chunks=len(documents),
        total_searches=total_searches,
        average_search_time_ms=round(float(average_search_time or 0), 2),
    )
