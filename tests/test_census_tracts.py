"""Tract-specific checks using synthetic demographics, without network access."""

import pytest

from boston_map.census_tracts import parse_tracts, tract_params


def payload_for(*tracts):
    header = tract_params()["get"].split(",") + ["state", "county", "tract"]
    rows = []
    for tract in tracts:
        row = dict.fromkeys(header, "0")
        row.update(NAME="Synthetic tract", state="25", county="025", tract=tract)
        rows.append([row[field] for field in header])
    return [header, *rows]


def test_tract_geoids_preserve_zeros_and_sort():
    records = parse_tracts(payload_for("000200", "000101"))
    assert [record["geoid"] for record in records] == ["25025000101", "25025000200"]
    assert records[0]["tract"] == "000101"
    assert records[0]["white_alone_vs_everyone_else"]["everyone_else"]["percent"] is None


def test_duplicate_tract_is_rejected():
    with pytest.raises(ValueError, match="Duplicate"):
        parse_tracts(payload_for("000101", "000101"))


@pytest.mark.parametrize("tract", ["101", "abcdef", None, "０００１０１"])
def test_invalid_tract_code_is_rejected(tract):
    with pytest.raises(ValueError, match="six-digit"):
        parse_tracts(payload_for(tract))


def test_wrong_county_is_rejected():
    payload = payload_for("000101")
    payload[1][-2] = "017"
    with pytest.raises(ValueError, match="outside Suffolk"):
        parse_tracts(payload)


def test_empty_dataset_is_rejected():
    with pytest.raises(ValueError, match="at least one"):
        parse_tracts(payload_for())
