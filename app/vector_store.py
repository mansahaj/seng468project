import os

from qdrant_client import QdrantClient
from qdrant_client.http import models


def get_qdrant_url() -> str:
    return os.getenv("QDRANT_URL", "http://localhost:6333")


def get_collection_name() -> str:
    return os.getenv("QDRANT_COLLECTION", "document_chunks")


def get_qdrant_client() -> QdrantClient:
    return QdrantClient(url=get_qdrant_url())


def collection_exists() -> bool:
    client = get_qdrant_client()
    collection_name = get_collection_name()
    collections = client.get_collections().collections
    return any(collection.name == collection_name for collection in collections)


def ensure_collection_exists(vector_size: int) -> None:
    if collection_exists():
        return

    client = get_qdrant_client()
    collection_name = get_collection_name()
    client.create_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(
            size=vector_size,
            distance=models.Distance.COSINE,
        ),
    )


def upsert_chunk_vectors(chunk_records: list[dict]) -> None:
    if not chunk_records:
        return

    ensure_collection_exists(len(chunk_records[0]["vector"]))
    client = get_qdrant_client()
    points = [
        models.PointStruct(
            id=record["chunk_id"],
            vector=record["vector"],
            payload={
                "chunk_id": record["chunk_id"],
                "document_id": record["document_id"],
                "filename": record["filename"],
                "user_id": record["user_id"],
                "text": record["text"],
            },
        )
        for record in chunk_records
    ]
    client.upsert(collection_name=get_collection_name(), points=points)


def search_chunk_vectors(
    query_vector: list[float],
    user_id: str,
    limit: int = 5,
) -> list[dict]:
    ensure_collection_exists(len(query_vector))
    client = get_qdrant_client()
    response = client.query_points(
        collection_name=get_collection_name(),
        query=query_vector,
        query_filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="user_id",
                    match=models.MatchValue(value=user_id),
                )
            ]
        ),
        limit=limit,
        with_payload=True,
    )
    results = response.points

    return [
        {
            "text": result.payload["text"],
            "score": round(max(0.0, min((result.score + 1) / 2, 1.0)), 3),
            "document_id": result.payload["document_id"],
            "filename": result.payload["filename"],
        }
        for result in results
    ]


def delete_document_vectors(document_id: str) -> None:
    if not collection_exists():
        return

    client = get_qdrant_client()
    client.delete(
        collection_name=get_collection_name(),
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="document_id",
                        match=models.MatchValue(value=document_id),
                    )
                ]
            )
        ),
    )
