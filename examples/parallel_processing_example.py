"""
Example: Parallel Processing and Streaming with M3S

Demonstrates the parallel processing capabilities including:
1. Dask distributed computing
2. GPU acceleration (if available)
3. Streaming data processing
4. Multi-grid batch operations
5. Performance monitoring
"""

import time
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import Point, box
import warnings

from m3s import (
    GeohashGrid, H3Grid, MGRSGrid,
    ParallelConfig, ParallelGridEngine,
    parallel_intersect, stream_grid_processing,
    create_data_stream, create_file_stream
)

def create_large_test_dataset(n_points: int = 1000) -> gpd.GeoDataFrame:
    """Create a large test dataset for parallel processing demonstration."""
    print(f"Creating test dataset with {n_points:,} points...")
    
    # Generate random points across continental US
    lats = np.random.uniform(25, 49, n_points)  # Continental US latitude range
    lons = np.random.uniform(-125, -66, n_points)  # Continental US longitude range
    
    geometries = [Point(lon, lat) for lat, lon in zip(lons, lats)]
    
    # Add some sample attributes
    data = {
        'id': range(n_points),
        'category': np.random.choice(['A', 'B', 'C', 'D'], n_points),
        'value': np.random.uniform(0, 100, n_points),
        'timestamp': pd.date_range('2024-01-01', periods=n_points, freq='1min')
    }
    
    return gpd.GeoDataFrame(data, geometry=geometries, crs="EPSG:4326")

def benchmark_processing_methods(gdf: gpd.GeoDataFrame):
    """Benchmark different processing methods."""
    print("\n" + "="*60)
    print("BENCHMARKING PROCESSING METHODS")
    print("="*60)
    
    grid = GeohashGrid(precision=5)
    sample_size = min(1000, len(gdf))  # Use smaller sample for benchmarking
    sample_gdf = gdf.sample(n=sample_size).reset_index(drop=True)
    
    print(f"Using sample of {sample_size:,} points for benchmarking...")
    
    # 1. Standard single-threaded processing
    print("\n1. Standard Processing (Single-threaded)")
    start_time = time.time()
    result_standard = grid.intersects(sample_gdf)
    standard_time = time.time() - start_time
    print(f"   Time: {standard_time:.2f} seconds")
    print(f"   Results: {len(result_standard):,} grid cells")
    
    # 2. Parallel processing with threading
    print("\n2. Parallel Processing (Threading)")
    config_threaded = ParallelConfig(use_dask=False, use_gpu=False, chunk_size=1000)
    start_time = time.time()
    result_parallel = parallel_intersect(grid, sample_gdf, config_threaded)
    parallel_time = time.time() - start_time
    print(f"   Time: {parallel_time:.2f} seconds")
    print(f"   Results: {len(result_parallel):,} grid cells")
    print(f"   Speedup: {standard_time/parallel_time:.2f}x")
    
    # 3. Dask processing (if available)
    try:
        print("\n3. Dask Distributed Processing")
        config_dask = ParallelConfig(use_dask=True, use_gpu=False, chunk_size=1000)
        engine = ParallelGridEngine(config_dask)
        
        if engine._client:
            start_time = time.time()
            result_dask = engine.intersect_parallel(grid, sample_gdf)
            dask_time = time.time() - start_time
            print(f"   Time: {dask_time:.2f} seconds")
            print(f"   Results: {len(result_dask):,} grid cells")
            print(f"   Speedup: {standard_time/dask_time:.2f}x")
        else:
            print("   Dask client not available - skipping")
    except Exception as e:
        print(f"   Dask processing failed: {e}")
    
    # 4. GPU processing (if available)
    try:
        print("\n4. GPU Processing (RAPIDS)")
        config_gpu = ParallelConfig(use_dask=False, use_gpu=True, chunk_size=1000)
        engine = ParallelGridEngine(config_gpu)
        
        start_time = time.time()
        result_gpu = engine.intersect_parallel(grid, sample_gdf)
        gpu_time = time.time() - start_time
        print(f"   Time: {gpu_time:.2f} seconds")
        print(f"   Results: {len(result_gpu):,} grid cells")
        print(f"   Speedup: {standard_time/gpu_time:.2f}x")
    except Exception as e:
        print(f"   GPU processing not available: {e}")

