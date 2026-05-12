import json

# This model runs locally on your machine.
# It is small, popular, and a good beginner-friendly choice for semantic search.
MODEL_NAME = "all-MiniLM-L6-v2"

# This starts as None and gets loaded the first time we need embeddings.
# Keeping it global lets us reuse the model instead of reloading it every request.
embedding_model = None


def get_embedding_model():
    """
    Load the embedding model once, then reuse it.

    The first call may take a little while because the model may need to be
    downloaded. Later calls are much faster.
    """
    global embedding_model

    if embedding_model is None:
        # Import here so normal app startup stays quick.
        from sentence_transformers import SentenceTransformer

        embedding_model = SentenceTransformer(MODEL_NAME)

    return embedding_model


def generate_embedding(text: str) -> list[float]:
    """
    Convert text into a list of numbers called an embedding.

    Similar pieces of text should produce embeddings that point in similar
    directions, which lets us compare meaning instead of exact keywords.
    """
    model = get_embedding_model()
    embedding = model.encode(text)
    return embedding.tolist()


def serialize_embedding(embedding: list[float]) -> str:
    """
    Store embeddings as JSON text in PostgreSQL.
    """
    return json.dumps(embedding)
