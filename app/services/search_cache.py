from app.schemas.search import SearchResult

# Simple in-memory cache for repeated search queries.
# This resets whenever the FastAPI process restarts.
search_cache: dict[tuple[int, str, int], dict] = {}


def build_cache_key(user_id: int, query: str, top_k: int) -> tuple[int, str, int]:
    return (user_id, query.strip().lower(), top_k)


def get_cached_results(user_id: int, query: str, top_k: int) -> dict | None:
    return search_cache.get(build_cache_key(user_id, query, top_k))


def set_cached_results(
    user_id: int,
    query: str,
    top_k: int,
    results: list[SearchResult],
    answer_summary: str,
    total_documents_scanned: int,
) -> None:
    search_cache[build_cache_key(user_id, query, top_k)] = {
        "results": results,
        "answer_summary": answer_summary,
        "total_documents_scanned": total_documents_scanned,
    }


def clear_search_cache() -> None:
    search_cache.clear()
