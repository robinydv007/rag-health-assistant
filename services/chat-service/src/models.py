"""Shared data models for the chat-service (no heavy dependencies)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SearchResult:
    doc_id: str
    chunk_id: str
    text: str
    title: str
    page_num: int
    score: float
