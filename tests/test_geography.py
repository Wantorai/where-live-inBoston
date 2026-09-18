"""Small synthetic polygons verify joins and density independently of Census downloads."""

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Polygon

from boston_map.geography import join_density


def boundaries():
    return gpd.GeoDataFrame(
        {
            "STATEFP": ["25"],
            "COUNTYFP": ["025"],
            "GEOID": ["25025000101"],
            "ALAND": [2_000_000],
            "AWATER": [3_000_000],
        },
        geometry=[Polygon([(-71, 42), (-70.99, 42), (-70.99, 42.01), (-71, 42)])],
        crs="EPSG:4269",
    )


def records(population=1000):
    return [{"geoid": "25025000101", "population_estimate": population}]


def test_density_uses_land_area_not_water_or_polygon_area():
    result = join_density(boundaries(), records())
    assert result.iloc[0]["land_area_km2"] == 2
    assert result.iloc[0]["population_density_km2"] == 500
    assert result.crs.to_epsg() == 4326


def test_zero_land_area_has_no_density():
    frame = boundaries()
    frame["ALAND"] = 0
    row = join_density(frame, records()).iloc[0]
    assert pd.isna(row["population_density_km2"])
    assert row["density_status"] == "no_land_area"


def test_zero_population_is_zero_density_but_missing_is_not():
    assert join_density(boundaries(), records(0)).iloc[0]["population_density_km2"] == 0
    row = join_density(boundaries(), records(None)).iloc[0]
    assert pd.isna(row["population_density_km2"])
    assert row["density_status"] == "missing_population"


def test_join_rejects_unmatched_ids():
    frame = boundaries()
    frame["GEOID"] = "25025000999"
    with pytest.raises(ValueError, match="GEOID mismatch"):
        join_density(frame, records())


def test_join_rejects_duplicate_records():
    with pytest.raises(ValueError, match="unique ACS"):
        join_density(boundaries(), records() * 2)


def test_invalid_polygon_is_rejected():
    frame = boundaries()
    frame.geometry = [Polygon([(0, 0), (1, 1), (1, 0), (0, 1), (0, 0)])]
    with pytest.raises(ValueError, match="valid, nonempty"):
        join_density(frame, records())


def test_unknown_crs_is_rejected():
    frame = boundaries().set_crs(None, allow_override=True)
    with pytest.raises(ValueError, match="coordinate system"):
        join_density(frame, records())
