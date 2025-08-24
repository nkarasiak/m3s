"""
Parallel processing engine for M3S spatial grid operations.

Provides distributed computing capabilities using Dask, GPU acceleration,
and streaming data processing for large-scale spatial operations.
"""

import warnings
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, Iterator, List, Optional

import geopandas as gpd
import pandas as pd

from .memory import MemoryMonitor, optimize_geodataframe_memory

try:
    import dask
    from dask import delayed
    from dask.distributed import Client
    from dask.distributed import as_completed as dask_as_completed

    DASK_AVAILABLE = True
except ImportError:
    DASK_AVAILABLE = False
    dask = None
    delayed = None
    Client = None
    dask_as_completed = None
    warnings.warn(
        "Dask not available. Parallel operations will use threading fallback.",
        stacklevel=2,
    )

try:
    import cudf
    import cupy as cp
    import cuspatial

    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False
    cudf = None
    cp = None
    cuspatial = None
    warnings.warn("RAPIDS/CuPy not available. GPU acceleration disabled.", stacklevel=2)

from .base import BaseGrid


class ParallelConfig:
    """Configuration for parallel processing operations."""

    def __init__(
        self,
        use_dask: bool = True,
        use_gpu: bool = True,
        n_workers: Optional[int] = None,
        chunk_size: int = 10000,
        memory_limit: str = "2GB",
        threads_per_worker: int = 2,
        scheduler_address: Optional[str] = None,
        optimize_memory: bool = True,
        adaptive_chunking: bool = True,
    ):
        self.use_dask = use_dask and DASK_AVAILABLE
        self.use_gpu = use_gpu and GPU_AVAILABLE
        self.n_workers = n_workers
        self.chunk_size = chunk_size
        self.memory_limit = memory_limit
        self.threads_per_worker = threads_per_worker
        self.scheduler_address = scheduler_address
        self.optimize_memory = optimize_memory
        self.adaptive_chunking = adaptive_chunking

        if use_dask and not DASK_AVAILABLE:
            warnings.warn(
                "Dask requested but not available. Using threading fallback.",
                stacklevel=2,
            )
        if use_gpu and not GPU_AVAILABLE:
            warnings.warn(
                "GPU requested but RAPIDS/CuPy not available. Using CPU fallback.",
                stacklevel=2,
            )


