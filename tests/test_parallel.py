"""
Tests for parallel processing functionality in M3S.
"""

import warnings
from unittest.mock import Mock, patch

import geopandas as gpd
import pytest
from shapely.geometry import Point

from m3s import GeohashGrid, H3Grid
from m3s.parallel import (
    GridStreamProcessor,
    ParallelConfig,
    ParallelGridEngine,
    create_data_stream,
    create_file_stream,
    parallel_intersect,
    stream_grid_processing,
)


class TestParallelConfig:
    """Test ParallelConfig class."""

    def test_default_config(self):
        """Test default configuration."""
        config = ParallelConfig()
        assert config.chunk_size == 10000
        assert config.memory_limit == "2GB"
        assert config.threads_per_worker == 2
        assert config.scheduler_address is None

    def test_custom_config(self):
        """Test custom configuration."""
        config = ParallelConfig(
            chunk_size=5000, memory_limit="4GB", threads_per_worker=4, n_workers=8
        )
        assert config.chunk_size == 5000
        assert config.memory_limit == "4GB"
        assert config.threads_per_worker == 4
        assert config.n_workers == 8

    def test_fallback_when_dask_unavailable(self):
        """Test fallback when Dask is unavailable."""
        with patch("m3s.parallel.DASK_AVAILABLE", False):
            config = ParallelConfig(use_dask=True)
            assert config.use_dask is False

    def test_fallback_when_gpu_unavailable(self):
        """Test fallback when GPU is unavailable."""
        with patch("m3s.parallel.GPU_AVAILABLE", False):
            config = ParallelConfig(use_gpu=True)
            assert config.use_gpu is False


class TestGridStreamProcessor:
    """Test GridStreamProcessor class."""

    @pytest.fixture
    def sample_grid(self):
        """Create a sample grid for testing."""
        return GeohashGrid(precision=5)

    @pytest.fixture
    def sample_gdf(self):
        """Create sample GeoDataFrame."""
        geometries = [
            Point(-74.0060, 40.7128),  # NYC
            Point(-118.2437, 34.0522),  # LA
        ]
        data = {"name": ["NYC", "LA"], "value": [100, 200]}
        return gpd.GeoDataFrame(data, geometry=geometries, crs="EPSG:4326")

    def test_process_chunk(self, sample_grid, sample_gdf):
        """Test processing a single chunk."""
        processor = GridStreamProcessor(sample_grid)
        result = processor.process_chunk(sample_gdf)

        assert isinstance(result, gpd.GeoDataFrame)
        assert len(result) >= 2  # At least one cell per point
        assert "cell_id" in result.columns
        assert "name" in result.columns

    def test_combine_results(self, sample_grid, sample_gdf):
        """Test combining multiple results."""
        processor = GridStreamProcessor(sample_grid)

        # Create multiple chunks
        chunk1 = sample_gdf.iloc[:1]
        chunk2 = sample_gdf.iloc[1:]

        result1 = processor.process_chunk(chunk1)
        result2 = processor.process_chunk(chunk2)

        combined = processor.combine_results([result1, result2])

        assert isinstance(combined, gpd.GeoDataFrame)
        assert len(combined) == len(result1) + len(result2)
        assert combined.crs == result1.crs

    def test_combine_empty_results(self, sample_grid):
        """Test combining empty results."""
        processor = GridStreamProcessor(sample_grid)
        combined = processor.combine_results([])

        assert isinstance(combined, gpd.GeoDataFrame)
        assert len(combined) == 0


