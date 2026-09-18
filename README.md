# Where Live in Boston

A Python geospatial portfolio project exploring residential population density across Suffolk County, Massachusetts (Boston, Chelsea, Revere, and Winthrop), using U.S. Census data.

**Status: interactive density map implemented.** Explore 235 Suffolk County tracts, their population density, and demographic details. Docker includes the prepared data; no Census key is needed to view the map.

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

The backend uses Python and FastAPI; the data pipeline uses Python and GeoPandas. The frontend uses plain HTML, CSS, and JavaScript, with locally bundled MapLibre GL JS 5.6.2 for the map. FastAPI serves the frontend files and API from the same application. Frontend assets live in `src/boston_map/frontend/` so they are included in the installed Python package. Prepared GeoJSON files provide the storage layer. TypeScript can be considered later if the browser code grows.

Docker Compose runs one container serving both the page and API. The map demo includes a documented real-data snapshot so reviewers do not need a Census API key or a data import to explore the map. Data refresh is a separate workflow. Initial image builds and the optional online basemap require internet access.

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

- <http://127.0.0.1:8000/> вЂ” interactive population-density map.
- <http://127.0.0.1:8000/api/health> вЂ” HTTP 200 with `{"status":"ok"}`.
- <http://127.0.0.1:8000/docs> вЂ” interactive API documentation.

Python, uv, and Census credentials are not required on the host. The first build downloads base images and dependencies. The home page displays the prepared density map. Swagger UI in `/docs` loads assets from a CDN.

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

The health endpoint returns HTTP 200 and `{"status":"ok"}`. It confirms the API responds, not that Census data is available. The root path `/` serves the map. JavaScript and WebGL are required; loading failures offer a retry button. Census data and MapLibre assets are served locally. The documentation page loads Swagger UI assets from a CDN.

Stop the development server with **Ctrl+C**. `--reload` restarts it when Python source files change and is intended for development.

## First Census request

A small command-line example requests the 2020вЂ“2024 ACS population estimate and margin of error for Boston city. This is a learning step before tract-level processing; it does not change the map's planned geography.

Copy `.env.example` to `.env` and set your activated `CENSUS_API_KEY`, then run from the repository root:

```bash
uv sync --locked
uv run --locked --env-file .env python -m boston_map.census
```

Authenticated city-level population and demographic downloads succeeded on September 18, 2026. Census requires an activated API key for downloads. The example validates the response and saves successful data and key-free metadata in the ignored `data/raw/census/` directory. The existing web app still requires no Census key.

After a successful download, inspect it again without network access:

```bash
uv run --locked python -m boston_map.census --from-cache
```

Add `--demographics` to collect race (B02001) and race/origin (B03002) estimates and margins of error in the same request. The output includes White alone versus everyone else; multiracial people belong to the latter group. Use `--demographics --from-cache` to inspect the saved demographic response.

See [request parameters, field definitions, and sources](data/README.md). The CLI refreshes data separately from the web app; the page reads the prepared snapshot.

## Census tracts: county acquisition

Download the same population and demographic fields for all Suffolk County tracts:

```bash
uv run --locked --env-file .env python -m boston_map.census_tracts
```

Rebuild the normalized snapshot from the saved raw response:

```bash
uv run --locked python -m boston_map.census_tracts --from-cache
```

The checked-in `data/processed/suffolk_tracts_2024.json` contains 235 tracts, source metadata, estimates, count margins of error, and derived percentages. **The map covers all of Suffolk County.** All 235 tracts remain in scope; no Boston city clipping is planned. Tract boundaries have now been joined by GEOID and land-area density calculated in the separate GeoJSON described below. The web app displays the geographic version of this snapshot. Refreshing requires a key; inspecting the included JSON does not.

## Prepare geographic boundaries and density

From the repository root:

```bash
uv sync --locked
uv run --locked python -m boston_map.geography
```

This downloads the official Massachusetts TIGER/Line 2024 tract archive (no Census API key needed), selects Suffolk County, and joins the included ACS snapshot by GEOID. The output is `data/processed/suffolk_density_2024.geojson`, with source metadata in the adjacent `.metadata.json` file. Both are intended for Git.

```bash
uv run --locked python -m boston_map.geography --from-cache
```

The cached command rebuilds without network access, after verifying the archive checksum. All 235 tracts match one-to-one. Density is population divided by land area in square kilometers: 234 tracts have a result, and one zero-land-area tract has a null density. Geometry is exported in WGS84 without clipping or simplification. Demographic values and margins of error are retained.

This preparation command runs on the host with uv. Docker includes the prepared GeoJSON and metadata. Rebuild the image after refreshing data.

## Checks

```bash
uv run --locked pytest
uv run --locked ruff check .
uv run --locked ruff format --check .
```

The health test checks the HTTP status, JSON content type, and response body without starting a network server. Census parser tests use synthetic rows to check geography codes, numeric conversion, special missing-value codes, and malformed responses without contacting Census.

## Implementation roadmap

1. Agree on architecture and document the development workflow.
2. Create a minimal FastAPI service with a health endpoint вЂ” implemented.
3. Containerize the API and add a minimal HTML/JavaScript frontend вЂ” implemented.
4. Fetch Census population estimates and compatible boundaries.
5. Validate joins and land-area density calculations вЂ” implemented for all 235 Suffolk tracts.
6. Implement density layer, tooltips, tract details, legend, and error states вЂ” implemented. Boston neighborhood outlines remain a later step.
7. Verify a fresh-clone Docker demo and complete the portfolio documentation.

## Documentation

The public README is maintained in English and contains the current setup and verification instructions. Russian learning notes are kept locally under `docs/`, which is currently excluded from Git. Public Census documentation lives in [data/README.md](data/README.md).

Changes are developed in small, explained steps. The repository owner performs all pushes and any future deployments.

## Using the map

- Pan and zoom; hover over a tract for its density and click for full details.
- The tract selector offers the same details through a keyboard-accessible control.
- Colors use fixed density thresholds: 1,000, 5,000, 10,000, 20,000, and 30,000 people/kmВІ. Gray means missing density, not zero.
- Details show population and White-alone count MOEs, land area, density, and White alone versus everyone else. Percentage and derived-count MOEs are not calculated.
- Full tract polygons include water; the density denominator uses land area only. This explains the large offshore polygon with no density.
- The default map needs no external map requests after local startup. Optional OpenStreetMap streets need internet; attribution is shown on the map. Tiles are requested directly by the browser, with no prefetching or offline tile downloads.
- `GET /api/tracts` serves the prepared GeoJSON; `GET /api/metadata` serves provenance. Missing files return HTTP 503. These routes never contact Census.
- Run local commands from the repository root. `BOSTON_DATA_DIR` can override the default `data/processed` directory when launching elsewhere.

MapLibre GL JS 5.6.2 is bundled under `src/boston_map/frontend/vendor/` with its BSD-3-Clause license. Sources: [MapLibre distribution](https://unpkg.com/maplibre-gl@5.6.2/), [OpenStreetMap tile policy](https://operations.osmfoundation.org/policies/tiles/). Data attribution: U.S. Census Bureau, ACS 2020вЂ“2024 and TIGER/Line 2024.
