import json
import math
import re
from time import perf_counter

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.database import get_db
from app.models.document import Document
from app.models.search_history import SearchHistory
from app.models.user import User
from app.schemas.search import SearchHistoryResponse, SearchRequest, SearchResponse, SearchResult
from app.services.embedding_service import generate_embedding
from app.services.ranking_service import combined_search_score, keyword_overlap_score
from app.services.search_cache import get_cached_results, set_cached_results

router = APIRouter(tags=["Search"])

MIN_SIMILARITY_SCORE = 0.25
MIN_FINAL_SCORE = 0.30
NEAR_DUPLICATE_THRESHOLD = 0.85
NO_RELEVANT_INFO_MESSAGE = "I could not find enough relevant information in the uploaded documents."
STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "what",
    "when",
    "where",
    "why",
    "with",
}


def parse_stored_embedding(embedding) -> list[float]:
    """
    Convert the stored embedding into a normal Python list.

    Depending on the database setup, the value may already be a list or it may
    be JSON text.
    """
    if isinstance(embedding, str):
        return json.loads(embedding)

    if hasattr(embedding, "tolist"):
        return embedding.tolist()

    return list(embedding)


def cosine_similarity(first_embedding: list[float], second_embedding: list[float]) -> float:
    """
    Compare two embeddings in Python.
    """
    dot_product = sum(a * b for a, b in zip(first_embedding, second_embedding))
    first_length = math.sqrt(sum(a * a for a in first_embedding))
    second_length = math.sqrt(sum(b * b for b in second_embedding))

    if first_length == 0 or second_length == 0:
        return 0.0

    return dot_product / (first_length * second_length)


def content_words(text: str) -> set[str]:
    """
    Normalize content into words for duplicate checks and simple explanations.
    """
    return set(re.findall(r"\w+", text.lower()))


def meaningful_words(text: str) -> set[str]:
    """
    Keep words that carry more meaning for ranking and filtering.
    """
    return {
        word
        for word in content_words(text)
        if len(word) > 2 and word not in STOP_WORDS
    }


def is_generic_chunk(content: str) -> bool:
    """
    Filter chunks that are too short or mostly generic words.
    """
    words = meaningful_words(content)
    return len(words) < 3


def is_near_duplicate(content: str, existing_contents: list[str]) -> bool:
    """
    Skip exact or highly overlapping chunks in search results.
    """
    current_words = content_words(content)

    if not current_words:
        return True

    normalized_content = " ".join(content.lower().split())

    for existing_content in existing_contents:
        if normalized_content == " ".join(existing_content.lower().split()):
            return True

        existing_words = content_words(existing_content)

        if not existing_words:
            continue

        overlap = len(current_words.intersection(existing_words))
        union = len(current_words.union(existing_words))

        if union and overlap / union >= NEAR_DUPLICATE_THRESHOLD:
            return True

    return False


def best_sentence_for_query(query: str, content: str) -> str:
    """
    Pick the sentence with the most query overlap from a chunk.
    """
    query_words = meaningful_words(query)
    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", content)
        if sentence.strip()
    ]

    if not sentences:
        sentences = [content.strip()]

    return max(
        sentences,
        key=lambda sentence: len(query_words.intersection(meaningful_words(sentence))),
    )


def build_answer_summary(query: str, results: list[SearchResult]) -> str:
    """
    Generate a short rule-based answer from the top matching chunks.
    """
    if not results:
        return NO_RELEVANT_INFO_MESSAGE

    top_results = results[:3]
    selected_sentences = []

    for result in top_results:
        sentence = best_sentence_for_query(query, result.content)

        if sentence and sentence not in selected_sentences:
            selected_sentences.append(sentence)

        if len(selected_sentences) == 2:
            break

    if not selected_sentences:
        return NO_RELEVANT_INFO_MESSAGE

    answer = " ".join(selected_sentences)
    shared_words = sorted(meaningful_words(query).intersection(meaningful_words(answer)))

    if shared_words:
        keywords = ", ".join(shared_words[:5])
        return f"{answer} This answer is based on matching chunks related to {keywords}."

    return f"{answer} This answer is based on the highest-ranked matching chunks."