class TestParallelGridEngine:
    """Test ParallelGridEngine class."""

    @pytest.fixture
    def sample_gdf_large(self):
        """Create a larger sample GeoDataFrame for parallel testing."""
        # Create a grid of points for testing
        lats = [40.7 + i * 0.01 for i in range(100)]
        lons = [-74.0 + i * 0.01 for i in range(100)]

        geometries = [Point(lon, lat) for lat, lon in zip(lats, lons)]
        data = {
            "id": range(len(geometries)),
            "value": [i * 10 for i in range(len(geometries))],
        }
        return gpd.GeoDataFrame(data, geometry=geometries, crs="EPSG:4326")

    @pytest.fixture
    def sample_grid(self):
        """Create a sample grid."""
        return GeohashGrid(precision=5)

    def test_engine_initialization(self):
        """Test engine initialization."""
        config = ParallelConfig(use_dask=False, use_gpu=False)
        engine = ParallelGridEngine(config)

        assert engine.config is not None
        assert not engine.config.use_dask
        assert not engine.config.use_gpu

    def test_intersect_parallel_threaded(self, sample_grid, sample_gdf_large):
        """Test parallel intersection using threading."""
        config = ParallelConfig(use_dask=False, use_gpu=False, chunk_size=25)
        engine = ParallelGridEngine(config)

        result = engine.intersect_parallel(sample_grid, sample_gdf_large, chunk_size=25)

        assert isinstance(result, gpd.GeoDataFrame)
        assert len(result) >= len(sample_gdf_large)  # At least one cell per point
        assert "cell_id" in result.columns
        assert result.crs == sample_gdf_large.crs

    def test_intersect_parallel_empty_input(self, sample_grid):
        """Test parallel intersection with empty input."""
        config = ParallelConfig(use_dask=False)
        engine = ParallelGridEngine(config)

        empty_gdf = gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
        result = engine.intersect_parallel(sample_grid, empty_gdf)

        assert isinstance(result, gpd.GeoDataFrame)
        assert len(result) == 0

    def test_intersect_parallel_small_input(self, sample_grid):
        """Test parallel intersection with small input (no chunking)."""
        config = ParallelConfig(use_dask=False, chunk_size=100)
        engine = ParallelGridEngine(config)

        small_gdf = gpd.GeoDataFrame(
            {"name": ["test"]}, geometry=[Point(-74.0, 40.7)], crs="EPSG:4326"
        )

        result = engine.intersect_parallel(sample_grid, small_gdf, chunk_size=100)

        assert isinstance(result, gpd.GeoDataFrame)
        assert len(result) >= 1

    @patch("m3s.parallel.DASK_AVAILABLE", True)
    @patch("m3s.parallel.dask")
    @patch("m3s.parallel.delayed")
    def test_intersect_parallel_dask_fallback(
        self, mock_delayed, mock_dask, sample_grid, sample_gdf_large
    ):
        """Test Dask processing with mocked dependencies."""
        # Mock dask.compute to return expected results
        mock_result = sample_grid.intersects(sample_gdf_large.iloc[:25])
        mock_dask.compute.return_value = [mock_result]
        mock_delayed.return_value = Mock()

        config = ParallelConfig(use_dask=True, use_gpu=False)

        # Mock client setup to avoid actual Dask cluster
        with patch.object(ParallelGridEngine, "_setup_client"):
            engine = ParallelGridEngine(config)
            engine._client = Mock()  # Mock client

            result = engine._intersect_dask(sample_grid, sample_gdf_large.iloc[:25], 25)

            assert isinstance(result, gpd.GeoDataFrame)

    def test_batch_intersect_multiple_grids(self, sample_gdf_large):
        """Test batch intersection with multiple grids."""
        grids = [
            GeohashGrid(precision=4),
            GeohashGrid(precision=5),
            H3Grid(resolution=6),
        ]
        grid_names = ["geohash_4", "geohash_5", "h3_6"]

        config = ParallelConfig(use_dask=False, use_gpu=False)
        engine = ParallelGridEngine(config)

        # Use smaller dataset for testing
        small_gdf = sample_gdf_large.iloc[:10]
        results = engine.batch_intersect_multiple_grids(grids, small_gdf, grid_names)

        assert isinstance(results, dict)
        assert len(results) == 3

        for name in grid_names:
            assert name in results
            assert isinstance(results[name], gpd.GeoDataFrame)
            assert len(results[name]) >= len(small_gdf)

    def test_batch_intersect_auto_names(self, sample_gdf_large):
        """Test batch intersection with auto-generated names."""
        grids = [GeohashGrid(precision=4), GeohashGrid(precision=5)]

        config = ParallelConfig(use_dask=False, use_gpu=False)
        engine = ParallelGridEngine(config)

        small_gdf = sample_gdf_large.iloc[:5]
        results = engine.batch_intersect_multiple_grids(grids, small_gdf)

        assert "grid_0" in results
        assert "grid_1" in results

    def test_get_performance_stats_no_client(self):
        """Test performance stats when no Dask client."""
        config = ParallelConfig(use_dask=False)
        engine = ParallelGridEngine(config)

        stats = engine.get_performance_stats()

        assert "status" in stats
        assert stats["status"] == "dask_disabled"
        assert "config" in stats


