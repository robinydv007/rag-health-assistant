"""Weaviate schema definition for the KnowledgeChunk class."""

KNOWLEDGE_CHUNK_CLASS = {
    "class": "KnowledgeChunk",
    "description": "A single text chunk from a healthcare document with its embedding",
    "vectorizer": "none",
    "properties": [
        {"name": "docId",          "dataType": ["text"],   "description": "Document UUID"},
        {"name": "chunkId",        "dataType": ["text"],   "description": "Unique chunk ID"},
        {"name": "chunkIdx",       "dataType": ["int"],    "description": "Position within document"},
        {"name": "text",           "dataType": ["text"],   "description": "Chunk text (PII-scrubbed)"},
        {"name": "docType",        "dataType": ["text"],   "description": "Document category"},
        {"name": "title",          "dataType": ["text"],   "description": "Document title"},
        {"name": "pageNum",        "dataType": ["int"],    "description": "Source page number"},
        {"name": "version",        "dataType": ["int"],    "description": "Document version"},
        {"name": "embeddedModel",  "dataType": ["text"],   "description": "Model used to embed"},
        {"name": "indexedAt",      "dataType": ["date"],   "description": "When chunk was indexed"},
    ],
}

WEAVIATE_SCHEMA = {
    "classes": [KNOWLEDGE_CHUNK_CLASS]
}