def save_search_history(db: Session, user_id: int, query: str, search_time_ms: float):
    """
    Save a successful search, or refresh it if the user searched it before.
    """
    cleaned_query = query.strip()

    if not cleaned_query:
        return

    existing_search = (
        db.query(SearchHistory)
        .filter(
            SearchHistory.user_id == user_id,
            func.lower(SearchHistory.query) == cleaned_query.lower(),
        )
        .order_by(SearchHistory.created_at.desc())
        .first()
    )

    if existing_search:
        existing_search.created_at = func.now()
        existing_search.search_time_ms = search_time_ms
    else:
        db.add(
            SearchHistory(
                user_id=user_id,
                query=cleaned_query,
                search_time_ms=search_time_ms,
            )
        )

    db.commit()


@router.get("/search/history", response_model=list[SearchHistoryResponse])
def get_search_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return the latest searches for the logged-in user.
    """
    saved_searches = (
        db.query(SearchHistory)
        .filter(SearchHistory.user_id == current_user.id)
        .order_by(SearchHistory.created_at.desc())
        .limit(50)
        .all()
    )

    unique_searches = []
    seen_queries = set()

    for saved_search in saved_searches:
        normalized_query = saved_search.query.strip().lower()

        if normalized_query in seen_queries:
            continue

        unique_searches.append(saved_search)
        seen_queries.add(normalized_query)

        if len(unique_searches) == 10:
            break

    return unique_searches


@router.post("/search", response_model=SearchResponse)
def semantic_search(
    search_request: SearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Search documents by comparing query and document embeddings.
    """
    start_time = perf_counter()
    cached_response = get_cached_results(
        current_user.id,
        search_request.query,
        search_request.top_k,
    )

    if cached_response is not None:
        execution_time_ms = round((perf_counter() - start_time) * 1000, 2)
        save_search_history(db, current_user.id, search_request.query, execution_time_ms)
        return SearchResponse(
            results=cached_response["results"],
            answer_summary=cached_response["answer_summary"],
            execution_time_ms=execution_time_ms,
            total_documents_scanned=cached_response["total_documents_scanned"],
            cache_hit=True,
        )

    query_embedding = generate_embedding(search_request.query)
    documents = (
        db.query(Document)
        .filter(Document.user_id == current_user.id, Document.embedding.isnot(None))
        .all()
    )
    total_documents_scanned = len(documents)

    candidates = []
    for document in documents:
        if is_generic_chunk(document.content):
            continue

        document_embedding = parse_stored_embedding(document.embedding)
        cosine_score = cosine_similarity(query_embedding, document_embedding)

        if cosine_score < MIN_SIMILARITY_SCORE:
            continue

        final_score = combined_search_score(
            search_request.query,
            document.content,
            cosine_score,
        )

        candidates.append(
            SearchResult(
                id=document.id,
                title=document.title,
                content=document.content,
                created_at=document.created_at,
                similarity_score=cosine_score,
                final_score=final_score,
                source_filename=document.source_filename,
                chunk_index=document.chunk_index,
            )
        )

    candidates.sort(key=lambda result: result.final_score, reverse=True)

    results = []
    selected_contents = []

    for candidate in candidates:
        if candidate.final_score < MIN_FINAL_SCORE:
            continue

        if keyword_overlap_score(search_request.query, candidate.content) == 0 and candidate.final_score < 0.45:
            continue

        if is_near_duplicate(candidate.content, selected_contents):
            continue

        results.append(candidate)
        selected_contents.append(candidate.content)

        if len(results) == search_request.top_k:
            break

    answer_summary = build_answer_summary(search_request.query, results)

    if results:
        results[0].answer_summary = answer_summary

    set_cached_results(
        current_user.id,
        search_request.query,
        search_request.top_k,
        results,
        answer_summary,
        total_documents_scanned,
    )
    execution_time_ms = round((perf_counter() - start_time) * 1000, 2)
    save_search_history(db, current_user.id, search_request.query, execution_time_ms)

    return SearchResponse(
        results=results,
        answer_summary=answer_summary,
        execution_time_ms=execution_time_ms,
        total_documents_scanned=total_documents_scanned,
        cache_hit=False,
    )
