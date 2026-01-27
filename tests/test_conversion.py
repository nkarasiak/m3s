import pandas as pd
import pytest

from m3s import GeohashGrid, H3Grid, Cell
from m3s.conversion import GridConverter, convert_cell, convert_cells, get_equivalent_precision


def test_converter_basic():
    converter = GridConverter()
    geohash = converter._get_grid("geohash")
    assert isinstance(geohash, GeohashGrid)

    h3 = converter._get_grid("h3", 8)
    assert isinstance(h3, H3Grid)


def test_convert_cell_centroid():
    converter = GridConverter()
    cell = GeohashGrid(precision=5).cell(40.7128, -74.0060)
    target = converter.convert_cell(cell, "h3", method="centroid")
    assert isinstance(target, Cell)


def test_convert_cells_batch():
    converter = GridConverter()
    cells = [
        GeohashGrid(precision=5).cell(40.7128, -74.0060),
        GeohashGrid(precision=5).cell(34.0522, -118.2437),
    ]
    results = converter.convert_cells_batch(cells, "h3")
    assert len(results) == 2


def test_create_conversion_table():
    converter = GridConverter()
    bounds = (-74.01, 40.71, -74.00, 40.72)
    table = converter.create_conversion_table("geohash", "h3", bounds)
    assert isinstance(table, pd.DataFrame)
    assert len(table) > 0


def test_equivalent_precision():
    converter = GridConverter()
    eq = converter.get_equivalent_precision("geohash", 5, "h3")
    assert isinstance(eq, int)


def test_convenience_functions():
    cell = GeohashGrid(precision=5).cell(40.7128, -74.0060)
    result = convert_cell(cell, "h3")
    assert isinstance(result, Cell)

    results = convert_cells([cell], "h3")
    assert len(results) == 1

    eq = get_equivalent_precision("geohash", 5, "h3")
    assert isinstance(eq, int)
