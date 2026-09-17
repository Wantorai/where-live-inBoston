FROM python:3.12.13-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.10.9 /uv /usr/local/bin/uv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Install locked runtime dependencies before copying the application source.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project --no-cache

COPY README.md ./
COPY src/ ./src/
RUN uv sync --locked --no-dev --no-editable --no-cache

RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "boston_map.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
