#!/usr/bin/env bash
set -euo pipefail

WEAVIATE_URL="${WEAVIATE_URL:-http://localhost:8080}"

echo "Waiting for Weaviate at ${WEAVIATE_URL}..."
until curl -sf "${WEAVIATE_URL}/v1/.well-known/ready" > /dev/null 2>&1; do
    echo "  not ready, retrying in 2s..."
    sleep 2
done
echo "Weaviate is ready."

echo "Creating KnowledgeChunk schema..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "${WEAVIATE_URL}/v1/schema" \
    -H "Content-Type: application/json" \
    -d '{
        "class": "KnowledgeChunk",
        "description": "A single text chunk from a healthcare document with its embedding",
        "vectorizer": "none",
        "properties": [
            {"name": "docId",         "dataType": ["text"]},
            {"name": "chunkId",       "dataType": ["text"]},
            {"name": "chunkIdx",      "dataType": ["int"]},
            {"name": "text",          "dataType": ["text"]},
            {"name": "docType",       "dataType": ["text"]},
            {"name": "title",         "dataType": ["text"]},
            {"name": "pageNum",       "dataType": ["int"]},
            {"name": "version",       "dataType": ["int"]},
            {"name": "embeddedModel", "dataType": ["text"]},
            {"name": "indexedAt",     "dataType": ["date"]}
        ]
    }')

if [ "$HTTP_STATUS" = "200" ] || [ "$HTTP_STATUS" = "201" ]; then
    echo "KnowledgeChunk schema created (HTTP $HTTP_STATUS)."
elif [ "$HTTP_STATUS" = "422" ]; then
    echo "KnowledgeChunk schema already exists, skipping."
else
    echo "Error creating schema: HTTP $HTTP_STATUS" >&2
    exit 1
fi

echo "Weaviate initialized successfully."
