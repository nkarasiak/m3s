"""
Shared scaffold for the h3geo.org-style interactive grid maps.

This is a helper module, not a gallery example (it is excluded via the
gallery ``ignore_pattern``). Each ``*_interactive_map.py`` example supplies a
small JavaScript *driver* and calls :func:`build`.

A driver must define three JS functions:

``baseIdx(zoom)``
    Map the Leaflet zoom level to the coarsest precision index to draw.
``cellsInView(precision, west, south, east, north)``
    Return the cells covering the view at ``precision`` as an array of
    polygons, each polygon an array of ``[lat, lng]`` vertices.
``driverReady()`` *(optional)*
    Return ``true`` once any CDN library the driver needs has loaded.

The scaffold draws ``baseIdx``, ``baseIdx + 1`` and ``baseIdx + 2`` with
decreasing line weight (coarse on top), redrawing on every pan/zoom. Helpers
``tileRect`` (degree lattice) and ``tileMerc`` (Web Mercator tiles) are
available to drivers.
"""

import folium
from branca.element import MacroElement
from jinja2 import Template

_SCAFFOLD = r"""
{% macro script(this, kwargs) %}
var map = {{ this._parent.get_name() }};
var grp = L.layerGroup().addTo(map);
var STYLES = [{d: 2, weight: 0.5, color: "#888888", opacity: 0.55},
              {d: 1, weight: 1.2, color: "#555555", opacity: 0.7},
              {d: 0, weight: 2.6, color: "#222222", opacity: 0.9}];
var MAX_CELLS = 8000;

// Degree lattice: cells of lonStep x latStep aligned to (lonOff, latOff).
function tileRect(w, s, e, n, lonStep, latStep, lonOff, latOff, cap) {
    w = Math.max(-180, w); e = Math.min(180, e);
    s = Math.max(-85, s); n = Math.min(85, n);
    var x0 = Math.floor((w - lonOff) / lonStep);
    var x1 = Math.ceil((e - lonOff) / lonStep);
    var y0 = Math.floor((s - latOff) / latStep);
    var y1 = Math.ceil((n - latOff) / latStep);
    if ((x1 - x0) * (y1 - y0) > cap || x1 <= x0 || y1 <= y0) { return []; }
    var out = [];
    for (var xi = x0; xi < x1; xi++) {
        var lo = lonOff + xi * lonStep;
        for (var yi = y0; yi < y1; yi++) {
            var la = latOff + yi * latStep;
            out.push([[la, lo], [la, lo + lonStep],
                      [la + latStep, lo + lonStep], [la + latStep, lo]]);
        }
    }
    return out;
}

// Web Mercator tiles at tile-zoom T (slippy / quadkey grid).
function _np(v) { return Math.pow(2, v); }
function lon2x(lon, T) { return Math.floor((lon + 180) / 360 * _np(T)); }
function lat2y(lat, T) {
    var r = lat * Math.PI / 180;
    return Math.floor((1 - Math.log(Math.tan(r) + 1 / Math.cos(r)) / Math.PI)
                      / 2 * _np(T));
}
function x2lon(x, T) { return x / _np(T) * 360 - 180; }
function y2lat(y, T) {
    var a = Math.PI - 2 * Math.PI * y / _np(T);
    return 180 / Math.PI * Math.atan(0.5 * (Math.exp(a) - Math.exp(-a)));
}
function tileMerc(w, s, e, n, T, cap) {
    w = Math.max(-179.99, w); e = Math.min(179.99, e);
    s = Math.max(-85, s); n = Math.min(85, n);
    var x0 = lon2x(w, T), x1 = lon2x(e, T), y0 = lat2y(n, T), y1 = lat2y(s, T);
    if ((x1 - x0 + 1) * (y1 - y0 + 1) > cap) { return []; }
    var out = [];
    for (var x = x0; x <= x1; x++) {
        for (var y = y0; y <= y1; y++) {
            out.push([[y2lat(y, T), x2lon(x, T)], [y2lat(y, T), x2lon(x + 1, T)],
                      [y2lat(y + 1, T), x2lon(x + 1, T)],
                      [y2lat(y + 1, T), x2lon(x, T)]]);
        }
    }
    return out;
}

// ---- grid-specific driver ----
{{ this.driver }}

function redraw() {
    if (typeof driverReady === "function" && !driverReady()) { return; }
    grp.clearLayers();
    var b = map.getBounds();
    var w = b.getWest(), e = b.getEast(), s = b.getSouth(), n = b.getNorth();
    if (e - w >= 360 || e <= w) { w = -180; e = 180; }
    var base = baseIdx(map.getZoom());
    STYLES.forEach(function (st) {
        var cells;
        try { cells = cellsInView(base + st.d, w, s, e, n); }
        catch (err) { return; }
        if (!cells || cells.length > MAX_CELLS) { return; }
        cells.forEach(function (poly) {
            var lngs = poly.map(function (p) { return p[1]; });
            if (Math.max.apply(null, lngs) -
                Math.min.apply(null, lngs) > 180) { return; }
            L.polygon(poly, {
                fill: false, color: st.color, weight: st.weight,
                opacity: st.opacity, interactive: false
            }).addTo(grp);
        });
    });
}
map.on("moveend", redraw);
(function wait() {
    if (typeof driverReady !== "function" || driverReady()) { redraw(); }
    else { setTimeout(wait, 120); }
})();
{% endmacro %}
"""


class _GridLayer(MacroElement):
    """MacroElement that injects the scaffold + a grid driver."""

    def __init__(self, driver: str):
        super().__init__()
        self.driver = driver
        self._template = Template(_SCAFFOLD)


def build(
    driver: str,
    *,
    zoom_start: int = 2,
    min_zoom: int = 2,
    lib_urls: tuple = (),
) -> folium.Map:
    """Build a Positron map with the injected grid driver.

    Parameters
    ----------
    driver : str
        JavaScript defining ``baseIdx``, ``cellsInView`` and optionally
        ``driverReady``.
    zoom_start, min_zoom : int
        Initial and minimum Leaflet zoom.
    lib_urls : tuple of str
        Optional CDN script URLs to load before the driver.
    """
    fmap = folium.Map(
        location=[25.0, 0.0],
        zoom_start=zoom_start,
        min_zoom=min_zoom,
        tiles=None,
        control_scale=True,
        max_bounds=True,
    )
    folium.TileLayer("CartoDB positron", no_wrap=True, control=False).add_to(fmap)
    for url in lib_urls:
        fmap.get_root().header.add_child(
            folium.Element('<script src="%s"></script>' % url)
        )
    fmap.add_child(_GridLayer(driver))
    return fmap
