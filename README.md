# Where Live in Boston

A Python geospatial portfolio project exploring residential population density in Boston using U.S. Census data.

**Status: minimal frontend, API, and Docker setup implemented.** The home page checks the API connection. The map and data pipeline are planned.

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

The architecture above is the target design. The backend uses Python and FastAPI; the data pipeline will also use Python. The frontend uses plain HTML, CSS, and JavaScript, with MapLibre GL JS proposed for the future map. FastAPI serves the frontend files and API from the same application. Frontend assets live in `src/boston_map/frontend/` so they are included in the installed Python package. Prepared GeoJSON files will provide the initial storage layer. TypeScript can be considered later if the browser code grows.

Docker Compose runs one container serving both the page and API. The map demo will include a small, documented real-data snapshot so reviewers do not need a Census API key or a data import to explore the map. Data refresh will be a separate workflow. Initial image builds and the future online basemap require internet access.

An optional Folium HTML export may be added later. Hosted deployment is outside the current scope.

## Get the repository

```bash
git clone https://github.com/Wantorai/where-live-inBoston.git
cd where-live-inBoston
```

## Run with Docker (recommended for reviewers)

Install and start Docker Desktop with Linux containers, or use Docker Engine with the Compose plugin on Linux. From the repository root:

```bash
docker compose up --build
```

Wait for `Application startup complete`, then open:

- <http://127.0.0.1:8000/> — home page with an automatic connection check.
- <http://127.0.0.1:8000/api/health> — HTTP 200 with `{"status":"ok"}`.
- <http://127.0.0.1:8000/docs> — interactive API documentation.

Python, uv, and Census credentials are not required on the host. The first build downloads base images and dependencies. The home page and API are available; the map and Census data are not implemented yet. Swagger UI in `/docs` loads assets from a CDN.

Stop with **Ctrl+C**, then remove the project's stopped container and network:

```bash
docker compose down
```

For background mode, wait for the container health check:

```bash
docker compose up --build --wait --wait-timeout 60
docker compose ps
docker compose logs api
```

`docker compose down` also stops a background run. It retains the built image for reuse. The health check confirms the API responds; it does not validate Census data.

Port 8000 is exposed only on the host's loopback interface. If it is occupied by a locally running Uvicorn process, stop that process first. Alternatively, change the mapping in `compose.yaml` to `127.0.0.1:8001:8000` and open port 8001 in your browser.

Source files are copied into the image. After code changes, run `docker compose up --build` again; this Docker setup does not use auto-reload or mount the host `.venv`.

## Run without Docker (development)

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then run these commands from the repository root:

```bash
uv sync --locked
uv run --locked uvicorn boston_map.api.main:app --reload
```

The project targets Python 3.12. uv can download the required interpreter and creates an isolated `.venv`; the first setup needs internet access. `uv.lock` records the resolved dependency versions. No Census credentials or Docker installation are required for this step.

- Home page: <http://127.0.0.1:8000/>
- Health endpoint: <http://127.0.0.1:8000/api/health>
- Interactive API documentation: <http://127.0.0.1:8000/docs>

The health endpoint returns HTTP 200 and `{"status":"ok"}`. It confirms the API responds, not that Census data is available. The root path `/` serves the connection-check page. It shows loading, success, or error and offers a retry button; requests time out after five seconds. The page uses only local assets and requires JavaScript for the connection check. The documentation page loads Swagger UI assets from a CDN.

Stop the development server with **Ctrl+C**. `--reload` restarts it when Python source files change and is intended for development.

## First Census request

A small command-line example requests the 2020–2024 ACS population estimate and margin of error for Boston city. This is a learning step before tract-level processing; it does not change the map's planned geography.

Copy `.env.example` to `.env` and set your activated `CENSUS_API_KEY`, then run from the repository root:

```bash
uv sync --locked
uv run --locked --env-file .env python -m boston_map.census
```

The first unauthenticated request returned a Census `Missing Key` page; a successful authenticated download is still pending. The example validates the response and saves successful data and key-free metadata in the ignored `data/raw/census/` directory. The existing web app still requires no Census key.

After a successful download, inspect it again without network access:

```bash
uv run --locked python -m boston_map.census --from-cache
```

See [request parameters, field definitions, and sources](data/README.md). The CLI runs separately from the web app; no population data is displayed on the page yet.

## Checks

```bash
uv run --locked pytest
uv run --locked ruff check .
uv run --locked ruff format --check .
```

The health test checks the HTTP status, JSON content type, and response body without starting a network server. Census parser tests use synthetic rows to check geography codes, numeric conversion, special missing-value codes, and malformed responses without contacting Census.

## Implementation roadmap

1. Agree on architecture and document the development workflow.
2. Create a minimal FastAPI service with a health endpoint — implemented.
3. Containerize the API and add a minimal HTML/JavaScript frontend — implemented.
4. Fetch Census population estimates and compatible boundaries.
5. Validate joins and land-area density calculations.
6. Implement map layers, tooltips, legend, and error states.
7. Verify a fresh-clone Docker demo and complete the portfolio documentation.

## Documentation

The public README is maintained in English and contains the current setup and verification instructions. Russian learning notes are kept locally under `docs/`, which is currently excluded from Git. Public Census documentation lives in [data/README.md](data/README.md).

Changes are developed in small, explained steps. The repository owner performs all pushes and any future deployments.
