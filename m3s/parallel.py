from __future__ import annotations

"""
Parallel processing engine for M3S spatial grid operations.
"""

from abc import ABC, abstractmethod
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from typing import Iterator, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    import geopandas as gpd
    import pandas as pd

from .core.grid import GridProtocol
from .memory import MemoryMonitor, optimize_geodataframe_memory

class ParallelConfig:
    """Configuration for parallel processing operations."""

    def __init__(
        self,
        use_processes: bool = False,
        n_workers: Optional[int] = None,
        chunk_size: int = 10000,
        optimize_memory: bool = True,
        adaptive_chunking: bool = True,
    ):
        self.use_processes = use_processes
        self.n_workers = n_workers
        self.chunk_size = chunk_size
        self.optimize_memory = optimize_memory
        self.adaptive_chunking = adaptive_chunking


class StreamProcessor(ABC):
    """Abstract base class for streaming data processors."""

    @abstractmethod
    def process_chunk(self, chunk: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Process a single chunk of data."""

    @abstractmethod
    def combine_results(self, results: list[gpd.GeoDataFrame]) -> gpd.GeoDataFrame:
        """Combine multiple processed chunks into final result."""


class GridStreamProcessor(StreamProcessor):
    """Stream processor for grid intersection operations."""

    def __init__(self, grid: GridProtocol):
        self.grid = grid

    def process_chunk(self, chunk: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        return self.grid.intersects(chunk)

    def combine_results(self, results: list[gpd.GeoDataFrame]) -> gpd.GeoDataFrame:
        import geopandas as gpd
        import pandas as pd

        if not results:
            return gpd.GeoDataFrame()

        combined = pd.concat(results, ignore_index=True)
        return gpd.GeoDataFrame(combined, crs=results[0].crs)


class ParallelGridEngine:
    """Parallel processing engine for spatial grid operations."""

    def __init__(self, config: Optional[ParallelConfig] = None):
        self.config = config or ParallelConfig()
        self.memory_monitor = MemoryMonitor() if self.config.optimize_memory else None

    def intersect_parallel(
        self, grid: GridProtocol, gdf: gpd.GeoDataFrame, chunk_size: Optional[int] = None
    ) -> gpd.GeoDataFrame:
        import geopandas as gpd

        if len(gdf) == 0:
            return gpd.GeoDataFrame()

        chunk_size = chunk_size or self.config.chunk_size
        if self.config.adaptive_chunking and self.memory_monitor:
            chunk_size = self.memory_monitor.suggest_chunk_size(chunk_size)

        if self.config.optimize_memory:
            gdf = optimize_geodataframe_memory(gdf)

        chunks = [gdf.iloc[i : i + chunk_size] for i in range(0, len(gdf), chunk_size)]

        if self.config.use_processes:
            return self._intersect_executor(grid, chunks, use_processes=True)

        return self._intersect_executor(grid, chunks, use_processes=False)

    def _intersect_executor(
        self,
        grid: GridProtocol,
        chunks: list[gpd.GeoDataFrame],
        use_processes: bool,
    ) -> gpd.GeoDataFrame:
        import geopandas as gpd
        import pandas as pd

        executor_cls = ProcessPoolExecutor if use_processes else ThreadPoolExecutor
        results = []
        with executor_cls(max_workers=self.config.n_workers) as executor:
            futures = [executor.submit(grid.intersects, chunk) for chunk in chunks]
            for future in as_completed(futures):
                results.append(future.result())

        if not results:
            return gpd.GeoDataFrame()
        combined = pd.concat(results, ignore_index=True)
        return gpd.GeoDataFrame(combined, crs=results[0].crs)

    def stream_grid_processing(
        self,
        processor: StreamProcessor,
        data_stream: Iterator[gpd.GeoDataFrame],
    ) -> gpd.GeoDataFrame:
        results = []
        for chunk in data_stream:
            results.append(processor.process_chunk(chunk))
        return processor.combine_results(results)


def parallel_intersect(
    grid: GridProtocol,
    gdf: gpd.GeoDataFrame,
    config: Optional[ParallelConfig] = None,
) -> gpd.GeoDataFrame:
    engine = ParallelGridEngine(config)
    return engine.intersect_parallel(grid, gdf)


def stream_grid_processing(
    processor: StreamProcessor, data_stream: Iterator[gpd.GeoDataFrame]
) -> gpd.GeoDataFrame:
    engine = ParallelGridEngine(ParallelConfig())
    return engine.stream_grid_processing(processor, data_stream)


def create_data_stream(
    gdf: gpd.GeoDataFrame, chunk_size: int
) -> Iterator[gpd.GeoDataFrame]:
    for i in range(0, len(gdf), chunk_size):
        yield gdf.iloc[i : i + chunk_size]


def create_file_stream(
    file_path: str, chunk_size: int
) -> Iterator[gpd.GeoDataFrame]:
    import geopandas as gpd

    for chunk in gpd.read_file(file_path, chunksize=chunk_size):
        yield chunk
