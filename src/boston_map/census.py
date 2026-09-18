"""Fetch and inspect one ACS population row for Boston city, Massachusetts."""

import argparse
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import requests

ENDPOINT = "https://api.census.gov/data/2024/acs/acs5"
PARAMS = {
    "get": "NAME,B01003_001E,B01003_001M",
    "for": "place:07000",
    "in": "state:25",
}
RAW_PATH = Path("data/raw/census/boston_population_2024.json")


def parse_population(payload: object) -> dict:
    """Validate this single-city response; preserve Census codes as strings."""
    expected = ["NAME", "B01003_001E", "B01003_001M", "state", "place"]
    if not isinstance(payload, list) or len(payload) != 2 or payload[0] != expected:
        raise ValueError("Expected a header and exactly one Boston population row.")
    values = payload[1]
    if not isinstance(values, list) or len(values) != len(expected):
        raise ValueError("Population row does not match the expected columns.")
    row = dict(zip(expected, values, strict=True))
    if (row["state"], row["place"]) != ("25", "07000"):
        raise ValueError("Response geography is not Boston city, Massachusetts.")
    if not isinstance(row["NAME"], str):
        raise ValueError("Expected a geographic name.")

    def count(field: str) -> int | None:
        value = row[field]
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError(f"Expected a Census string or null for {field}.")
        try:
            number = int(value)
        except ValueError:
            raise ValueError(f"Expected a numeric Census value for {field}.") from None
        # Negative ACS values are special codes, not negative people or uncertainty.
        return number if number >= 0 else None

    return {
        "name": row["NAME"],
        "geoid": row["state"] + row["place"],
        "period": "2020-2024",
        "population_estimate": count("B01003_001E"),
        "population_moe": count("B01003_001M"),
        "population_estimate_raw": row["B01003_001E"],
        "population_moe_raw": row["B01003_001M"],
    }


def fetch_population(api_key: str) -> bytes:
    """Make one request; do not expose the key through URLs or exception messages."""
    try:
        response = requests.get(
            ENDPOINT, params={**PARAMS, "key": api_key}, timeout=30, allow_redirects=False
        )
    except requests.RequestException:
        raise ValueError("Census request failed. Check your connection and try again.") from None
    if response.status_code != 200:
        raise ValueError(f"Census returned HTTP {response.status_code}. Check your API key.")
    if "application/json" not in response.headers.get("Content-Type", "").lower():
        raise ValueError("Census did not return JSON. Check that your API key is activated.")
    return response.content


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-cache", action="store_true", help="Read saved data without HTTP.")
    args = parser.parse_args()
    if args.from_cache:
        raw = RAW_PATH.read_bytes()
    else:
        key = os.environ.get("CENSUS_API_KEY", "").strip()
        if not key:
            raise ValueError("Set CENSUS_API_KEY in .env; use uv run --env-file .env.")
        raw = fetch_population(key)
    result = parse_population(json.loads(raw))
    if not args.from_cache:
        RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
        RAW_PATH.write_bytes(raw)
        metadata = {
            "endpoint": ENDPOINT,
            "params": PARAMS,
            "retrieved_at": datetime.now(UTC).isoformat(),
            "period": "2020-2024",
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
        RAW_PATH.with_suffix(".metadata.json").write_text(
            json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
        )
    print(json.dumps(result, indent=2))
    print(f"Raw response: {RAW_PATH}")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as error:
        raise SystemExit(f"Census example: {error}") from None
