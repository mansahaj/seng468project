# Semantic Retrieval System

Distributed semantic PDF retrieval system for SENG 468. The stack uses:
- FastAPI for the API
- PostgreSQL for users and document metadata
- Redis + RQ for asynchronous document processing
- MinIO for PDF object storage
- Qdrant for vector similarity search
- `sentence-transformers/all-MiniLM-L6-v2` for local embeddings

## Quick Start

```bash
cp .env.example .env
docker compose up --build
```

The API is available at `http://localhost:8080`.

## Services

- API: `http://localhost:8080`
- MinIO API: `http://localhost:9000`
- MinIO Console: `http://localhost:9001`
- Qdrant: `http://localhost:6333`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

## Core API

- `POST /auth/signup`
- `POST /auth/login`
- `POST /documents`
- `GET /documents`
- `DELETE /documents/{id}`
- `GET /search?q=...`

## Notes

- `POST /documents` returns immediately with `202 Accepted`.
- A background worker extracts PDF text, chunks it, generates embeddings, and stores vectors in Qdrant.
- Search is semantic retrieval over document content, not filename matching.
- The first run may take longer because the embedding model is downloaded into the shared `model_cache` volume.

## Healthchecks

Compose healthchecks are configured for:
- PostgreSQL
- Redis
- MinIO
- Qdrant
- API

`api` and `worker` wait for healthy dependencies before starting.

## End-to-End Verification

Verified flow:
- sign up
- log in
- upload PDF
- wait for document status to become `ready`
- search and receive top results
- delete document
- confirm document and search results are removed

## Troubleshooting

- If you change dependencies, rebuild with `docker compose up --build`.
- If startup fails because of stale containers or images, run:

```bash
docker compose down
docker compose up --build
```

- If PostgreSQL authentication fails after changing database credentials, your existing
  `postgres_data` volume was likely initialized with older values. Recreate the stack with a
  fresh database volume:

```bash
docker compose down -v
cp .env.example .env
docker compose up --build
```
