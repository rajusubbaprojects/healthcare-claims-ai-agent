"""Ingest documents and denial codes into ChromaDB vector store."""

import json
import logging
from pathlib import Path

import chromadb


from app.config import get_settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


def get_chroma_client() -> chromadb.PersistentClient:
    """Return a persistent ChromaDB client.
    
    Returns:
        ChromaDB client connected to local storage.
    """
    return chromadb.PersistentClient(path=settings.chroma_db_path)




def get_or_create_collection(
    client: chromadb.PersistentClient,
    collection_name: str = "healthcare_policies"
) -> chromadb.Collection:
    """Get existing collection or create a new one.

    Args:
        client: ChromaDB client instance.
        collection_name: Name of the collection to get or create.

    Returns:
        ChromaDB collection.
    """
    return client.get_or_create_collection(
        name=collection_name,
        metadata={"description": "Healthcare policy and denial code knowledge base"}
    )


def ingest_denial_codes(
    collection: chromadb.Collection,
    denial_codes_path: str = "data/denial_codes.json"
) -> int:
    """Load denial codes into ChromaDB.
    
    Each denial code becomes a searchable document chunk
    containing its description, causes, and resolution steps.
    
    Args:
        collection: ChromaDB collection to ingest into.
        denial_codes_path: Path to denial codes JSON file.
        
    Returns:
        Number of denial codes ingested.
    """
    path = Path(denial_codes_path)
    if not path.exists():
        logger.error(f"Denial codes file not found: {denial_codes_path}")
        return 0

    denial_codes = json.loads(path.read_text())

    documents = []
    metadatas = []
    ids = []

    for code, data in denial_codes.items():
        # Build a rich text document for each denial code
        # The richer the text, the better the semantic search
        causes_text = "\n".join(f"- {c}" for c in data["common_causes"])
        resolution_text = "\n".join(f"- {r}" for r in data["resolution"])

        document = f"""
Denial Code: {data['code']}
Category: {data['category']}
Description: {data['description']}

Common Causes:
{causes_text}

Resolution Steps:
{resolution_text}
        """.strip()

        documents.append(document)
        metadatas.append({
            "type": "denial_code",
            "code": code,
            "category": data["category"]
        })
        ids.append(f"denial_code_{code}")

    # Upsert — insert or update if already exists
    collection.upsert(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )

    logger.info(f"Ingested {len(documents)} denial codes")
    return len(documents)


def ingest_policy_documents(
    collection: chromadb.Collection,
    policies_dir: str = "data/policies"
) -> int:
    """Load policy text files into ChromaDB.
    
    Reads all .txt files from the policies directory
    and ingests them as searchable documents.
    
    Args:
        collection: ChromaDB collection to ingest into.
        policies_dir: Directory containing policy text files.
        
    Returns:
        Number of policy documents ingested.
    """
    path = Path(policies_dir)
    if not path.exists():
        logger.warning(f"Policies directory not found: {policies_dir}")
        return 0

    policy_files = list(path.glob("*.txt"))
    if not policy_files:
        logger.warning("No policy files found in policies directory")
        return 0

    documents = []
    metadatas = []
    ids = []

    for i, file_path in enumerate(policy_files):
        content = file_path.read_text()

        # Split large documents into chunks of ~500 words
        chunks = chunk_text(content, chunk_size=500)

        for j, chunk in enumerate(chunks):
            documents.append(chunk)
            metadatas.append({
                "type": "policy_document",
                "filename": file_path.name,
                "chunk_index": j
            })
            ids.append(f"policy_{file_path.stem}_chunk_{j}")

    if documents:
        collection.upsert(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        logger.info(f"Ingested {len(documents)} policy document chunks")

    return len(documents)


def chunk_text(text: str, chunk_size: int = 500) -> list[str]:
    """Split text into chunks of approximately chunk_size words.
    
    Args:
        text: Text to split into chunks.
        chunk_size: Target number of words per chunk.
        
    Returns:
        List of text chunks.
    """
    words = text.split()
    chunks = []

    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)

    return chunks


def run_ingestion() -> dict:
    """Run full ingestion pipeline.
    
    Returns:
        Summary of ingestion results.
    """
    logger.info("Starting ingestion pipeline...")

    client = get_chroma_client()
    collection = get_or_create_collection(client)

    denial_count = ingest_denial_codes(collection)
    policy_count = ingest_policy_documents(collection)

    total = collection.count()

    summary = {
        "denial_codes_ingested": denial_count,
        "policy_chunks_ingested": policy_count,
        "total_documents_in_db": total
    }

    logger.info(f"Ingestion complete: {summary}")
    return summary


if __name__ == "__main__":
    result = run_ingestion()
    print(f"\nIngestion Summary:")
    print(f"  Denial codes:     {result['denial_codes_ingested']}")
    print(f"  Policy chunks:    {result['policy_chunks_ingested']}")
    print(f"  Total in ChromaDB: {result['total_documents_in_db']}")