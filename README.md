# Where Live in Boston

A Python geospatial portfolio project exploring residential population density in Boston using U.S. Census data.

**Status: planning.** The application and Docker setup are not implemented yet.

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

The backend and data pipeline use Python. The proposed frontend uses TypeScript, Vite, and MapLibre GL JS; this choice will be reviewed before frontend implementation. Prepared GeoJSON files provide the initial storage layer.

Docker Compose will run the API and frontend locally. The demo will include a small, documented real-data snapshot so reviewers do not need a Census API key or a data import to explore the map. Data refresh will be a separate workflow. Initial image builds and the online basemap require internet access.

An optional Folium HTML export may be added later. Hosted deployment is outside the current scope.

## Get the repository

```bash
git clone https://github.com/Wantorai/where-live-inBoston.git
cd where-live-inBoston
```

The intended demo workflow is `docker compose up --build`, then opening a documented localhost URL. **This command is a design target, not a working launch instruction yet.** Tested startup and shutdown instructions will be added with the Docker implementation.

## Implementation roadmap

1. Agree on architecture and document the development workflow.
2. Create a minimal FastAPI service with a health endpoint.
3. Containerize the API, then add a minimal separate frontend.
4. Fetch Census population estimates and compatible boundaries.
5. Validate joins and land-area density calculations.
6. Implement map layers, tooltips, legend, and error states.
7. Verify a fresh-clone Docker demo and complete the portfolio documentation.

## Documentation

The public README is maintained in English. Learning notes and implementation discussions are currently in Russian.

- [Implementation plan and Raleigh comparison](docs/plan.md)
- [Data sources and methodology](docs/data-methodology.md)
- [Local Git workflow](docs/git-workflow.md)

Changes are developed in small, explained steps. The repository owner performs all pushes and any future deployments.
