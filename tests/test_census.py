"""Synthetic examples test parsing; these numbers are not Census observations."""

import pytest

from boston_map.census import RACE_ORIGIN, RACES, parse_population, request_params

HEADER = ["NAME", "B01003_001E", "B01003_001M", "state", "place"]


def test_population_preserves_geography_and_converts_counts():
    result = parse_population([HEADER, ["Boston city, Massachusetts", "100", "12", "25", "07000"]])
    assert result["geoid"] == "2507000"
    assert result["population_estimate"] == 100
    assert result["population_moe"] == 12


@pytest.mark.parametrize("moe", ["-555555555", "-222222222", None])
def test_missing_or_special_moe_is_not_a_numeric_margin(moe):
    result = parse_population([HEADER, ["Boston city, Massachusetts", "100", moe, "25", "07000"]])
    assert result["population_moe"] is None
    assert result["population_moe_raw"] == moe


@pytest.mark.parametrize(
    "payload",
    [
        "<html>Missing Key</html>",
        [HEADER],
        [HEADER, ["Boston", "100", "12", "25"]],
        [HEADER, ["Other place", "100", "12", "25", "00001"]],
        [HEADER, ["Boston", "not a number", "12", "25", "07000"]],
    ],
)
def test_invalid_response_is_rejected(payload):
    with pytest.raises(ValueError):
        parse_population(payload)


def demographic_payload():
    """Synthetic partition: 40 White alone, 60 everyone else, total 100."""
    header = request_params(True)["get"].split(",") + ["state", "place"]
    row = dict.fromkeys(header, "0")
    row.update(NAME="Boston city, Massachusetts", state="25", place="07000")
    row["B01003_001E"] = "100"
    for table, groups in (("B02001", RACES), ("B03002", RACE_ORIGIN)):
        row[f"{table}_001E"] = "100"
        first, second, *_ = groups
        row[f"{table}_{first}E"] = "40"
        row[f"{table}_{second}E"] = "60"
    return [header, [row[field] for field in header]]


def test_demographic_partitions_and_complement():
    result = parse_population(demographic_payload(), demographics=True)
    split = result["white_alone_vs_everyone_else"]
    assert split["white_alone"]["estimate"] == 40
    assert split["everyone_else"]["estimate"] == 60
    assert split["everyone_else"]["percent"] == 60
    assert split["everyone_else"]["moe"] is None


def test_inconsistent_partition_is_rejected():
    payload = demographic_payload()
    payload[1][payload[0].index("B02001_003E")] = "59"
    with pytest.raises(ValueError, match="categories do not sum"):
        parse_population(payload, demographics=True)


def test_missing_white_estimate_does_not_become_zero():
    payload = demographic_payload()
    payload[1][payload[0].index("B02001_002E")] = "-666666666"
    result = parse_population(payload, demographics=True)
    assert result["white_alone_vs_everyone_else"]["everyone_else"]["estimate"] is None


def test_zero_population_has_no_percentage():
    payload = demographic_payload()
    for index, field in enumerate(payload[0]):
        if field.endswith("E") and field != "NAME":
            payload[1][index] = "0"
    result = parse_population(payload, demographics=True)
    assert result["white_alone_vs_everyone_else"]["everyone_else"]["percent"] is None
