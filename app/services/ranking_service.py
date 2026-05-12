import re

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


def meaningful_words(text: str) -> set[str]:
    return {
        word
        for word in re.findall(r"\w+", text.lower())
        if len(word) > 2 and word not in STOP_WORDS
    }


def keyword_overlap_score(query: str, content: str) -> float:
    """
    Small ranking boost for chunks that share important words with the query.
    """
    query_words = meaningful_words(query)
    content_words = meaningful_words(content)

    if not query_words:
        return 0.0

    return len(query_words.intersection(content_words)) / len(query_words)


def combined_search_score(query: str, content: str, semantic_score: float) -> float:
    """
    Mostly trust semantic similarity, with a small keyword overlap boost.
    """
    lexical_score = keyword_overlap_score(query, content)
    score = (semantic_score * 0.85) + (lexical_score * 0.15)
    return max(0.0, min(score, 1.0))
