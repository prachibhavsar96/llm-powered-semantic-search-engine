import re


def split_long_sentence(sentence: str, max_characters: int) -> list[str]:
    """
    Break a very long sentence into smaller pieces.

    This is a fallback for text that has few or no sentence breaks.
    """
    return [
        sentence[index : index + max_characters].strip()
        for index in range(0, len(sentence), max_characters)
        if sentence[index : index + max_characters].strip()
    ]


def chunk_text(text: str, max_characters: int = 300) -> list[str]:
    """
    Split text into paragraph and sentence chunks.

    Smaller chunks make search results more focused.
    """
    if not text.strip():
        return []

    chunks = []
    paragraphs = re.split(r"\n\s*\n+", text.strip())

    for paragraph in paragraphs:
        clean_paragraph = " ".join(paragraph.split())

        if not clean_paragraph:
            continue

        if len(clean_paragraph) <= max_characters and not re.search(r"[.!?]\s+", clean_paragraph):
            chunks.append(clean_paragraph)
            continue

        sentences = re.split(r"(?<=[.!?])\s+", clean_paragraph)

        for sentence in sentences:
            sentence = sentence.strip()

            if not sentence:
                continue

            if len(sentence) > max_characters:
                chunks.extend(split_long_sentence(sentence, max_characters))
            else:
                chunks.append(sentence)

    return chunks