class StreamProcessor(ABC):
    """Abstract base class for streaming data processors."""

    @abstractmethod
    def process_chunk(self, chunk: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Process a single chunk of data."""
        pass

    @abstractmethod
    def combine_results(self, results: List[gpd.GeoDataFrame]) -> gpd.GeoDataFrame:
        """Combine multiple processed chunks into final result."""
        pass


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

    Supports Dask distributed computing, GPU acceleration via RAPIDS,
    and streaming data processing for large datasets.
    """

    def __init__(self, config: Optional[ParallelConfig] = None):
        self.config = config or ParallelConfig()
        self._client: Optional[Any] = None
        self.memory_monitor = MemoryMonitor() if self.config.optimize_memory else None
        self._setup_client()

    def _setup_client(self):
        """Initialize Dask client if available and configured."""
        if not self.config.use_dask:
            return

        try:
            if self.config.scheduler_address:
                self._client = Client(self.config.scheduler_address)
            else:
                self._client = Client(
                    n_workers=self.config.n_workers,
                    threads_per_worker=self.config.threads_per_worker,
                    memory_limit=self.config.memory_limit,
                    silence_logs=False,
                )
        except Exception as e:
            warnings.warn(
                f"Failed to setup Dask client: {e}. Using threading fallback.",
                stacklevel=2,
            )
            self.config.use_dask = False

    def __del__(self):
        """Cleanup Dask client on deletion."""
        if self._client:
            self._client.close()

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

        # Optimize input GeoDataFrame memory usage if enabled
        if self.config.optimize_memory:
            gdf = optimize_geodataframe_memory(gdf)

            # Adjust chunk size based on memory pressure
            if self.memory_monitor and self.config.adaptive_chunking:
                chunk_size = self.memory_monitor.suggest_chunk_size(chunk_size)

        if self.config.use_dask and self._client:
            return self._intersect_dask(grid, gdf, chunk_size)
        elif self.config.use_gpu:
            return self._intersect_gpu(grid, gdf, chunk_size)
        else:
            return self._intersect_threaded(grid, gdf, chunk_size)

    def _intersect_dask(
        self, grid: BaseGrid, gdf: gpd.GeoDataFrame, chunk_size: int
    ) -> gpd.GeoDataFrame:
        """Dask-based parallel intersection."""
        if not DASK_AVAILABLE:
            return self._intersect_threaded(grid, gdf, chunk_size)

        # Split GeoDataFrame into chunks
        chunks = [gdf.iloc[i : i + chunk_size] for i in range(0, len(gdf), chunk_size)]

        # Create delayed operations
        delayed_ops = [delayed(grid.intersects)(chunk) for chunk in chunks]

        # Compute in parallel
        results = dask.compute(*delayed_ops)

        # Combine results
        if not results:
            return gpd.GeoDataFrame()

        combined = pd.concat(results, ignore_index=True)
        return gpd.GeoDataFrame(combined, crs=gdf.crs)

    def _intersect_gpu(
        self, grid: BaseGrid, gdf: gpd.GeoDataFrame, chunk_size: int
    ) -> gpd.GeoDataFrame:
        """GPU-accelerated intersection using RAPIDS."""
        if not GPU_AVAILABLE:
            return self._intersect_threaded(grid, gdf, chunk_size)

        try:
            # Convert to cuDF for GPU processing
            cugdf = cudf.from_pandas(gdf)

            # Process in chunks to manage GPU memory
            results = []
            for i in range(0, len(cugdf), chunk_size):
                chunk = cugdf.iloc[i : i + chunk_size]
                # Convert back to pandas for grid operations (most grid ops are CPU-based)
                chunk_pd = chunk.to_pandas()
                chunk_gdf = gpd.GeoDataFrame(chunk_pd, crs=gdf.crs)
                result = grid.intersects(chunk_gdf)
                results.append(result)

            if not results:
                return gpd.GeoDataFrame()

            combined = pd.concat(results, ignore_index=True)
            return gpd.GeoDataFrame(combined, crs=gdf.crs)

        except Exception as e:
            warnings.warn(
                f"GPU processing failed: {e}. Falling back to CPU.", stacklevel=2
            )
            return self._intersect_threaded(grid, gdf, chunk_size)

    def _intersect_threaded(
        self, grid: BaseGrid, gdf: gpd.GeoDataFrame, chunk_size: int
    ) -> gpd.GeoDataFrame:
        """Thread-based parallel intersection."""
        if len(gdf) <= chunk_size:
            return grid.intersects(gdf)

        chunks = [gdf.iloc[i : i + chunk_size] for i in range(0, len(gdf), chunk_size)]
        results = []

        # Use ThreadPoolExecutor for CPU-bound operations
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
        if self.config.use_dask and self._client:
            return self._stream_process_dask(data_stream, processor, output_callback)
        else:
            return self._stream_process_threaded(
                data_stream, processor, output_callback
            )

    def _stream_process_dask(
        self,
        data_stream: Iterator[gpd.GeoDataFrame],
        processor: StreamProcessor,
        output_callback: Optional[Callable[[gpd.GeoDataFrame], None]],
    ) -> gpd.GeoDataFrame:
        """Dask-based stream processing."""
        futures = []

        for chunk in data_stream:
            if len(chunk) > 0:
                future = self._client.submit(processor.process_chunk, chunk)
                futures.append(future)

        results = []
        for future in dask_as_completed(futures):
            try:
                result = future.result()
                results.append(result)
                if output_callback:
                    output_callback(result)
            except Exception as e:
                warnings.warn(f"Stream chunk processing failed: {e}", stacklevel=2)

        return processor.combine_results(results)

    def _stream_process_threaded(
        self,
        data_stream: Iterator[gpd.GeoDataFrame],
        processor: StreamProcessor,
        output_callback: Optional[Callable[[gpd.GeoDataFrame], None]],
    ) -> gpd.GeoDataFrame:
        """Thread-based stream processing."""
        results = []
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

        if self.config.use_dask and self._client:
            # Use Dask for parallel processing
            futures = {}
            for name, grid in zip(grid_names, grids):
                future = self._client.submit(self.intersect_parallel, grid, gdf)
                futures[name] = future

            results = {}
            for name, future in futures.items():
                try:
                    results[name] = future.result()
                except Exception as e:
                    warnings.warn(f"Grid {name} processing failed: {e}", stacklevel=2)
                    results[name] = gpd.GeoDataFrame()

            return results
        else:
            # Use threading for parallel processing
            results = {}
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
                        warnings.warn(
                            f"Grid {name} processing failed: {e}", stacklevel=2
                        )
                        results[name] = gpd.GeoDataFrame()

            return results

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics from Dask client if available."""
        if self._client:
            try:
                return {
                    "scheduler_info": self._client.scheduler_info(),
                    "worker_info": self._client.nthreads(),
                    "memory_usage": self._client.memory_usage(),
                }
            except:
                return {"status": "client_unavailable"}
        else:
            return {
                "status": "dask_disabled",
                "config": {
                    "use_dask": self.config.use_dask,
                    "use_gpu": self.config.use_gpu,
                    "chunk_size": self.config.chunk_size,
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
                # Split large files into chunks
                for chunk in create_data_stream(gdf, chunk_size):
                    yield chunk
            else:
                yield gdf
        except Exception as e:
            warnings.warn(f"Failed to read {file_path}: {e}", stacklevel=2)


# Convenience functions for common operations
def parallel_intersect(
    grid: BaseGrid,
    gdf: gpd.GeoDataFrame,
    config: Optional[ParallelConfig] = None,
    chunk_size: Optional[int] = None,
) -> gpd.GeoDataFrame:
    """
    Convenience function for parallel grid intersection.

    Parameters
    ----------
    grid : BaseGrid
        Grid system to use
    gdf : gpd.GeoDataFrame
        Input GeoDataFrame
    config : ParallelConfig, optional
        Configuration for parallel processing
    chunk_size : int, optional
        Chunk size for processing

    Returns
    -------
    gpd.GeoDataFrame
        Grid intersection results
    """
    engine = ParallelGridEngine(config)
    return engine.intersect_parallel(grid, gdf, chunk_size)


def stream_grid_processing(
    grid: BaseGrid,
    data_stream: Iterator[gpd.GeoDataFrame],
    config: Optional[ParallelConfig] = None,
    output_callback: Optional[Callable[[gpd.GeoDataFrame], None]] = None,
) -> gpd.GeoDataFrame:
    """
    Convenience function for streaming grid processing.

    Parameters
    ----------
    grid : BaseGrid
        Grid system to use
    data_stream : Iterator[gpd.GeoDataFrame]
        Stream of data chunks
    config : ParallelConfig, optional
        Configuration for parallel processing
    output_callback : callable, optional
        Callback for each processed chunk

    Returns
    -------
    gpd.GeoDataFrame
        Combined processing results
    """
    engine = ParallelGridEngine(config)
    processor = GridStreamProcessor(grid)
    return engine.stream_process(data_stream, processor, output_callback)
