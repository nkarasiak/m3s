"""
Maidenhead grid
===============

The Maidenhead Locator System used by amateur radio operators. Fields and
squares tile the globe in 2° × 1° squares (precision 2), refinable into
subsquares.

The **interactive explorer** below is rendered with
`deck.gl <https://deck.gl/>`_ and behaves like the
`h3geo.org <https://h3geo.org/>`_ map: the Maidenhead precision follows the zoom
and locators are generated **in the browser** for whatever is in view. Two
neighbouring precisions are shown at once — the current level with a darker,
heavier border and the next finer level with a lighter, thinner one — so the
field → square → subsquare nesting stays visible. The field/square/subsquare
encoder is the exact one in :mod:`m3s.maidenhead`, reproduced in JavaScript so
the locators and edges match M3S. GIS-native ``(lon, lat)`` order is used
throughout.
"""

from _deckmap import DeckExplorer, read_grid_js

# sphinx_gallery_thumbnail_path = '_static/thumbs/maidenhead.png'

DeckExplorer(
    center=(9.5, 48.5), zoom=5, grid_js=read_grid_js("maidenhead"), hover="#882255"
)
