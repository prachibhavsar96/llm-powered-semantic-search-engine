import os

from pinecone import Pinecone, ServerlessSpec

INDEX_NAME = "semantic-search-docs"
EMBEDDING_DIMENSION = 384

# Free-tier serverless region; override if your Pinecone project uses another.
PINECONE_CLOUD = os.environ.get("PINECONE_CLOUD", "aws")
PINECONE_REGION = os.environ.get("PINECONE_REGION", "us-east-1")

_pinecone_client = None
_index = None


def get_pinecone_client() -> Pinecone:
    """
    Create the Pinecone client once, then reuse it.
    """
    global _pinecone_client

    if _pinecone_client is None:
        _pinecone_client = Pinecone(api_key=os.environ["PINECONE_API_KEY"])

    return _pinecone_client


def get_index():
    """
    Connect to the semantic-search index, creating it first if needed.
    """
    global _index

    if _index is None:
        client = get_pinecone_client()

        if not client.has_index(INDEX_NAME):
            client.create_index(
                name=INDEX_NAME,
                dimension=EMBEDDING_DIMENSION,
                metric="cosine",
                spec=ServerlessSpec(cloud=PINECONE_CLOUD, region=PINECONE_REGION),
            )

        _index = client.Index(INDEX_NAME)

    return _index


def upsert_document(document_id: int, embedding: list[float], metadata: dict) -> None:
    """
    Store or update a document chunk's embedding and metadata in Pinecone.
    """
    index = get_index()
    clean_metadata = {key: value for key, value in metadata.items() if value is not None}

    index.upsert(
        vectors=[
            {
                "id": str(document_id),
                "values": embedding,
                "metadata": clean_metadata,
            }
        ]
    )


def query_similar(embedding: list[float], user_id: int, top_k: int):
    """
    Find the most similar vectors for a user, filtered by user_id metadata.

    Returns Pinecone match objects (each with .id, .score, .metadata) so
    results can be reconstructed without a database round-trip.
    """
    index = get_index()
    response = index.query(
        vector=embedding,
        top_k=top_k,
        filter={"user_id": {"$eq": user_id}},
        include_metadata=True,
    )
    return response.matches


def delete_document(document_id: int) -> None:
    """
    Remove a document's vector from Pinecone.
    """
    index = get_index()
    index.delete(ids=[str(document_id)])