def demonstrate_streaming_processing(gdf: gpd.GeoDataFrame):
    """Demonstrate streaming data processing."""
    print("\n" + "="*60)
    print("STREAMING DATA PROCESSING")
    print("="*60)
    
    grid = H3Grid(resolution=6)
    chunk_size = 2000
    
    print(f"Processing {len(gdf):,} points in chunks of {chunk_size:,}...")
    
    # Create data stream
    data_stream = create_data_stream(gdf, chunk_size=chunk_size)
    
    # Track processing with callback
    processed_chunks = []
    total_cells = 0
    
    def chunk_callback(chunk_result):
        nonlocal total_cells
        processed_chunks.append(len(chunk_result))
        total_cells += len(chunk_result)
        print(f"   Processed chunk: {len(chunk_result):,} cells (Total: {total_cells:,})")
    
    config = ParallelConfig(use_dask=False, use_gpu=False, n_workers=4)
    
    start_time = time.time()
    result = stream_grid_processing(
        grid, 
        data_stream, 
        config, 
        output_callback=chunk_callback
    )
    processing_time = time.time() - start_time
    
    print(f"\nStreaming Processing Complete:")
    print(f"   Total time: {processing_time:.2f} seconds")
    print(f"   Chunks processed: {len(processed_chunks)}")
    print(f"   Total cells: {len(result):,}")
    print(f"   Processing rate: {len(gdf)/processing_time:.0f} points/second")

def demonstrate_multi_grid_processing(gdf: gpd.GeoDataFrame):
    """Demonstrate processing with multiple grid systems simultaneously."""
    print("\n" + "="*60)
    print("MULTI-GRID BATCH PROCESSING")
    print("="*60)
    
    # Create different grid systems
    grids = [
        GeohashGrid(precision=4),
        GeohashGrid(precision=5),
        H3Grid(resolution=5),
        H3Grid(resolution=6),
        MGRSGrid(precision=1)
    ]
    
    grid_names = [
        'geohash_p4',
        'geohash_p5', 
        'h3_res5',
        'h3_res6',
        'mgrs_p1'
    ]
    
    # Use subset for multi-grid demo
    sample_size = min(2000, len(gdf))
    sample_gdf = gdf.sample(n=sample_size).reset_index(drop=True)
    
    print(f"Processing {sample_size:,} points with {len(grids)} different grid systems...")
    
    config = ParallelConfig(use_dask=False, use_gpu=False, n_workers=4)
    engine = ParallelGridEngine(config)
    
    start_time = time.time()
    results = engine.batch_intersect_multiple_grids(grids, sample_gdf, grid_names)
    processing_time = time.time() - start_time
    
    print(f"\nMulti-Grid Processing Complete:")
    print(f"   Total time: {processing_time:.2f} seconds")
    print(f"   Grids processed: {len(results)}")
    
    print("\nResults by grid system:")
    for name, result in results.items():
        print(f"   {name:12}: {len(result):,} cells")
    
    return results

