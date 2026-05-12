"""Retrieve relevant documents from ChromaDB vector store."""

import logging
from dataclasses import dataclass

import chromadb

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class RetrievalResult:
    """A single retrieved document with its metadata and relevance score.

    Attributes:
        document: The text content of the retrieved chunk.
        metadata: Associated metadata (type, code, filename, etc).
        distance: Similarity distance — lower means more relevant.
        id: Unique identifier of the document in ChromaDB.
    """

    document: str
    metadata: dict
    distance: float
    id: str


def get_chroma_client() -> chromadb.PersistentClient:
    """Return a persistent ChromaDB client.

    Returns:
        ChromaDB client connected to local storage.
    """
    return chromadb.PersistentClient(path=settings.chroma_db_path)


def get_collection(
    client: chromadb.PersistentClient,
    collection_name: str = "healthcare_policies"
) -> chromadb.Collection:
    """Get existing ChromaDB collection.

    Args:
        client: ChromaDB client instance.
        collection_name: Name of the collection to retrieve.

    Returns:
        ChromaDB collection.

    Raises:
        ValueError: If collection does not exist.
    """
    try:
        return client.get_collection(name=collection_name)
    except Exception:
        raise ValueError(
            f"Collection '{collection_name}' not found. "
            "Run ingest.py first to populate the knowledge base."
        )


def retrieve(
    query: str,
    n_results: int = 3,
    filter_type: str | None = None
) -> list[RetrievalResult]:
    """Search ChromaDB for documents relevant to the query.

    Args:
        query: The search query from the provider or agent.
        n_results: Number of results to return.
        filter_type: Optional filter — 'denial_code' or 'policy_document'.

    Returns:
        List of RetrievalResult ordered by relevance.
    """
    client = get_chroma_client()
    collection = get_collection(client)

    # Build optional metadata filter
    where = {"type": filter_type} if filter_type else None

    try:
        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"]
        )
    except Exception as e:
        logger.error(f"ChromaDB query failed: {e}")
        return []

    # Unpack ChromaDB response format into clean objects
    retrieval_results = []
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]
    ids = results["ids"][0]

    for doc, meta, dist, doc_id in zip(documents, metadatas, distances, ids):
        retrieval_results.append(
            RetrievalResult(
                document=doc,
                metadata=meta,
                distance=dist,
                id=doc_id
            )
        )

    logger.info(f"Retrieved {len(retrieval_results)} results for query: '{query}'")
    return retrieval_results


def retrieve_denial_code(denial_code: str) -> RetrievalResult | None:
    """Retrieve a specific denial code by its code string.

    Args:
        denial_code: The denial code to look up (e.g. 'CO-4', 'PR-1').

    Returns:
        RetrievalResult if found, None otherwise.
    """
    client = get_chroma_client()
    collection = get_collection(client)

    try:
        results = collection.get(
            ids=[f"denial_code_{denial_code}"],
            include=["documents", "metadatas"]
        )
    except Exception as e:
        logger.error(f"Denial code lookup failed: {e}")
        return None

    if not results["documents"]:
        return None

    return RetrievalResult(
        document=results["documents"][0],
        metadata=results["metadatas"][0],
        distance=0.0,
        id=f"denial_code_{denial_code}"
    )


def format_results_for_claude(results: list[RetrievalResult]) -> str:
    """Format retrieval results into a string Claude can use as context.

    Args:
        results: List of retrieval results to format.

    Returns:
        Formatted string with all retrieved documents.
    """
    if not results:
        return "No relevant documents found in knowledge base."

    formatted = []
    for i, result in enumerate(results, 1):
        source = result.metadata.get("code") or result.metadata.get("filename", "unknown")
        formatted.append(
            f"[Source {i}: {source}]\n{result.document}"
        )

    return "\n\n---\n\n".join(formatted)


if __name__ == "__main__":
    # Quick test
    print("Testing retriever...\n")

    # Test semantic search
    query = "claim denied for missing prior authorization"
    results = retrieve(query, n_results=3)

    print(f"Query: '{query}'")
    print(f"Results: {len(results)}\n")

    formatted = format_results_for_claude(results)
    print(formatted)