class TestStreamProcessing:
    """Test streaming data processing."""

    @pytest.fixture
    def sample_stream_data(self):
        """Create sample streaming data."""
        chunks = []
        for i in range(3):
            geometries = [Point(-74.0 + i * 0.1, 40.7 + j * 0.1) for j in range(5)]
            data = {"chunk": [i] * 5, "id": range(i * 5, (i + 1) * 5)}
            chunk = gpd.GeoDataFrame(data, geometry=geometries, crs="EPSG:4326")
            chunks.append(chunk)
        return chunks

    def test_stream_process_threaded(self, sample_stream_data):
        """Test threaded stream processing."""
        grid = GeohashGrid(precision=5)
        processor = GridStreamProcessor(grid)

        config = ParallelConfig(use_dask=False, use_gpu=False)
        engine = ParallelGridEngine(config)

        result = engine.stream_process(iter(sample_stream_data), processor)

        assert isinstance(result, gpd.GeoDataFrame)
        assert len(result) >= len(sample_stream_data) * 5  # 5 points per chunk
        assert "cell_id" in result.columns

    def test_stream_process_with_callback(self, sample_stream_data):
        """Test stream processing with output callback."""
        grid = GeohashGrid(precision=5)
        processor = GridStreamProcessor(grid)

        config = ParallelConfig(use_dask=False, use_gpu=False)
        engine = ParallelGridEngine(config)

        callback_results = []

        def callback(chunk_result):
            callback_results.append(len(chunk_result))

        engine.stream_process(iter(sample_stream_data), processor, callback)

        assert len(callback_results) == 3  # 3 chunks processed
        assert all(count > 0 for count in callback_results)


class TestConvenienceFunctions:
    """Test convenience functions."""

    @pytest.fixture
    def sample_gdf(self):
        """Create sample GeoDataFrame."""
        geometries = [Point(-74.0, 40.7), Point(-118.2, 34.0)]
        data = {"name": ["NYC", "LA"]}
        return gpd.GeoDataFrame(data, geometry=geometries, crs="EPSG:4326")

    def test_parallel_intersect_function(self, sample_gdf):
        """Test parallel_intersect convenience function."""
        grid = GeohashGrid(precision=5)
        config = ParallelConfig(use_dask=False, use_gpu=False)

        result = parallel_intersect(grid, sample_gdf, config, chunk_size=1)

        assert isinstance(result, gpd.GeoDataFrame)
        assert len(result) >= 2
        assert "cell_id" in result.columns

    def test_stream_grid_processing_function(self, sample_gdf):
        """Test stream_grid_processing convenience function."""
        grid = GeohashGrid(precision=5)
        config = ParallelConfig(use_dask=False, use_gpu=False)

        # Create stream from data
        stream = create_data_stream(sample_gdf, chunk_size=1)

        result = stream_grid_processing(grid, stream, config)

        assert isinstance(result, gpd.GeoDataFrame)
        assert len(result) >= 2


