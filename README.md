# Where Live in Boston

A Python geospatial portfolio project exploring residential population density in Boston using U.S. Census data.

**Status: initial API implemented.** `GET /api/health` returns `{"status":"ok"}`. The map, data pipeline, frontend, and Docker setup are planned.

## MVP

- An interactive population-density map at the Census tract level.
- Boston neighborhood outlines as a separate reference layer.
- A legend and tract details: population estimates, land area, density, data period, and population margin of error.
- Documented sources, reproducible data preparation, and a local Docker demo.

Population density describes residential concentration; it is not a neighborhood quality score.

## Architecture and stack

```text
Census API + TIGER/Line + neighborhood boundaries
                         |
              Python data preparation
               pandas / GeoPandas
                         |
                GeoJSON + metadata
                         |
                    FastAPI
                         |
               Separate web frontend
```

The architecture above is the target design. The backend uses Python and FastAPI; the data pipeline will also use Python. The planned frontend uses plain HTML, CSS, and JavaScript, with MapLibre GL JS proposed for the map. FastAPI will serve the frontend files and API from the same application. Prepared GeoJSON files will provide the initial storage layer. TypeScript can be considered later if the browser code grows.

Docker Compose will run one application container serving both the API and frontend locally. The demo will include a small, documented real-data snapshot so reviewers do not need a Census API key or a data import to explore the map. Data refresh will be a separate workflow. Initial image builds and the online basemap require internet access.

An optional Folium HTML export may be added later. Hosted deployment is outside the current scope.

## Get the repository

```bash
git clone https://github.com/Wantorai/where-live-inBoston.git
cd where-live-inBoston
```

## Run the API locally

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then run these commands from the repository root:

```bash
uv sync --locked
uv run --locked uvicorn boston_map.api.main:app --reload
```

The project targets Python 3.12. uv can download the required interpreter and creates an isolated `.venv`; the first setup needs internet access. `uv.lock` records the resolved dependency versions. No Census credentials or Docker installation are required for this step.

- Health endpoint: <http://127.0.0.1:8000/api/health>
- Interactive API documentation: <http://127.0.0.1:8000/docs>

The health endpoint returns HTTP 200 and `{"status":"ok"}`. It confirms the API responds, not that Census data is available. The root path `/` currently returns 404 because the frontend is not implemented. The documentation page loads Swagger UI assets from a CDN.

Stop the development server with **Ctrl+C**. `--reload` restarts it when Python source files change and is intended for development.

## Checks

```bash
uv run --locked pytest
uv run --locked ruff check .
uv run --locked ruff format --check .
```

The health test checks the HTTP status, JSON content type, and response body without starting a network server.

## Planned Docker demo

The intended demo workflow is `docker compose up --build`, then opening a documented localhost URL. **This command is a design target, not a working launch instruction yet.** Tested startup and shutdown instructions will be added with the Docker implementation.

## Implementation roadmap

1. Agree on architecture and document the development workflow.
2. Create a minimal FastAPI service with a health endpoint — implemented.
3. Containerize the API, then add a minimal HTML/JavaScript frontend.
4. Fetch Census population estimates and compatible boundaries.
5. Validate joins and land-area density calculations.
6. Implement map layers, tooltips, legend, and error states.
7. Verify a fresh-clone Docker demo and complete the portfolio documentation.

## Documentation

The public README is maintained in English and contains the current setup and verification instructions. Russian learning notes are kept locally under `docs/`, which is currently excluded from Git. Public data-source and methodology documentation will be added alongside the data pipeline.

Changes are developed in small, explained steps. The repository owner performs all pushes and any future deployments.

