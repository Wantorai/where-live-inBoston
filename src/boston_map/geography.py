"""Join Suffolk ACS tracts to 2024 TIGER/Line and compute land-area density."""

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests

SOURCE_URL = "https://www2.census.gov/geo/tiger/TIGER2024/TRACT/tl_2024_25_tract.zip"
ZIP_PATH = Path("data/raw/tiger/tl_2024_25_tract.zip")
ACS_PATH = Path("data/processed/suffolk_tracts_2024.json")
OUTPUT_PATH = Path("data/processed/suffolk_density_2024.geojson")


def join_density(boundaries: gpd.GeoDataFrame, records: list[dict]) -> gpd.GeoDataFrame:
    """Require an exact one-to-one county join; never clip or infer population."""
    required = {"STATEFP", "COUNTYFP", "GEOID", "ALAND", "AWATER", "geometry"}
    if not required.issubset(boundaries.columns) or boundaries.crs is None:
        raise ValueError("Boundaries need TIGER columns and a known coordinate system.")
    county = boundaries.loc[
        (boundaries["STATEFP"] == "25") & (boundaries["COUNTYFP"] == "025")
    ].copy()
    if county.empty or county["GEOID"].duplicated().any():
        raise ValueError("Expected nonempty, unique Suffolk tract geometries.")
    if (
        county.geometry.isna().any()
        or county.geometry.is_empty.any()
        or not county.geometry.is_valid.all()
        or not county.geom_type.isin(["Polygon", "MultiPolygon"]).all()
    ):
        raise ValueError("All tract geometries must be valid, nonempty polygons.")
    stats = pd.DataFrame(records)
    if stats.empty or stats["geoid"].duplicated().any():
        raise ValueError("Expected nonempty, unique ACS tract records.")
    geometry_ids, data_ids = set(county["GEOID"]), set(stats["geoid"])
    if geometry_ids != data_ids:
        raise ValueError(
            f"GEOID mismatch: missing geometry={sorted(data_ids - geometry_ids)}, "
            f"missing ACS={sorted(geometry_ids - data_ids)}"
        )
    for area in ("ALAND", "AWATER"):
        county[area] = pd.to_numeric(county[area], errors="raise")
        if county[area].isna().any() or (county[area] < 0).any():
            raise ValueError("TIGER areas must be nonnegative and present.")
    joined = county[["GEOID", "ALAND", "AWATER", "geometry"]].merge(
        stats, left_on="GEOID", right_on="geoid", validate="one_to_one"
    )
    joined = joined.drop(columns="GEOID").rename(
        columns={"ALAND": "land_area_m2", "AWATER": "water_area_m2"}
    )
    population = pd.to_numeric(joined["population_estimate"], errors="raise")
    if (population.dropna() < 0).any():
        raise ValueError("Population must be nonnegative or missing.")
    joined["land_area_km2"] = joined["land_area_m2"] / 1_000_000
    joined["population_density_km2"] = population / joined["land_area_km2"].where(
        joined["land_area_km2"] > 0
    )
    joined["density_status"] = "available"
    joined.loc[population.isna(), "density_status"] = "missing_population"
    joined.loc[joined["land_area_m2"] == 0, "density_status"] = "no_land_area"
    return joined.sort_values("geoid").to_crs("EPSG:4326")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-cache", action="store_true", help="Use the saved TIGER archive.")
    args = parser.parse_args()
    source_metadata_path = ZIP_PATH.with_suffix(".metadata.json")
    if args.from_cache:
        archive = ZIP_PATH.read_bytes()
        source = json.loads(source_metadata_path.read_text(encoding="utf-8"))
        if (
            source.get("url") != SOURCE_URL
            or source.get("sha256") != hashlib.sha256(archive).hexdigest()
        ):
            raise ValueError("TIGER cache does not match its source metadata.")
    else:
        try:
            response = requests.get(SOURCE_URL, timeout=60)
            response.raise_for_status()
        except requests.RequestException:
            raise ValueError("TIGER download failed; check the connection and retry.") from None
        archive = response.content
        if not archive.startswith(b"PK"):
            raise ValueError("Expected a TIGER ZIP archive.")
        source = {
            "url": SOURCE_URL,
            "vintage": 2024,
            "retrieved_at": datetime.now(UTC).isoformat(),
            "sha256": hashlib.sha256(archive).hexdigest(),
        }
        ZIP_PATH.parent.mkdir(parents=True, exist_ok=True)
        ZIP_PATH.write_bytes(archive)
        source_metadata_path.write_text(json.dumps(source, indent=2) + "\n", encoding="utf-8")
    acs_bytes = ACS_PATH.read_bytes()
    acs = json.loads(acs_bytes)
    if acs["metadata"].get("period") != "2020-2024":
        raise ValueError("Expected the ACS 2020-2024 dataset.")
    boundaries = gpd.read_file(f"zip://{ZIP_PATH.resolve().as_posix()}")
    joined = join_density(boundaries, acs["tracts"])
    geojson = joined.to_json(drop_id=True, na="null", to_wgs84=True)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(geojson + "\n", encoding="utf-8")
    metadata = {
        "scope": "Suffolk County, Massachusetts; all county tracts",
        "acs": acs["metadata"],
        "acs_file_sha256": hashlib.sha256(acs_bytes).hexdigest(),
        "tiger": source,
        "feature_count": len(joined),
        "crs": "EPSG:4326",
        "formula": "population_estimate / (ALAND / 1000000)",
        "density_unit": "people per square kilometer of land",
        "geometry_modified": False,
        "density_status_counts": joined["density_status"].value_counts().to_dict(),
        "population_sum": int(joined["population_estimate"].sum()),
        "geojson_sha256": hashlib.sha256((geojson + "\n").encode()).hexdigest(),
    }
    OUTPUT_PATH.with_suffix(".metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": str(OUTPUT_PATH),
                **{
                    key: metadata[key]
                    for key in ("feature_count", "density_status_counts", "population_sum")
                },
            },
            indent=2,
        )
    )
    print(
        joined[["geoid", "population_estimate", "land_area_km2", "population_density_km2"]]
        .head()
        .to_string(index=False)
    )


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as error:
        raise SystemExit(f"Geography: {error}") from None
