import geopandas as gpd
from shapely.geometry import Point

from m3s import GeohashGrid
from m3s.parallel import ParallelConfig, ParallelGridEngine


def test_parallel_intersect_threaded():
    gdf = gpd.GeoDataFrame(
        {"name": ["NYC", "LA"]},
        geometry=[Point(-74.0060, 40.7128), Point(-118.2437, 34.0522)],
        crs="EPSG:4326",
    )

    grid = GeohashGrid(precision=5)
    engine = ParallelGridEngine(ParallelConfig(use_processes=False))
    result = engine.intersect_parallel(grid, gdf)
    assert isinstance(result, gpd.GeoDataFrame)
    assert len(result) > 0
