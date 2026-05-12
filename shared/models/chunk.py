from pydantic import BaseModel

from shared.models.document import DocType


class ChunkMetadata(BaseModel):
    doc_type: DocType
    page_num: int
    chunk_idx: int
    version: int
    target_index: str = "live"
