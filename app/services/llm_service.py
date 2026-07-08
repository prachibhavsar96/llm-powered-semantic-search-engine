import logging
import os

from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger(__name__)

MODEL_NAME = "gemini-2.5-flash"
LLM_TIMEOUT_SECONDS = 15

REWRITE_SYSTEM_PROMPT = (
    "Rewrite the user's search query to be clearer and more specific for a "
    "document search engine. Return only the rewritten query, nothing else."
)
ANSWER_SYSTEM_PROMPT = (
    "Answer the user's question using only the numbered excerpts below. Be "
    "concise and answer directly. If the excerpts don't contain enough "
    "information, say so."
)


def _get_llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=MODEL_NAME,
        api_key=os.environ["GOOGLE_API_KEY"],
        timeout=LLM_TIMEOUT_SECONDS,
        max_retries=0,
    )


def rewrite_query(raw_query: str) -> str:
    """
    Expand a vague user query into a clearer search query via one LLM call.

    Falls back to the raw query unchanged if the call fails for any reason.
    """
    try:
        response = _get_llm().invoke(
            [
                ("system", REWRITE_SYSTEM_PROMPT),
                ("human", raw_query),
            ]
        )
        rewritten = response.content.strip()
        return rewritten or raw_query
    except Exception:
        return raw_query


def generate_answer(query: str, results: list) -> str | None:
    """
    Synthesize an answer from the top retrieved chunks via one LLM call.

    Returns None if there are no results or the call fails, so the caller
    can fall back to the existing build_answer_summary() logic.
    """
    if not results:
        return None

    try:
        excerpts = "\n\n".join(
            f"[{index + 1}] {result.content}" for index, result in enumerate(results[:5])
        )
        response = _get_llm().invoke(
            [
                ("system", ANSWER_SYSTEM_PROMPT),
                ("human", f"Excerpts:\n{excerpts}\n\nQuestion: {query}"),
            ]
        )
        answer = response.content.strip()
        return answer or None
    except Exception as exc:
        logger.error("generate_answer() LLM call failed: %s: %s", type(exc).__name__, exc)
        return None
