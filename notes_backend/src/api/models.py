"""Pydantic models for the Notes API."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class NoteBase(BaseModel):
    """Common fields shared by Note create/update payloads."""

    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Short note title.",
        examples=["Grocery list"],
    )
    content: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Full note content.",
        examples=["Milk\nEggs\nBread"],
    )


class NoteCreate(NoteBase):
    """Payload for creating a note."""
    pass


class NoteUpdate(BaseModel):
    """Payload for updating a note (partial updates allowed)."""

    title: Optional[str] = Field(
        None,
        min_length=1,
        max_length=200,
        description="Updated title (optional).",
    )
    content: Optional[str] = Field(
        None,
        min_length=1,
        max_length=10000,
        description="Updated content (optional).",
    )


class Note(NoteBase):
    """Note as returned by the API."""

    id: int = Field(..., description="Note unique identifier.", examples=[1])
    created_at: str = Field(
        ..., description="Creation timestamp (SQLite datetime string)."
    )
    updated_at: str = Field(
        ..., description="Last update timestamp (SQLite datetime string)."
    )


class NotesList(BaseModel):
    """Wrapper for listing notes."""
    items: list[Note] = Field(..., description="Notes ordered by updated_at desc.")


class SearchResults(BaseModel):
    """Wrapper for search results."""
    q: str = Field(..., description="Original search query string.")
    items: list[Note] = Field(..., description="Matched notes.")
    total: int = Field(..., ge=0, description="Number of matched notes.")

