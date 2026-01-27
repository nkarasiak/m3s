"""Intersection operations between grids and GeoDataFrames."""

from __future__ import annotations

import geopandas as gpd
import numpy as np
from shapely.strtree import STRtree

from ..core.grid import GridProtocol


def _empty_result(gdf: gpd.GeoDataFrame, crs: str) -> gpd.GeoDataFrame:
    columns = ["cell_id", "precision", "geometry"]
    columns.extend([col for col in gdf.columns if col != "geometry"])
    return gpd.GeoDataFrame(columns=columns, crs=crs)


def intersects(
    grid: GridProtocol,
    gdf: gpd.GeoDataFrame,
    target_crs: str = "EPSG:4326",
) -> gpd.GeoDataFrame:
    """Return all grid cells intersecting geometries in a GeoDataFrame."""
    if gdf.empty:
        return _empty_result(gdf, gdf.crs or target_crs)

    original_crs = gdf.crs
    if original_crs is None:
        raise ValueError("GeoDataFrame CRS must be defined")

    gdf_transformed = gdf.to_crs(target_crs) if original_crs != target_crs else gdf

    geometries = gdf_transformed.geometry
    valid_mask = geometries.notna() & ~geometries.is_empty
    if not bool(valid_mask.any()):
        return _empty_result(gdf, target_crs)

    valid_mask_values = valid_mask.to_numpy()
    valid_indices = np.flatnonzero(valid_mask_values)
    valid_geometries = geometries.array[valid_mask_values]
    non_geom_cols = [col for col in gdf.columns if col != "geometry"]
    non_geom_values = None
    if non_geom_cols:
        non_geom_values = gdf.iloc[valid_indices][non_geom_cols].to_numpy()

    min_lon, min_lat, max_lon, max_lat = geometries.iloc[valid_indices].total_bounds
    cells = list(grid.cells_in_bbox((min_lon, min_lat, max_lon, max_lat)))
    if not cells:
        return _empty_result(gdf, target_crs)

    if len(cells) > 50000 and len(valid_geometries) > 1:
        index_to_pos = {
            idx: pos for pos, idx in enumerate(gdf_transformed.index[valid_mask])
        }
        rows_with_order = []
        rows_with_order_append = rows_with_order.append
        sindex = gdf_transformed.sindex

        for cell_idx, cell in enumerate(cells):
            candidate_indices = list(sindex.intersection(cell.bbox))
            if not candidate_indices:
                continue
            cell_polygon = None
            for candidate in candidate_indices:
                pos = index_to_pos.get(candidate)
                if pos is None:
                    continue
                geometry = valid_geometries[pos]
                if geometry is None or geometry.is_empty:
                    continue
                if cell_polygon is None:
                    cell_polygon = cell.polygon
                if geometry.intersects(cell_polygon):
                    row = {
                        "cell_id": cell.id,
                        "precision": cell.precision,
                        "geometry": cell_polygon,
                    }
                    if non_geom_values is not None:
                        for col, value in zip(non_geom_cols, non_geom_values[pos]):
                            row[col] = value
                    rows_with_order_append((pos, cell_idx, row))

        if not rows_with_order:
            return _empty_result(gdf, target_crs)

        rows_with_order.sort(key=lambda item: (item[0], item[1]))
        rows = [row for _, _, row in rows_with_order]
        result = gpd.GeoDataFrame(rows, crs=target_crs)
        if original_crs != target_crs:
            result = result.to_crs(original_crs)
        return result

    cell_polygons = [cell.polygon for cell in cells]
    cell_gdf = gpd.GeoDataFrame(
        {
            "cell_id": [cell.id for cell in cells],
            "precision": [cell.precision for cell in cells],
        },
        geometry=cell_polygons,
        crs=target_crs,
    )

    if non_geom_cols:
        right = gdf_transformed.loc[valid_mask, non_geom_cols + ["geometry"]]
    else:
        right = gdf_transformed.loc[valid_mask, ["geometry"]]

    try:
        joined = gpd.sjoin(cell_gdf, right, how="inner", predicate="intersects")
    except Exception:
        joined = None

    if joined is not None:
        if joined.empty:
            return _empty_result(gdf, target_crs)
        joined = joined.reset_index().rename(columns={"index": "_cell_idx"})
        sort_cols = ["index_right", "_cell_idx"]
        joined = joined.sort_values(by=sort_cols, kind="mergesort")
        joined = joined.drop(columns=["index_right", "_cell_idx"], errors="ignore")
        ordered_cols = ["cell_id", "precision", "geometry"]
        if non_geom_cols:
            ordered_cols.extend(non_geom_cols)
        joined = joined[ordered_cols]
        if original_crs != target_crs:
            joined = joined.to_crs(original_crs)
        return joined

    polygons = cell_polygons
    tree = STRtree(polygons)

    rows = []
    source_indices = []
    try:
        pairs = tree.query_bulk(valid_geometries, predicate="intersects")
        pairs = np.asarray(pairs)
    except Exception:
        pairs = None

    if pairs is not None:
        if pairs.size == 0:
            return _empty_result(gdf, target_crs)
        src_positions = pairs[0]
        cell_indices = pairs[1]
        for src_pos, cell_idx in zip(src_positions, cell_indices):
            cell = cells[int(cell_idx)]
            rows.append(
                {
                    "cell_id": cell.id,
                    "precision": cell.precision,
                    "geometry": cell.polygon,
                }
            )
            source_indices.append(int(valid_indices[int(src_pos)]))
    else:
        for src_idx, geometry in zip(valid_indices, valid_geometries):
            matches = tree.query(geometry, predicate="intersects")
            for match_idx in matches:
                cell = cells[int(match_idx)]
                rows.append(
                    {
                        "cell_id": cell.id,
                        "precision": cell.precision,
                        "geometry": cell.polygon,
                    }
                )
                source_indices.append(int(src_idx))

    if not rows:
        return _empty_result(gdf, target_crs)

    result = gpd.GeoDataFrame(rows, crs=target_crs)
    non_geom_cols = [col for col in gdf.columns if col != "geometry"]
    if non_geom_cols:
        result[non_geom_cols] = gdf.iloc[source_indices][non_geom_cols].reset_index(
            drop=True
        )

    if original_crs != target_crs:
        result = result.to_crs(original_crs)

    return result
