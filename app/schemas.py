from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, description="User question about the PDF")


class SourceItem(BaseModel):
    chunk_id: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    section: str | None = None


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceItem]