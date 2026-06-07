"""
MGRS grid
=========

Military Grid Reference System, built on UTM. Square cells whose identifier
length sets precision (100 km → 1 m). Widely used for surveying and defence.

The **interactive explorer** below is rendered with
`deck.gl <https://deck.gl/>`_ and behaves like the
`h3geo.org <https://h3geo.org/>`_ map: the MGRS precision follows the zoom and
cells are generated **in the browser** for whatever is in view. Two neighbouring
precisions are shown at once — the current level with a darker, heavier border
and the next finer level with a lighter, thinner one. The cell references come
from `mgrs <https://github.com/proj4js/mgrs>`_ and the per-zone UTM squares from
`proj4js <http://proj4js.org/>`_, reproducing the exact M3S maths so the
references and edges match :mod:`m3s.mgrs`. MGRS only refines down to 100 km, so
it has no whole-globe level — zoom out and the explorer asks you to zoom back in.
GIS-native ``(lon, lat)`` order is used throughout.
"""

from _deckmap import DeckExplorer, read_grid_js

# sphinx_gallery_thumbnail_path = '_static/thumbs/mgrs.png'

DeckExplorer(
    center=(2.35, 48.85),
    zoom=7,
    grid_js=read_grid_js("mgrs"),
    hover="#332288",
    wasm=True,
)
