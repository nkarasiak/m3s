"""
Parallel processing engine for M3S spatial grid operations.

Threading-only implementation for parallel and streaming workloads.
"""

import warnings
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, Iterator, List, Optional

import geopandas as gpd
import pandas as pd

from .base import BaseGrid
from .memory import MemoryMonitor, optimize_geodataframe_memory


class ParallelConfig:
    """Configuration for parallel processing operations."""

    def __init__(
        self,
        n_workers: Optional[int] = None,
        chunk_size: int = 10000,
        optimize_memory: bool = True,
        adaptive_chunking: bool = True,
    ):
        self.n_workers = n_workers
        self.chunk_size = chunk_size
        self.optimize_memory = optimize_memory
        self.adaptive_chunking = adaptive_chunking


class StreamProcessor(ABC):
    """Abstract base class for streaming data processors."""

    @abstractmethod
    def process_chunk(self, chunk: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Process a single chunk of data."""
        raise NotImplementedError

    @abstractmethod
    def combine_results(self, results: List[gpd.GeoDataFrame]) -> gpd.GeoDataFrame:
        """Combine multiple processed chunks into final result."""
        raise NotImplementedError


class GridStreamProcessor(StreamProcessor):
    """Stream processor for grid intersection operations."""

    def __init__(self, grid: BaseGrid):
        self.grid = grid

    def process_chunk(self, chunk: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Process a chunk through grid intersection."""
        return self.grid.intersects(chunk)

    def combine_results(self, results: List[gpd.GeoDataFrame]) -> gpd.GeoDataFrame:
        """Combine intersection results."""
        if not results:
            return gpd.GeoDataFrame()

        combined = pd.concat(results, ignore_index=True)
        return gpd.GeoDataFrame(combined, crs=results[0].crs)


class ParallelGridEngine:
    """
    Parallel processing engine for spatial grid operations.

    Threading-only implementation for moderate-size workloads.
    """

    def __init__(self, config: Optional[ParallelConfig] = None):
        self.config = config or ParallelConfig()
        self.memory_monitor = MemoryMonitor() if self.config.optimize_memory else None

    def intersect_parallel(
        self, grid: BaseGrid, gdf: gpd.GeoDataFrame, chunk_size: Optional[int] = None
    ) -> gpd.GeoDataFrame:
        """
        Perform parallel grid intersection on GeoDataFrame.

        Parameters
        ----------
        grid : BaseGrid
            Grid system to use for intersection
        gdf : gpd.GeoDataFrame
            Input GeoDataFrame
        chunk_size : int, optional
            Size of chunks for parallel processing

        Returns
        -------
        gpd.GeoDataFrame
            Results of grid intersection
        """
        if len(gdf) == 0:
            return gpd.GeoDataFrame()

        chunk_size = chunk_size or self.config.chunk_size

        if self.config.optimize_memory:
            gdf = optimize_geodataframe_memory(gdf)
            if self.memory_monitor and self.config.adaptive_chunking:
                chunk_size = self.memory_monitor.suggest_chunk_size(chunk_size)

        return self._intersect_threaded(grid, gdf, chunk_size)

    def _intersect_threaded(
        self, grid: BaseGrid, gdf: gpd.GeoDataFrame, chunk_size: int
    ) -> gpd.GeoDataFrame:
        """Thread-based parallel intersection."""
        if len(gdf) <= chunk_size:
            return grid.intersects(gdf)

        chunks = [gdf.iloc[i : i + chunk_size] for i in range(0, len(gdf), chunk_size)]
        results: List[gpd.GeoDataFrame] = []

        max_workers = self.config.n_workers or min(4, len(chunks))

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_chunk = {
                executor.submit(grid.intersects, chunk): chunk for chunk in chunks
            }

            for future in as_completed(future_to_chunk):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    warnings.warn(f"Chunk processing failed: {e}", stacklevel=2)

        if not results:
            return gpd.GeoDataFrame()

        combined = pd.concat(results, ignore_index=True)
        return gpd.GeoDataFrame(combined, crs=gdf.crs)

    def stream_process(
        self,
        data_stream: Iterator[gpd.GeoDataFrame],
        processor: StreamProcessor,
        output_callback: Optional[Callable[[gpd.GeoDataFrame], None]] = None,
    ) -> gpd.GeoDataFrame:
        """
        Process streaming geospatial data.

        Parameters
        ----------
        data_stream : Iterator[gpd.GeoDataFrame]
            Stream of GeoDataFrame chunks
        processor : StreamProcessor
            Processor to apply to each chunk
        output_callback : callable, optional
            Callback function called with each processed chunk

        Returns
        -------
        gpd.GeoDataFrame
            Combined results from all chunks
        """
        return self._stream_process_threaded(data_stream, processor, output_callback)

    def _stream_process_threaded(
        self,
        data_stream: Iterator[gpd.GeoDataFrame],
        processor: StreamProcessor,
        output_callback: Optional[Callable[[gpd.GeoDataFrame], None]],
    ) -> gpd.GeoDataFrame:
        """Thread-based stream processing."""
        results: List[gpd.GeoDataFrame] = []
        max_workers = self.config.n_workers or 4

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []

            for chunk in data_stream:
                if len(chunk) > 0:
                    future = executor.submit(processor.process_chunk, chunk)
                    futures.append(future)

            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                    if output_callback:
                        output_callback(result)
                except Exception as e:
                    warnings.warn(f"Stream chunk processing failed: {e}", stacklevel=2)

        return processor.combine_results(results)

    def batch_intersect_multiple_grids(
        self,
        grids: List[BaseGrid],
        gdf: gpd.GeoDataFrame,
        grid_names: Optional[List[str]] = None,
    ) -> Dict[str, gpd.GeoDataFrame]:
        """
        Intersect GeoDataFrame with multiple grid systems in parallel.

        Parameters
        ----------
        grids : List[BaseGrid]
            List of grid systems
        gdf : gpd.GeoDataFrame
            Input GeoDataFrame
        grid_names : List[str], optional
            Names for each grid system

        Returns
        -------
        Dict[str, gpd.GeoDataFrame]
            Results keyed by grid name
        """
        if not grid_names:
            grid_names = [f"grid_{i}" for i in range(len(grids))]

        results: Dict[str, gpd.GeoDataFrame] = {}
        max_workers = min(len(grids), self.config.n_workers or 4)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_name = {
                executor.submit(self.intersect_parallel, grid, gdf): name
                for name, grid in zip(grid_names, grids)
            }

            for future in as_completed(future_to_name):
                name = future_to_name[future]
                try:
                    results[name] = future.result()
                except Exception as e:
                    warnings.warn(f"Grid {name} processing failed: {e}", stacklevel=2)
                    results[name] = gpd.GeoDataFrame()

        return results

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get basic performance statistics."""
        return {
            "status": "threading_only",
            "config": {
                "chunk_size": self.config.chunk_size,
                "n_workers": self.config.n_workers,
                "optimize_memory": self.config.optimize_memory,
            },
        }


def create_data_stream(
    gdf: gpd.GeoDataFrame, chunk_size: int = 10000
) -> Iterator[gpd.GeoDataFrame]:
    """
    Create a streaming iterator from a GeoDataFrame.

    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        Input GeoDataFrame
    chunk_size : int
        Size of each chunk

    Yields
    ------
    gpd.GeoDataFrame
        Chunks of the input GeoDataFrame
    """
    for i in range(0, len(gdf), chunk_size):
        yield gdf.iloc[i : i + chunk_size].copy()


def create_file_stream(
    file_paths: List[str], chunk_size: Optional[int] = None
) -> Iterator[gpd.GeoDataFrame]:
    """
    Create a streaming iterator from multiple geospatial files.

    Parameters
    ----------
    file_paths : List[str]
        List of file paths to read
    chunk_size : int, optional
        If provided, split large files into chunks

    Yields
    ------
    gpd.GeoDataFrame
        GeoDataFrames loaded from files
    """
    for file_path in file_paths:
        try:
            gdf = gpd.read_file(file_path)
            if chunk_size and len(gdf) > chunk_size:
                for chunk in create_data_stream(gdf, chunk_size):
                    yield chunk
            else:
                yield gdf
        except Exception as e:
            warnings.warn(f"Failed to read {file_path}: {e}", stacklevel=2)


def parallel_intersect(
    grid: BaseGrid,
    gdf: gpd.GeoDataFrame,
    config: Optional[ParallelConfig] = None,
    chunk_size: Optional[int] = None,
) -> gpd.GeoDataFrame:
    """Convenience wrapper for parallel intersection."""
    engine = ParallelGridEngine(config)
    return engine.intersect_parallel(grid, gdf, chunk_size)


def stream_grid_processing(
    grid: BaseGrid,
    data_stream: Iterator[gpd.GeoDataFrame],
    config: Optional[ParallelConfig] = None,
    output_callback: Optional[Callable[[gpd.GeoDataFrame], None]] = None,
) -> gpd.GeoDataFrame:
    """Convenience wrapper for stream processing."""
    engine = ParallelGridEngine(config)
    processor = GridStreamProcessor(grid)
    return engine.stream_process(data_stream, processor, output_callback)
