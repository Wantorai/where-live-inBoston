"""Serve the API and a small frontend from one application."""

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
DATA_DIR = Path(os.environ.get("BOSTON_DATA_DIR", "data/processed"))

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


@app.get("/api/tracts", tags=["map"])
def tracts() -> FileResponse:
    """Serve the prepared county snapshot without contacting Census."""
    path = DATA_DIR / "suffolk_density_2024.geojson"
    if not path.is_file():
        raise HTTPException(status_code=503, detail="Prepared tract data is unavailable.")
    return FileResponse(path, media_type="application/geo+json")


@app.get("/api/metadata", tags=["map"])
def metadata() -> FileResponse:
    path = DATA_DIR / "suffolk_density_2024.metadata.json"
    if not path.is_file():
        raise HTTPException(status_code=503, detail="Prepared metadata is unavailable.")
    return FileResponse(path, media_type="application/json")
