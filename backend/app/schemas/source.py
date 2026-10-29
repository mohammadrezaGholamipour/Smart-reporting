from pydantic import BaseModel, ConfigDict
from datetime import datetime



class SourceRead(BaseModel):
    original_filename: str | None
    processed_at: datetime | None
    error_message: str | None
    page_count: int | None
    created_at: datetime
    source_type: str
    status: str
    name: str
    id: int

    model_config = ConfigDict(from_attributes=True)