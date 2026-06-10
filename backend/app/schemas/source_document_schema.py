from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict


class SourceDocumentBase(BaseModel):
    source_name: str
    source_type: str
    source_url: str
    document_title: Optional[str] = None
    document_date: Optional[datetime] = None
    retrieved_at: datetime
    content_hash: str
    storage_path: str
    mime_type: Optional[str] = None
    file_size_bytes: Optional[int] = None
    raw_metadata_json: Optional[Dict[str, Any]] = None


class SourceDocumentCreate(SourceDocumentBase):
    pass


class SourceDocumentResponse(SourceDocumentBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IngestionRunBase(BaseModel):
    source_name: str
    run_status: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    records_found: int = 0
    records_saved: int = 0
    error_message: Optional[str] = None


class IngestionRunCreate(IngestionRunBase):
    pass


class IngestionRunResponse(IngestionRunBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)