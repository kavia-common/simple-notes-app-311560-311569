"""FastAPI application entrypoint for the Notes backend.

Provides REST endpoints for managing notes with SQLite persistence.

Key routes:
- GET /            : Health check
- GET /notes       : List notes
- GET /notes/{id}  : Get note
- POST /notes      : Create note
- PUT /notes/{id}  : Update note
- DELETE /notes/{id}: Delete note
- GET /search?q=   : Search notes
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.db import init_db
from src.api.routes import router as notes_router

openapi_tags = [
    {
        "name": "system",
        "description": "Health and diagnostics endpoints.",
    },
    {
        "name": "notes",
        "description": "CRUD and search endpoints for notes.",
    },
]

app = FastAPI(
    title="Notes Backend API",
    description="Backend for a simple notes app (CRUD + search) using SQLite.",
    version="1.0.0",
    openapi_tags=openapi_tags,
)

# CORS for the React frontend (dev setup: localhost:3000). We keep '*' to reduce
# friction in this template environment, but you can tighten it later.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _on_startup() -> None:
    """Initialize database schema on application startup."""
    init_db()


@app.get(
    "/",
    tags=["system"],
    summary="Health check",
    description="Simple health check endpoint.",
    operation_id="health_check",
)
def health_check() -> dict:
    """Health check."""
    return {"message": "Healthy"}


app.include_router(notes_router)

