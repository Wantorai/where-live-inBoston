"""Download Suffolk County tract demographics; Boston boundary filtering comes later."""

import argparse
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from boston_map.census import ENDPOINT, fetch_data, parse_metrics, request_params

RAW_PATH = Path("data/raw/census/suffolk_tracts_2024.json")
OUTPUT_PATH = Path("data/processed/suffolk_tracts_2024.json")
SCOPE = "Suffolk County, Massachusetts; not filtered to Boston city"


def tract_params() -> dict[str, str]:
    return {**request_params(True), "for": "tract:*", "in": "state:25 county:025"}


def parse_tracts(payload: object) -> list[dict]:
    expected = tract_params()["get"].split(",") + ["state", "county", "tract"]
    if not isinstance(payload, list) or len(payload) < 2 or payload[0] != expected:
        raise ValueError("Expected a Census header and at least one tract row.")
    records = []
    seen = set()
    for values in payload[1:]:
        if not isinstance(values, list) or len(values) != len(expected):
            raise ValueError("Tract row does not match the expected columns.")
        row = dict(zip(expected, values, strict=True))
        if (row["state"], row["county"]) != ("25", "025"):
            raise ValueError("Response includes a geography outside Suffolk County.")
        tract = row["tract"]
        if (
            not isinstance(tract, str)
            or len(tract) != 6
            or not tract.isascii()
            or not tract.isdigit()
        ):
            raise ValueError("Expected a six-digit Census tract code.")
        geoid = row["state"] + row["county"] + tract
        if geoid in seen:
            raise ValueError(f"Duplicate tract GEOID: {geoid}.")
        seen.add(geoid)
        record = parse_metrics(row, geoid, demographics=True)
        record.update(state=row["state"], county=row["county"], tract=tract)
        records.append(record)
    return sorted(records, key=lambda record: record["geoid"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-cache", action="store_true", help="Rebuild from saved raw data.")
    args = parser.parse_args()
    metadata_path = RAW_PATH.with_suffix(".metadata.json")
    if args.from_cache:
        raw = RAW_PATH.read_bytes()
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata.get("sha256") != hashlib.sha256(raw).hexdigest():
            raise ValueError("Cached response checksum does not match its metadata.")
        if metadata.get("endpoint") != ENDPOINT or metadata.get("params") != tract_params():
            raise ValueError("Cached response uses a different dataset or geography.")
    else:
        key = os.environ.get("CENSUS_API_KEY", "").strip()
        if not key:
            raise ValueError("Set CENSUS_API_KEY in .env; use uv run --env-file .env.")
        raw = fetch_data(key, tract_params())
        metadata = {
            "endpoint": ENDPOINT,
            "params": tract_params(),
            "retrieved_at": datetime.now(UTC).isoformat(),
            "period": "2020-2024",
            "scope": SCOPE,
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
    records = parse_tracts(json.loads(raw))
    if not args.from_cache:
        RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
        RAW_PATH.write_bytes(raw)
        metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps({"metadata": metadata, "tracts": records}, indent=2) + "\n",
        encoding="utf-8",
    )
    populations = [record["population_estimate"] for record in records]
    print(
        json.dumps(
            {
                "scope": SCOPE,
                "tract_count": len(records),
                "population_sum": sum(value for value in populations if value is not None),
                "missing_population_count": populations.count(None),
                "zero_population_count": populations.count(0),
                "output": str(OUTPUT_PATH),
                "example": records[0],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as error:
        raise SystemExit(f"Census tracts: {error}") from None
