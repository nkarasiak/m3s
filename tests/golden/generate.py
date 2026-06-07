"""Freeze golden vectors from the CURRENT (pre-migration) Python m3s.

These JSON files are the parity contract of ADR 0001: the Rust-backed core
(``m3s_core``, and later the WASM build) must reproduce them exactly, proving
the migration introduced no behaviour change. Regenerate only deliberately.

    uv run python tests/golden/generate.py
"""

import json
from pathlib import Path

from m3s import (
    A5Grid,
    CSquaresGrid,
    EAQuadGrid,
    GARSGrid,
    GeohashGrid,
    H3Grid,
    MaidenheadGrid,
    MGRSGrid,
    PlusCodeGrid,
    QuadkeyGrid,
    S2Grid,
    SlippyGrid,
)

# Fixed sample points, spread across hemispheres (poles avoided).
POINTS = [
    (40.7128, -74.0060),  # New York
    (51.5074, -0.1278),  # London
    (-33.8688, 151.2093),  # Sydney
    (0.0, 0.0),  # null island
    (-23.5505, -46.6333),  # Sao Paulo
]

# MGRS excludes null island: (0,0) is equator + prime meridian + UTM zone edge,
# a degenerate case the geoconvert backend can't represent (the Python mgrs/PROJ
# backend can). Documented limitation; all other points/precisions match.
MGRS_POINTS = [p for p in POINTS if p != (0.0, 0.0)]

# name -> (grid class, precisions to freeze, hierarchical?).
# Non-hierarchical grids (GARS, Maidenhead) have no children/parent.
GRIDS = {
    "geohash": (GeohashGrid, [1, 5, 8], True),
    "h3": (H3Grid, [0, 5, 9], True),
    "quadkey": (QuadkeyGrid, [1, 8, 12], True),
    "slippy": (SlippyGrid, [0, 8, 12], True),
    "gars": (GARSGrid, [1, 2, 3], False),
    "maidenhead": (MaidenheadGrid, [1, 2, 4], False),
    "csquares": (CSquaresGrid, [1, 3, 5], True),
    "pluscode": (PlusCodeGrid, [1, 4, 6], True),
    "eaquad": (EAQuadGrid, [0, 4, 8], True),
    "mgrs": (MGRSGrid, [0, 1, 3, 5], False),
    "a5": (A5Grid, [0, 5, 10], True),
    "s2": (S2Grid, [0, 5, 13], True),
}

OUT = Path(__file__).parent


def ring_of(cell):
    """Closed [lon, lat] ring from a GridCell polygon exterior."""
    return [[x, y] for x, y in cell.polygon.exterior.coords]


def record(grid, lat, lon, precision, hierarchical):
    cell = grid.get_cell_from_point(lat, lon)
    rec = {
        "lat": lat,
        "lon": lon,
        "precision": precision,
        "id": cell.identifier,
        "cell_precision": cell.precision,
        "ring": ring_of(cell),
        "neighbors": sorted(c.identifier for c in grid.get_neighbors(cell)),
    }
    if hierarchical:
        rec["children"] = sorted(c.identifier for c in grid.get_children(cell))
        if precision > type(grid).MIN_PRECISION:
            rec["parent"] = grid.get_parent(cell).identifier
    return rec


def build(grid_cls, precisions, hierarchical, points):
    out = []
    for p in precisions:
        grid = grid_cls(p)
        for lat, lon in points:
            out.append(record(grid, lat, lon, p, hierarchical))
    return out


def main():
    for name, (grid_cls, precisions, hierarchical) in GRIDS.items():
        points = MGRS_POINTS if name == "mgrs" else POINTS
        (OUT / f"{name}.json").write_text(
            json.dumps(build(grid_cls, precisions, hierarchical, points), indent=2)
        )
    print(f"wrote golden vectors for {', '.join(GRIDS)} to {OUT}")


if __name__ == "__main__":
    main()
