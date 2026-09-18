"""Serve the API and a small frontend from one application."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app = FastAPI(title="Where Live in Boston", version="0.1.0")
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    """Return the page; its JavaScript requests the health endpoint separately."""
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/api/health", tags=["health"])
def health() -> dict[str, str]:
    """Confirm the API responds; this does not check Census data readiness."""
    return {"status": "ok"}
