from __future__ import annotations

"""
Memory optimization utilities for M3S spatial operations.
"""

import gc
import warnings
from contextlib import contextmanager
from typing import Callable, Iterator, Optional, TYPE_CHECKING

if TYPE_CHECKING:
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
    """Monitor and manage memory usage during spatial operations."""

    def __init__(self, warn_threshold: float = 0.8, critical_threshold: float = 0.9):
        self.warn_threshold = warn_threshold
        self.critical_threshold = critical_threshold
        self.process = psutil.Process() if PSUTIL_AVAILABLE else None

    def get_memory_usage(self) -> dict:
        if not PSUTIL_AVAILABLE or not self.process:
            return {
                "rss_mb": 0.0,
                "vms_mb": 0.0,
                "percent": 50.0,
                "available_mb": 1000.0,
                "total_mb": 2000.0,
            }

        memory_info = self.process.memory_info()
        memory_percent = self.process.memory_percent()

        return {
            "rss_mb": memory_info.rss / 1024 / 1024,
            "vms_mb": memory_info.vms / 1024 / 1024,
            "percent": memory_percent,
            "available_mb": psutil.virtual_memory().available / 1024 / 1024,
            "total_mb": psutil.virtual_memory().total / 1024 / 1024,
        }

    def check_memory_pressure(self) -> str:
        usage = self.get_memory_usage()
        percent = usage["percent"] / 100

        if percent >= self.critical_threshold:
            return "critical"
        if percent >= self.warn_threshold:
            return "high"
        if percent >= 0.5:
            return "medium"
        return "low"

    def suggest_chunk_size(self, base_chunk_size: int = 10000) -> int:
        pressure = self.check_memory_pressure()

        if pressure == "critical":
            return max(100, base_chunk_size // 8)
        if pressure == "high":
            return max(500, base_chunk_size // 4)
        if pressure == "medium":
            return max(1000, base_chunk_size // 2)
        return base_chunk_size


@contextmanager
def memory_efficient_processing(
    auto_gc: bool = True, gc_threshold: int = 1000, monitor_memory: bool = True
):
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
    """Lazy-loading wrapper for GeoDataFrame to minimize memory usage."""

    def __init__(
        self,
        file_path: str | None = None,
        gdf: gpd.GeoDataFrame | None = None,
        chunk_size: int = 10000,
    ):
        if file_path and gdf is not None:
            raise ValueError("Provide either file_path OR gdf, not both")

        self.file_path = file_path
        self._gdf = gdf
        self.chunk_size = chunk_size
        self._length: int | None = None
        self._crs = None
        self._bounds = None

    def __len__(self) -> int:
        if self._length is None:
            if self._gdf is not None:
                self._length = len(self._gdf)
            else:
                import geopandas as gpd

                self._length = len(gpd.read_file(self.file_path))
        return self._length

    @property
    def crs(self):
        if self._crs is None:
            if self._gdf is not None:
                self._crs = self._gdf.crs
            else:
                import geopandas as gpd

                self._crs = gpd.read_file(self.file_path, rows=1).crs
        return self._crs

    @property
    def total_bounds(self):
        if self._bounds is None:
            if self._gdf is not None:
                self._bounds = self._gdf.total_bounds
            else:
                import geopandas as gpd

                self._bounds = gpd.read_file(self.file_path).total_bounds
        return self._bounds

    def iter_chunks(self) -> Iterator[gpd.GeoDataFrame]:
        if self._gdf is not None:
            for i in range(0, len(self._gdf), self.chunk_size):
                yield self._gdf.iloc[i : i + self.chunk_size]
        else:
            import geopandas as gpd

            yield from gpd.read_file(self.file_path, chunksize=self.chunk_size)


def optimize_geodataframe_memory(gdf: gpd.GeoDataFrame) -> gdf.GeoDataFrame:
    import pandas as pd

    optimized = gdf.copy()
    for col in optimized.columns:
        if col == "geometry":
            continue
        if pd.api.types.is_object_dtype(optimized[col]):
            num_unique = optimized[col].nunique(dropna=False)
            if num_unique / len(optimized) < 0.5:
                optimized[col] = optimized[col].astype("category")
    return optimized


def estimate_memory_usage(gdf: gpd.GeoDataFrame) -> dict:
    memory_usage = gdf.memory_usage(deep=True)
    total_mb = memory_usage.sum() / 1024 / 1024
    return {
        "total_mb": total_mb,
        "columns": {col: memory_usage[col] / 1024 / 1024 for col in gdf.columns},
    }


class StreamingGridProcessor:
    """Streaming processor for grid operations."""

    def __init__(
        self, processor: Callable[[gpd.GeoDataFrame], gpd.GeoDataFrame], chunk_size: int
    ):
        self.processor = processor
        self.chunk_size = chunk_size

    def process_stream(self, data: LazyGeodataFrame) -> gpd.GeoDataFrame:
        import geopandas as gpd
        import pandas as pd

        results = []
        for chunk in data.iter_chunks():
            results.append(self.processor(chunk))

        if not results:
            return gpd.GeoDataFrame()

        combined = pd.concat(results, ignore_index=True)
        return gpd.GeoDataFrame(combined, crs=results[0].crs)
