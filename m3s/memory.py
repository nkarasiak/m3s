"""
Memory optimization utilities for M3S spatial operations.

Provides memory-efficient processing capabilities for large datasets,
including lazy evaluation, chunked processing, and memory monitoring.
"""

import gc
import warnings
from contextlib import contextmanager
from typing import Callable, Iterator, Optional

import geopandas as gpd
import pandas as pd

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    warnings.warn(
        "psutil not available. Memory monitoring will be limited.", stacklevel=2
    )


class MemoryMonitor:
    """
    Monitor and manage memory usage during spatial operations.
    """

    def __init__(self, warn_threshold: float = 0.8, critical_threshold: float = 0.9):
        """
        Initialize memory monitor.

        Parameters
        ----------
        warn_threshold : float, optional
            Memory usage threshold (0-1) to trigger warning, by default 0.8
        critical_threshold : float, optional
            Memory usage threshold (0-1) to trigger critical action, by default 0.9
        """
        self.warn_threshold = warn_threshold
        self.critical_threshold = critical_threshold
        self.process = psutil.Process() if PSUTIL_AVAILABLE else None

    def get_memory_usage(self) -> dict:
        """
        Get current memory usage statistics.

        Returns
        -------
        dict
            Memory usage information including RSS, VMS, and percentage
        """
        if not PSUTIL_AVAILABLE or not self.process:
            # Return dummy values if psutil is not available
            return {
                "rss_mb": 0.0,
                "vms_mb": 0.0,
                "percent": 50.0,  # Assume moderate usage
                "available_mb": 1000.0,
                "total_mb": 2000.0,
            }

        memory_info = self.process.memory_info()
        memory_percent = self.process.memory_percent()

        return {
            "rss_mb": memory_info.rss / 1024 / 1024,  # Resident Set Size in MB
            "vms_mb": memory_info.vms / 1024 / 1024,  # Virtual Memory Size in MB
            "percent": memory_percent,
            "available_mb": psutil.virtual_memory().available / 1024 / 1024,
            "total_mb": psutil.virtual_memory().total / 1024 / 1024,
        }

    def check_memory_pressure(self) -> str:
        """
        Check current memory pressure level.

        Returns
        -------
        str
            Memory pressure level: 'low', 'medium', 'high', or 'critical'
        """
        usage = self.get_memory_usage()
        percent = usage["percent"] / 100

        if percent >= self.critical_threshold:
            return "critical"
        elif percent >= self.warn_threshold:
            return "high"
        elif percent >= 0.5:
            return "medium"
        else:
            return "low"

    def suggest_chunk_size(self, base_chunk_size: int = 10000) -> int:
        """
        Suggest optimal chunk size based on current memory usage.

        Parameters
        ----------
        base_chunk_size : int, optional
            Base chunk size to adjust, by default 10000

        Returns
        -------
        int
            Recommended chunk size
        """
        pressure = self.check_memory_pressure()

        if pressure == "critical":
            return max(100, base_chunk_size // 8)
        elif pressure == "high":
            return max(500, base_chunk_size // 4)
        elif pressure == "medium":
            return max(1000, base_chunk_size // 2)
        else:
            return base_chunk_size


@contextmanager
def memory_efficient_processing(
    auto_gc: bool = True, gc_threshold: int = 1000, monitor_memory: bool = True
):
    """
    Context manager for memory-efficient processing.

    Parameters
    ----------
    auto_gc : bool, optional
        Whether to automatically run garbage collection, by default True
    gc_threshold : int, optional
        Number of operations before triggering GC, by default 1000
    monitor_memory : bool, optional
        Whether to monitor memory usage, by default True
    """
    monitor = MemoryMonitor() if monitor_memory else None

    if monitor:
        initial_memory = monitor.get_memory_usage()
        print(f"Initial memory usage: {initial_memory['rss_mb']:.1f} MB")

    try:
        yield monitor
    finally:
        if auto_gc:
            gc.collect()

        if monitor:
            final_memory = monitor.get_memory_usage()
            memory_delta = final_memory["rss_mb"] - initial_memory["rss_mb"]
            print(
                f"Final memory usage: {final_memory['rss_mb']:.1f} MB "
                f"(Δ {memory_delta:+.1f} MB)"
            )


class LazyGeodataFrame:
    """
    Lazy-loading wrapper for GeoDataFrame to minimize memory usage.

    Only loads data chunks when needed and releases them after processing.
    """

    def __init__(
        self,
        file_path: str = None,
        gdf: gpd.GeoDataFrame = None,
        chunk_size: int = 10000,
    ):
        """
        Initialize lazy GeoDataFrame.

        Parameters
        ----------
        file_path : str, optional
            Path to geospatial file to load lazily
        gdf : gpd.GeoDataFrame, optional
            Existing GeoDataFrame to wrap
        chunk_size : int, optional
            Size of chunks for processing, by default 10000
        """
        if file_path and gdf is not None:
            raise ValueError("Provide either file_path OR gdf, not both")

        self.file_path = file_path
        self._gdf = gdf
        self.chunk_size = chunk_size
        self._length = None
        self._crs = None
        self._bounds = None

    def __len__(self) -> int:
        """Get total number of features."""
        if self._length is None:
            if self.file_path:
                # Use fiona to get count without loading full dataset
                import fiona

                with fiona.open(self.file_path) as src:
                    self._length = len(src)
            else:
                self._length = len(self._gdf)
        return self._length

    @property
    def crs(self):
        """Get CRS without loading full dataset."""
        if self._crs is None:
            if self.file_path:
                import fiona

                with fiona.open(self.file_path) as src:
                    self._crs = src.crs
            else:
                self._crs = self._gdf.crs
        return self._crs

    @property
    def bounds(self):
        """Get bounds without loading full dataset."""
        if self._bounds is None:
            if self.file_path:
                import fiona

                with fiona.open(self.file_path) as src:
                    self._bounds = src.bounds
            else:
                self._bounds = self._gdf.total_bounds
        return self._bounds

    def chunks(self, chunk_size: Optional[int] = None) -> Iterator[gpd.GeoDataFrame]:
        """
        Iterate over chunks of the GeoDataFrame.

        Parameters
        ----------
        chunk_size : int, optional
            Size of chunks, uses instance default if None

        Yields
        ------
        gpd.GeoDataFrame
            Chunks of the original GeoDataFrame
        """
        chunk_size = chunk_size or self.chunk_size

        if self.file_path:
            # Read file in chunks
            for i in range(0, len(self), chunk_size):
                # Use rows parameter to read specific chunk
                gdf_chunk = gpd.read_file(self.file_path, rows=slice(i, i + chunk_size))
                yield gdf_chunk
                # Explicitly delete chunk to free memory
                del gdf_chunk
                gc.collect()
        else:
            # Chunk existing GeoDataFrame
            for i in range(0, len(self._gdf), chunk_size):
                yield self._gdf.iloc[i : i + chunk_size].copy()

    def sample(self, n: int = 1000) -> gpd.GeoDataFrame:
        """
        Get a random sample without loading full dataset.

        Parameters
        ----------
        n : int, optional
            Number of samples to return, by default 1000

        Returns
        -------
        gpd.GeoDataFrame
            Random sample of features
        """
        total_features = len(self)
        if n >= total_features:
            if self.file_path:
                return gpd.read_file(self.file_path)
            else:
                return self._gdf.copy()

        # Generate random indices
        import random

        sample_indices = sorted(random.sample(range(total_features), n))

        if self.file_path:
            # For file-based data, read only sampled rows
            # This is a simplified approach; real implementation would be more complex
            return gpd.read_file(self.file_path).iloc[sample_indices]
        else:
            return self._gdf.iloc[sample_indices].copy()


class StreamingGridProcessor:
    """
    Memory-efficient streaming processor for grid operations.

    Processes large datasets in chunks while maintaining minimal memory footprint.
    """

    def __init__(self, grid, memory_monitor: Optional[MemoryMonitor] = None):
        """
        Initialize streaming processor.

        Parameters
        ----------
        grid : BaseGrid
            Grid system to use for processing
        memory_monitor : MemoryMonitor, optional
            Memory monitor for optimization
        """
        self.grid = grid
        self.memory_monitor = memory_monitor or MemoryMonitor()
        self.processed_count = 0
        self.results_cache = []

    def process_stream(
        self,
        data_source: LazyGeodataFrame,
        output_callback: Optional[Callable[[gpd.GeoDataFrame], None]] = None,
        adaptive_chunking: bool = True,
    ) -> Iterator[gpd.GeoDataFrame]:
        """
        Process data stream with memory optimization.

        Parameters
        ----------
        data_source : LazyGeodataFrame
            Lazy data source to process
        output_callback : callable, optional
            Callback function for each processed chunk
        adaptive_chunking : bool, optional
            Whether to adjust chunk size based on memory pressure

        Yields
        ------
        gpd.GeoDataFrame
            Processed chunks
        """
        base_chunk_size = data_source.chunk_size

        for chunk in data_source.chunks():
            # Adjust chunk size if memory pressure is high
            if adaptive_chunking:
                pressure = self.memory_monitor.check_memory_pressure()
                if pressure in ["high", "critical"]:
                    warnings.warn(f"High memory pressure detected: {pressure}", stacklevel=2)
                    # Force garbage collection
                    gc.collect()

                    # Reduce chunk size for future chunks
                    new_chunk_size = self.memory_monitor.suggest_chunk_size(
                        base_chunk_size
                    )
                    if new_chunk_size != base_chunk_size:
                        data_source.chunk_size = new_chunk_size
                        warnings.warn(f"Reduced chunk size to {new_chunk_size}", stacklevel=2)

            # Process chunk
            current_chunk = chunk  # Keep reference for error handling
            try:
                result = self.grid.intersects(chunk)
                self.processed_count += len(chunk)

                if output_callback:
                    output_callback(result)

                yield result

                # Clean up successful processing
                del result
                # Don't delete chunk here - wait until after error handling

                # Periodic garbage collection - optimize frequency based on memory pressure
                if self.processed_count % 10000 == 0:
                    pressure = self.memory_monitor.check_memory_pressure()
                    if pressure in ["high", "critical"]:
                        gc.collect()

            except MemoryError:
                warnings.warn("Memory error encountered, attempting recovery", stacklevel=2)
                gc.collect()

                # Try with smaller chunk using current_chunk reference
                if len(current_chunk) > 100:
                    # Split chunk in half and retry
                    mid = len(current_chunk) // 2
                    for sub_chunk in [current_chunk.iloc[:mid], current_chunk.iloc[mid:]]:
                        try:
                            result = self.grid.intersects(sub_chunk)
                            if output_callback:
                                output_callback(result)
                            yield result
                        except MemoryError:
                            warnings.warn(
                                f"Skipping problematic chunk of size {len(sub_chunk)}", 
                                stacklevel=2
                            )
                        finally:
                            del sub_chunk
                else:
                    warnings.warn(
                        f"Skipping small problematic chunk of size {len(current_chunk)}",
                        stacklevel=2
                    )

            finally:
                # Clean up chunk reference
                del chunk
                if 'current_chunk' in locals():
                    del current_chunk
                gc.collect()

    def get_processing_stats(self) -> dict:
        """
        Get processing statistics.

        Returns
        -------
        dict
            Processing statistics including memory usage
        """
        memory_stats = self.memory_monitor.get_memory_usage()
        return {
            "processed_features": self.processed_count,
            "memory_usage_mb": memory_stats["rss_mb"],
            "memory_percent": memory_stats["percent"],
            "memory_pressure": self.memory_monitor.check_memory_pressure(),
        }


def optimize_geodataframe_memory(
    gdf: gpd.GeoDataFrame, categorical_threshold: int = 10
) -> gpd.GeoDataFrame:
    """
    Optimize GeoDataFrame memory usage through type conversion and categorization.

    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        Input GeoDataFrame to optimize
    categorical_threshold : int, optional
        Maximum unique values for categorical conversion, by default 10

    Returns
    -------
    gpd.GeoDataFrame
        Memory-optimized GeoDataFrame
    """
    gdf_optimized = gdf.copy()

    # Batch process column optimizations to reduce overhead
    non_geom_cols = [col for col in gdf_optimized.columns if col != "geometry"]

    for col in non_geom_cols:
        col_dtype = gdf_optimized[col].dtype

        if col_dtype == "object":
            # Try to convert to category if small number of unique values
            unique_count = gdf_optimized[col].nunique()
            if unique_count <= categorical_threshold:
                gdf_optimized[col] = gdf_optimized[col].astype("category")
        elif pd.api.types.is_integer_dtype(col_dtype):
            # Downcast integer types
            gdf_optimized[col] = pd.to_numeric(gdf_optimized[col], downcast="integer")
        elif pd.api.types.is_float_dtype(col_dtype):
            # Downcast float types
            gdf_optimized[col] = pd.to_numeric(gdf_optimized[col], downcast="float")

    return gdf_optimized


def estimate_memory_usage(gdf: gpd.GeoDataFrame) -> dict:
    """
    Estimate memory usage of a GeoDataFrame.

    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        GeoDataFrame to analyze

    Returns
    -------
    dict
        Memory usage breakdown by column
    """
    memory_usage = {}

    for col in gdf.columns:
        if col == "geometry":
            # Estimate geometry memory usage (rough approximation)
            avg_coords = gdf.geometry.apply(
                lambda geom: len(geom.coords) if hasattr(geom, "coords") else 10
            ).mean()
            memory_usage[col] = (
                len(gdf) * avg_coords * 16
            )  # 8 bytes per coordinate (x,y)
        else:
            memory_usage[col] = gdf[col].memory_usage(deep=True)

    memory_usage["total"] = sum(memory_usage.values())
    memory_usage["total_mb"] = memory_usage["total"] / 1024 / 1024

    return memory_usage
