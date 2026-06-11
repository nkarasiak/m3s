"""Generate gallery thumbnails for the grid-system examples.

Each deck.gl explorer renders an interactive iframe (no matplotlib figure), so
Sphinx-Gallery has no plot to thumbnail. This script draws a small, basemap-free
nested-resolution sketch per grid into ``docs/_static/thumbs/<grid>.png``, which
the examples reference via ``# sphinx_gallery_thumbnail_path``.

Run once (the file is ignored by Sphinx-Gallery)::

    uv run python examples/grid_systems/_make_thumbs.py
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import m3s  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "docs" / "_static" / "thumbs"

# (slug, grid class, bbox, [coarse..fine resolutions])
GRIDS = [
    ("h3", m3s.H3, (2.30, 48.84, 2.40, 48.94), [5, 6, 7]),
    ("eaquad", m3s.EAQuad, (2.30, 48.84, 2.40, 48.94), [6, 7, 8]),
    ("a5", m3s.A5, (1.5, 48.2, 3.2, 49.5), [6, 7, 8]),
    ("geohash", m3s.Geohash, (2.30, 48.84, 2.40, 48.94), [5, 6]),
    ("quadkey", m3s.Quadkey, (2.30, 48.84, 2.40, 48.94), [12, 13, 14]),
    ("slippy", m3s.Slippy, (2.30, 48.84, 2.40, 48.94), [12, 13, 14]),
    ("csquares", m3s.CSquares, (1.0, 47.0, 3.0, 49.0), [3, 4, 5]),
    ("gars", m3s.GARS, (2.0, 48.0, 3.0, 49.0), [1, 2, 3]),
    ("maidenhead", m3s.Maidenhead, (4.0, 44.0, 18.0, 52.0), [1, 2]),
    ("pluscode", m3s.PlusCode, (8.0, 48.0, 10.0, 49.0), [2, 3]),
    ("s2", m3s.S2, (1.5, 48.2, 3.2, 49.5), [7, 8, 9]),
    ("mgrs", m3s.MGRS, (2.1, 48.75, 2.55, 49.0), [1, 2]),
]

WEIGHTS = {3: [3.5, 1.8, 0.7], 2: [3.0, 0.7]}
SHADES = {3: ["#000000", "#555555", "#999999"], 2: ["#000000", "#999999"]}


def build_layers(grid_cls, bbox, resolutions):
    """Coarsest over the bbox, then finer levels over the coarse extent."""
    coarse = grid_cls.from_geometry(bbox, precision=resolutions[0]).to_gdf()
    extent = tuple(coarse.total_bounds)
    layers = [coarse]
    layers += [
        grid_cls.from_geometry(extent, precision=r).to_gdf() for r in resolutions[1:]
    ]
    return layers


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for slug, grid_cls, bbox, resolutions in GRIDS:
        layers = build_layers(grid_cls, bbox, resolutions)
        n = len(resolutions)
        fig, ax = plt.subplots(figsize=(2.4, 2.4))
        for gdf, weight, shade in zip(layers, WEIGHTS[n], SHADES[n], strict=False):
            gdf.to_crs(epsg=3857).plot(
                ax=ax, facecolor="none", edgecolor=shade, linewidth=weight
            )
        xmin, ymin, xmax, ymax = layers[0].to_crs(epsg=3857).total_bounds
        ax.set_xlim(xmin, xmax)
        ax.set_ylim(ymin, ymax)
        ax.set_axis_off()
        fig.patch.set_facecolor("white")
        plt.tight_layout(pad=0.1)
        out = OUT / f"{slug}.png"
        fig.savefig(out, dpi=100, facecolor="white")
        plt.close(fig)
        print(f"wrote {out}")


if __name__ == "__main__":
    main()
