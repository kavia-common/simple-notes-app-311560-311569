"""API routes for Notes CRUD and search."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from src.api.db import fetch_note, get_connection, now_iso
from src.api.models import Note, NoteCreate, NoteUpdate, NotesList, SearchResults

router = APIRouter(tags=["notes"])


@router.get(
    "/notes",
    response_model=NotesList,
    summary="List notes",
    description="Returns all notes ordered by most recently updated.",
    operation_id="list_notes",
)
def list_notes() -> NotesList:
    """List all notes."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, title, content, created_at, updated_at
            FROM notes
            ORDER BY updated_at DESC, id DESC;
            """
        ).fetchall()
        return NotesList(items=rows)  # type: ignore[arg-type]


@router.get(
    "/notes/{note_id}",
    response_model=Note,
    summary="Get a note",
    description="Fetch a single note by its id.",
    operation_id="get_note",
)
def get_note(note_id: int) -> Note:
    """Get a note by id."""
    with get_connection() as conn:
        row = fetch_note(conn, note_id)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Note {note_id} not found",
            )
        return row  # type: ignore[return-value]


@router.post(
    "/notes",
    response_model=Note,
    status_code=status.HTTP_201_CREATED,
    summary="Create a note",
    description="Create a new note with title and content.",
    operation_id="create_note",
)
def create_note(payload: NoteCreate) -> Note:
    """Create a new note."""
    with get_connection() as conn:
        ts = now_iso(conn)
        cur = conn.execute(
            """
            INSERT INTO notes (title, content, created_at, updated_at)
            VALUES (?, ?, ?, ?);
            """,
            (payload.title.strip(), payload.content, ts, ts),
        )
        conn.commit()
        note_id = int(cur.lastrowid)
        row = fetch_note(conn, note_id)
        # Should always exist immediately after insert
        return row  # type: ignore[return-value]


@router.put(
    "/notes/{note_id}",
    response_model=Note,
    summary="Update a note",
    description="Update title/content for an existing note.",
    operation_id="update_note",
)
def update_note(note_id: int, payload: NoteUpdate) -> Note:
    """Update an existing note."""
    if payload.title is None and payload.content is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one of 'title' or 'content' must be provided",
        )

    with get_connection() as conn:
        existing = fetch_note(conn, note_id)
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Note {note_id} not found",
            )

        new_title = (
            payload.title.strip()
            if payload.title is not None
            else existing["title"]
        )
        new_content = payload.content if payload.content is not None else existing["content"]
        ts = now_iso(conn)

        conn.execute(
            """
            UPDATE notes
            SET title = ?, content = ?, updated_at = ?
            WHERE id = ?;
            """,
            (new_title, new_content, ts, note_id),
        )
        conn.commit()
        row = fetch_note(conn, note_id)
        return row  # type: ignore[return-value]


@router.delete(
    "/notes/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a note",
    description="Delete a note by id.",
    operation_id="delete_note",
)
def delete_note(note_id: int) -> None:
    """Delete a note."""
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM notes WHERE id = ?;", (note_id,))
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Note {note_id} not found",
            )
        return None


@router.get(
    "/search",
    response_model=SearchResults,
    summary="Search notes",
    description="Search notes by title/content using a case-insensitive substring match.",
    operation_id="search_notes",
)
def search_notes(
    q: str = Query(
        ...,
        min_length=1,
        max_length=200,
        description="Search query string.",
        examples=["grocery"],
    ),
    limit: int = Query(
        50, ge=1, le=200, description="Maximum number of results to return."
    ),
) -> SearchResults:
    """Search notes by title/content."""
    q_norm = q.strip()
    like = f"%{q_norm}%"

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, title, content, created_at, updated_at
            FROM notes
            WHERE title LIKE ? COLLATE NOCASE
               OR content LIKE ? COLLATE NOCASE
            ORDER BY updated_at DESC, id DESC
            LIMIT ?;
            """,
            (like, like, limit),
        ).fetchall()

        total_row = conn.execute(
            """
            SELECT COUNT(*) as cnt
            FROM notes
            WHERE title LIKE ? COLLATE NOCASE
               OR content LIKE ? COLLATE NOCASE;
            """,
            (like, like),
        ).fetchone()

        total = int(total_row["cnt"]) if total_row else 0
        return SearchResults(q=q_norm, items=rows, total=total)  # type: ignore[arg-type]

