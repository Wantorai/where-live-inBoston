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
DEMOGRAPHICS_PATH = Path("data/raw/census/boston_demographics_2024.json")
RACES = {
    "002": "White alone",
    "003": "Black or African American alone",
    "004": "American Indian and Alaska Native alone",
    "005": "Asian alone",
    "006": "Native Hawaiian and Other Pacific Islander alone",
    "007": "Some other race alone",
    "008": "Two or more races",
}
RACE_ORIGIN = {
    "003": "Not Hispanic or Latino: White alone",
    "004": "Not Hispanic or Latino: Black or African American alone",
    "005": "Not Hispanic or Latino: American Indian and Alaska Native alone",
    "006": "Not Hispanic or Latino: Asian alone",
    "007": "Not Hispanic or Latino: Native Hawaiian and Other Pacific Islander alone",
    "008": "Not Hispanic or Latino: Some other race alone",
    "009": "Not Hispanic or Latino: Two or more races",
    "012": "Hispanic or Latino: any race",
}


def request_params(demographics: bool = False) -> dict[str, str]:
    params = PARAMS.copy()
    if demographics:
        fields = [
            f"{table}_{code}{suffix}"
            for table, groups in (("B02001", RACES), ("B03002", RACE_ORIGIN))
            for code in ("001", *groups)
            for suffix in ("E", "M")
        ]
        params["get"] += "," + ",".join(fields)
    return params


def parse_population(payload: object, *, demographics: bool = False) -> dict:
    """Validate this single-city response; preserve Census codes as strings."""
    expected = request_params(demographics)["get"].split(",") + ["state", "place"]
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

    result = {
        "name": row["NAME"],
        "geoid": row["state"] + row["place"],
        "period": "2020-2024",
        "population_estimate": count("B01003_001E"),
        "population_moe": count("B01003_001M"),
        "population_estimate_raw": row["B01003_001E"],
        "population_moe_raw": row["B01003_001M"],
    }
    if demographics:
        for table, groups, name in (
            ("B02001", RACES, "race"),
            ("B03002", RACE_ORIGIN, "race_and_origin"),
        ):
            total = count(f"{table}_001E")
            if total is not None and total != result["population_estimate"]:
                raise ValueError(f"{table} total differs from the population estimate.")
            categories = []
            for code, label in groups.items():
                variable = f"{table}_{code}"
                estimate = count(variable + "E")
                if total is not None and estimate is not None and estimate > total:
                    raise ValueError(f"{variable} exceeds its table total.")
                categories.append(
                    {
                        "variable": variable,
                        "label": label,
                        "estimate": estimate,
                        "moe": count(variable + "M"),
                        "estimate_raw": row[variable + "E"],
                        "moe_raw": row[variable + "M"],
                        "percent": round(100 * estimate / total, 2)
                        if total and estimate is not None
                        else None,
                    }
                )
            estimates = [category["estimate"] for category in categories]
            if total is not None and all(value is not None for value in estimates):
                if sum(estimates) != total:
                    raise ValueError(f"{table} categories do not sum to their table total.")
            result[name] = {"table": table, "total": total, "categories": categories}
        population = result["race"]["total"]
        white = result["race"]["categories"][0]
        other = (
            population - white["estimate"]
            if (population is not None and white["estimate"] is not None)
            else None
        )
        result["white_alone_vs_everyone_else"] = {
            "definition": (
                "White alone, regardless of Hispanic/Latino origin; "
                "all others include multiracial people."
            ),
            "white_alone": white,
            "everyone_else": {
                "estimate": other,
                "percent": round(100 * other / population, 2)
                if population and other is not None
                else None,
                "moe": None,
                "moe_note": "Derived difference; margin of error has not been calculated.",
            },
        }
    return result


def fetch_population(api_key: str, *, demographics: bool = False) -> bytes:
    """Make one request; do not expose the key through URLs or exception messages."""
    try:
        response = requests.get(
            ENDPOINT,
            params={**request_params(demographics), "key": api_key},
            timeout=30,
            allow_redirects=False,
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
    parser.add_argument(
        "--demographics", action="store_true", help="Include race and origin tables."
    )
    args = parser.parse_args()
    raw_path = DEMOGRAPHICS_PATH if args.demographics else RAW_PATH
    if args.from_cache:
        raw = raw_path.read_bytes()
    else:
        key = os.environ.get("CENSUS_API_KEY", "").strip()
        if not key:
            raise ValueError("Set CENSUS_API_KEY in .env; use uv run --env-file .env.")
        raw = fetch_population(key, demographics=args.demographics)
    result = parse_population(json.loads(raw), demographics=args.demographics)
    if not args.from_cache:
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_bytes(raw)
        metadata = {
            "endpoint": ENDPOINT,
            "params": request_params(args.demographics),
            "retrieved_at": datetime.now(UTC).isoformat(),
            "period": "2020-2024",
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
        raw_path.with_suffix(".metadata.json").write_text(
            json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
        )
    print(json.dumps(result, indent=2))
    print(f"Raw response: {raw_path}")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as error:
        raise SystemExit(f"Census example: {error}") from None