def visualize_multi_grid_results(results: dict, sample_gdf: gpd.GeoDataFrame):
    """Visualize results from multiple grid systems."""
    print("\nCreating visualization of multi-grid results...")
    
    # Select subset for visualization
    viz_bounds = (-100, 35, -95, 40)  # Focus on central US area
    
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle('Multi-Grid System Comparison', fontsize=16)
    
    axes = axes.flatten()
    
    # Plot original points
    ax = axes[0]
    sample_gdf.plot(ax=ax, markersize=0.5, alpha=0.6, color='red')
    ax.set_xlim(viz_bounds[0], viz_bounds[2])
    ax.set_ylim(viz_bounds[1], viz_bounds[3])
    ax.set_title('Original Points')
    ax.grid(True, alpha=0.3)
    
    # Plot each grid system
    for idx, (name, result) in enumerate(list(results.items())[:5]):
        ax = axes[idx + 1]
        
        if len(result) > 0:
            # Filter to visualization bounds
            result_subset = result.cx[viz_bounds[0]:viz_bounds[2], viz_bounds[1]:viz_bounds[3]]
            
            if len(result_subset) > 0:
                result_subset.plot(ax=ax, facecolor='lightblue', edgecolor='blue', 
                                 alpha=0.6, linewidth=0.5)
                ax.set_title(f'{name}\n({len(result_subset):,} cells in view)')
            else:
                ax.set_title(f'{name}\n(No cells in view)')
        else:
            ax.set_title(f'{name}\n(No results)')
        
        ax.set_xlim(viz_bounds[0], viz_bounds[2])
        ax.set_ylim(viz_bounds[1], viz_bounds[3])
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()

def demonstrate_performance_monitoring():
    """Demonstrate performance monitoring capabilities."""
    print("\n" + "="*60)
    print("PERFORMANCE MONITORING")
    print("="*60)
    
    # Try different configurations
    configs = [
        ("Threading", ParallelConfig(use_dask=False, use_gpu=False, n_workers=2)),
        ("Threading (4 workers)", ParallelConfig(use_dask=False, use_gpu=False, n_workers=4)),
        ("Dask", ParallelConfig(use_dask=True, use_gpu=False, n_workers=2)),
    ]
    
    for name, config in configs:
        print(f"\n{name} Configuration:")
        engine = ParallelGridEngine(config)
        stats = engine.get_performance_stats()
        
        for key, value in stats.items():
            if isinstance(value, dict):
                print(f"   {key}:")
                for subkey, subvalue in value.items():
                    print(f"      {subkey}: {subvalue}")
            else:
                print(f"   {key}: {value}")

def main():
    """Main demonstration function."""
    print("M3S Parallel Processing Demonstration")
    print("="*60)
    
    # Create test dataset
    gdf = create_large_test_dataset(n_points=10000)  # Moderate size for demo
    
    print(f"Test dataset created: {len(gdf):,} points")
    print(f"Bounds: {gdf.total_bounds}")
    print(f"Memory usage: ~{gdf.memory_usage(deep=True).sum() / 1024 / 1024:.1f} MB")
    
    # Run demonstrations
    try:
        benchmark_processing_methods(gdf)
        demonstrate_streaming_processing(gdf)
        
        # Multi-grid processing with visualization
        sample_gdf = gdf.sample(n=1000).reset_index(drop=True)
        results = demonstrate_multi_grid_processing(sample_gdf)
        
        # Show visualization
        try:
            visualize_multi_grid_results(results, sample_gdf)
        except Exception as e:
            print(f"Visualization failed: {e}")
        
        demonstrate_performance_monitoring()
        
    except KeyboardInterrupt:
        print("\nDemo interrupted by user")
    except Exception as e:
        print(f"\nDemo failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)
    print("DEMO COMPLETE")
    print("="*60)
    
    print("\nKey Features Demonstrated:")
    print("✓ Parallel processing with threading and Dask")
    print("✓ Streaming data processing for large datasets")
    print("✓ Multi-grid system batch operations")
    print("✓ Performance monitoring and benchmarking")
    print("✓ Graceful fallbacks for missing dependencies")
    
    print("\nTo enable additional features:")
    print("• Install Dask: pip install 'dask[complete]' distributed")
    print("• Install RAPIDS: pip install cupy cudf cuspatial")

if __name__ == "__main__":
    # Suppress warnings for cleaner demo output
    warnings.filterwarnings("ignore", category=FutureWarning)
    warnings.filterwarnings("ignore", category=UserWarning, message=".*Dask.*")
    
    main()