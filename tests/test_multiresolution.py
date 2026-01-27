import geopandas as gpd
from shapely.geometry import Point

from m3s import GeohashGrid
from m3s.multiresolution import MultiResolutionGrid


def test_multiresolution_basic():
    factory = lambda p: GeohashGrid(precision=p)
    grid = MultiResolutionGrid(factory, [3, 4])

    bounds = (-74.2, 40.6, -73.8, 40.9)
    cells = grid.populate_region(bounds)
    assert 3 in cells and 4 in cells

    point = Point(-74.0060, 40.7128)
    hierarchy = grid.get_hierarchical_cells(point)
    assert 3 in hierarchy and 4 in hierarchy

    lod = grid.create_level_of_detail_view(bounds)
    assert isinstance(lod, gpd.GeoDataFrame)
