"""Synthetic examples test parsing; these numbers are not Census observations."""

import pytest

from boston_map.census import parse_population

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
