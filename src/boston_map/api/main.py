"""Application entry point and initial health endpoint."""

from fastapi import FastAPI

app = FastAPI(title="Where Live in Boston", version="0.1.0")


@app.get("/api/health", tags=["health"])
def health() -> dict[str, str]:
    """Confirm the API responds; this does not check Census data readiness."""
    return {"status": "ok"}