class TestStreamCreators:
    """Test stream creation utilities."""

    @pytest.fixture
    def sample_gdf(self):
        """Create sample GeoDataFrame."""
        geometries = [Point(-74.0 + i * 0.1, 40.7 + i * 0.1) for i in range(10)]
        data = {"id": range(10), "value": range(10, 20)}
        return gpd.GeoDataFrame(data, geometry=geometries, crs="EPSG:4326")

    def test_create_data_stream(self, sample_gdf):
        """Test creating data stream from GeoDataFrame."""
        stream = create_data_stream(sample_gdf, chunk_size=3)
        chunks = list(stream)

        assert len(chunks) == 4  # 10 items / 3 per chunk = 4 chunks
        assert len(chunks[0]) == 3
        assert len(chunks[1]) == 3
        assert len(chunks[2]) == 3
        assert len(chunks[3]) == 1  # Last chunk

        # Verify all data is preserved
        total_rows = sum(len(chunk) for chunk in chunks)
        assert total_rows == len(sample_gdf)

    def test_create_data_stream_exact_division(self, sample_gdf):
        """Test stream creation with exact division."""
        stream = create_data_stream(sample_gdf, chunk_size=5)
        chunks = list(stream)

        assert len(chunks) == 2
        assert all(len(chunk) == 5 for chunk in chunks)

    @patch("geopandas.read_file")
    def test_create_file_stream(self, mock_read_file):
        """Test creating stream from files."""
        # Mock file reading
        sample_gdf = gpd.GeoDataFrame(
            {"id": [1, 2]},
            geometry=[Point(-74.0, 40.7), Point(-118.2, 34.0)],
            crs="EPSG:4326",
        )
        mock_read_file.return_value = sample_gdf

        file_paths = ["file1.shp", "file2.shp"]
        stream = create_file_stream(file_paths)
        chunks = list(stream)

        assert len(chunks) == 2  # One chunk per file
        assert all(len(chunk) == 2 for chunk in chunks)
        assert mock_read_file.call_count == 2

    @patch("geopandas.read_file")
    def test_create_file_stream_with_chunking(self, mock_read_file):
        """Test file stream with chunking large files."""
        # Create larger mock data
        large_gdf = gpd.GeoDataFrame(
            {"id": range(10)},
            geometry=[Point(-74.0 + i * 0.1, 40.7) for i in range(10)],
            crs="EPSG:4326",
        )
        mock_read_file.return_value = large_gdf

        file_paths = ["large_file.shp"]
        stream = create_file_stream(file_paths, chunk_size=3)
        chunks = list(stream)

        # Should create multiple chunks from the large file
        assert len(chunks) == 4  # 10 items / 3 per chunk = 4 chunks

    @patch("geopandas.read_file")
    def test_create_file_stream_error_handling(self, mock_read_file):
        """Test file stream error handling."""
        # Mock file reading error
        mock_read_file.side_effect = Exception("File not found")

        file_paths = ["bad_file.shp"]

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            stream = create_file_stream(file_paths)
            chunks = list(stream)

            assert len(chunks) == 0  # No chunks due to error
            assert len(w) == 1  # Warning issued
            assert "Failed to read" in str(w[0].message)


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_stream_processing(self):
        """Test processing empty stream."""
        grid = GeohashGrid(precision=5)
        processor = GridStreamProcessor(grid)

        config = ParallelConfig(use_dask=False)
        engine = ParallelGridEngine(config)

        empty_stream = iter([])
        result = engine.stream_process(empty_stream, processor)

        assert isinstance(result, gpd.GeoDataFrame)
        assert len(result) == 0

    def test_stream_with_empty_chunks(self):
        """Test stream processing with some empty chunks."""
        grid = GeohashGrid(precision=5)
        processor = GridStreamProcessor(grid)

        config = ParallelConfig(use_dask=False)
        engine = ParallelGridEngine(config)

        # Create stream with empty and non-empty chunks
        chunks = [
            gpd.GeoDataFrame(geometry=[], crs="EPSG:4326"),  # Empty
            gpd.GeoDataFrame(
                {"id": [1]}, geometry=[Point(-74.0, 40.7)], crs="EPSG:4326"
            ),  # Non-empty
            gpd.GeoDataFrame(geometry=[], crs="EPSG:4326"),  # Empty
        ]

        result = engine.stream_process(iter(chunks), processor)

        assert isinstance(result, gpd.GeoDataFrame)
        assert len(result) >= 1  # Should have results from non-empty chunk

    def test_gpu_fallback_on_error(self):
        """Test GPU processing fallback on error."""
        mock_cudf = Mock()
        mock_cudf.from_pandas.side_effect = Exception("GPU error")

        with patch("m3s.parallel.GPU_AVAILABLE", True), patch(
            "m3s.parallel.cudf", mock_cudf
        ):
            config = ParallelConfig(use_dask=False, use_gpu=True)
            engine = ParallelGridEngine(config)

            grid = GeohashGrid(precision=5)
            gdf = gpd.GeoDataFrame(
                {"id": [1]}, geometry=[Point(-74.0, 40.7)], crs="EPSG:4326"
            )

            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                result = engine._intersect_gpu(grid, gdf, 1000)

                assert isinstance(result, gpd.GeoDataFrame)
                assert len(w) > 0  # Warning about GPU fallback
                assert any(
                    "GPU processing failed" in str(warning.message) for warning in w
                )


if __name__ == "__main__":
    pytest.main([__file__])
