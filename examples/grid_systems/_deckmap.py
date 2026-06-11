"""Shared deck.gl explorer for the grid-system gallery examples.

Builds an `h3geo.org <https://h3geo.org/>`_-style interactive map rendered with
`deck.gl <https://deck.gl/>`_: a CartoDB Positron raster basemap (drawn by a
deck.gl ``TileLayer``) with two neighbouring grid resolutions overlaid. The
resolution follows the zoom; the finer level draws a light, thin border and the
current level a darker, heavier one, so the hierarchical nesting stays visible.
Hovering a cell highlights it and shows its id.

Each example supplies a small JavaScript object describing its grid — a
``window.__GRID__`` with a ``resForZoom`` mapping, a ``label`` formatter and a
``cells(res, bounds, data)`` generator that returns ``[{id, poly, sub}]`` where
``poly`` is a ``[[lon, lat], ...]`` ring (GIS-native order). This module wires
that object into deck.gl, so the per-grid files only carry the grid maths.

The map is emitted as a self-contained ``<iframe srcdoc>``; Sphinx-Gallery
captures the ``_repr_html_`` and the docs ``hero-map.js`` hoists the iframe to
the top of the page. deck.gl and any per-grid library load from a CDN in the
reader's browser, so building the docs stays offline and fast.
"""

import base64
import html
import json
import pathlib

# Per-grid ``window.__GRID__`` definitions live as standalone .js files next to
# this module, so the example .py files stay free of inlined JavaScript.
_GRIDS_DIR = pathlib.Path(__file__).parent / "_grids"

# Web-target WASM build of the shared core (``wasm-pack build bindings/js
# --target web --out-dir pkg-web``). Gitignored; build before rendering examples
# that tile via the core.
_PKG_WEB = pathlib.Path(__file__).parents[2] / "bindings" / "js" / "pkg-web"


def read_grid_js(name):
    """Return the ``window.__GRID__`` JavaScript from ``_grids/<name>.js``."""
    return (_GRIDS_DIR / f"{name}.js").read_text(encoding="utf-8")


def _wasm_loader():
    """HTML that instantiates the core WASM in-page and exposes ``window.__M3S__``.

    The examples render as offline self-contained ``<iframe srcdoc>`` (no base
    URL to fetch from), so the wasm-bindgen glue and the ``.wasm`` are
    base64-inlined and the module is instantiated from bytes. A classic script
    sets ``__M3S_PENDING__`` *before* the harness runs (module scripts are
    deferred), so the harness knows to wait for the ``m3s-ready`` event.
    """
    glue = (_PKG_WEB / "m3s_core_js.js").read_text(encoding="utf-8")
    wasm = (_PKG_WEB / "m3s_core_js_bg.wasm").read_bytes()
    glue_b64 = base64.b64encode(glue.encode("utf-8")).decode("ascii")
    wasm_b64 = base64.b64encode(wasm).decode("ascii")
    return (
        "<script>window.__M3S_PENDING__ = true;</script>\n"
        '<script type="module">\n'
        f'import init, * as m3s from "data:text/javascript;base64,{glue_b64}";\n'
        f'const _bytes = Uint8Array.from(atob("{wasm_b64}"), c => c.charCodeAt(0));\n'
        "await init({module_or_path: _bytes});\n"
        "window.__M3S__ = m3s;\n"
        # Bulk core results are columnar {ids, coords, offsets, precisions};
        # this rebuilds the [{id, ring, precision}] list the grid files map over.
        "window.__M3S_CELLS__ = function (packed) {\n"
        "  if (!packed.ids) return [];\n"
        '  const ids = packed.ids.split("\\n");\n'
        "  const out = new Array(ids.length);\n"
        "  for (let i = 0; i < ids.length; i++) {\n"
        "    const ring = [];\n"
        "    for (let v = packed.offsets[i]; v < packed.offsets[i + 1]; v++) {\n"
        "      ring.push([packed.coords[2 * v], packed.coords[2 * v + 1]]);\n"
        "    }\n"
        "    out[i] = { id: ids[i], ring: ring, precision: packed.precisions[i] };\n"
        "  }\n"
        "  return out;\n"
        "};\n"
        'window.dispatchEvent(new Event("m3s-ready"));\n'
        "</script>"
    )


# deck.gl standalone (scripting) UMD bundle: exposes DeckGL, TileLayer,
# BitmapLayer, PolygonLayer and WebMercatorViewport on the global ``deck``.
_DECK_CDN = "https://unpkg.com/deck.gl@9/dist.min.js"

# The harness. __TOKENS__ are substituted in :meth:`DeckExplorer._doc`; the
# per-grid window.__GRID__ object is loaded from a separate <script> first.
_HARNESS = r"""
const {DeckGL, TileLayer, BitmapLayer, PolygonLayer, WebMercatorViewport} = deck;
const HOVER = __HOVER__;
const DATA = __DATA__;
const G = window.__GRID__;
const badge = document.getElementById('badge');

// A cell straddling the antimeridian comes back with longitudes that jump ~360°
// between consecutive vertices; drawn raw it streaks clear across the map.
// Unwrap each ring so neighbouring lons stay within 180° of each other (the
// polygon may then run past ±180°, which the Mercator view renders correctly).
function unwrap(ring) {
  const out = [ring[0].slice()];
  for (let i = 1; i < ring.length; i++) {
    let lon = ring[i][0];
    const prev = out[i - 1][0];
    while (lon - prev > 180) lon -= 360;
    while (lon - prev < -180) lon += 360;
    out.push([lon, ring[i][1]]);
  }
  return out;
}

// CartoDB Positron raster basemap, drawn entirely by deck.gl (no MapLibre).
const basemap = new TileLayer({
  id: 'carto-positron',
  data: 'https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
  minZoom: 0, maxZoom: 19, tileSize: 256,
  renderSubLayers: props => {
    const t = props.tile;
    let w, s, e, n;
    if (t.boundingBox) {
      w = t.boundingBox[0][0]; s = t.boundingBox[0][1];
      e = t.boundingBox[1][0]; n = t.boundingBox[1][1];
    } else {
      w = t.bbox.west; s = t.bbox.south; e = t.bbox.east; n = t.bbox.north;
    }
    return new BitmapLayer(props,
      {data: null, image: props.data, bounds: [w, s, e, n]});
  }
});

// View bounds as {w, s, e, n} so the per-grid cell generator can tile the view.
function viewBounds(vs) {
  const vp = new WebMercatorViewport(Object.assign({}, vs, {
    width: window.innerWidth || 800, height: window.innerHeight || 600
  }));
  const b = vp.getBounds();
  return {w: b[0], s: b[1], e: b[2], n: b[3]};
}

// Cells are generated for a view padded by PAD on each side and the resulting
// layers cached, so panning inside the padded area (and any view change that
// keeps the same resolution) reuses the existing GPU buffers instead of
// re-tiling the grid on every camera frame. PAD_AREA is how much bigger the
// padded view is; the per-grid cell caps scale by it so the on-screen density
// thresholds stay as authored.
const PAD = 0.25, PAD_AREA = (1 + 2 * PAD) * (1 + 2 * PAD);
function padBounds(b) {
  const dw = (b.e - b.w) * PAD, dh = (b.n - b.s) * PAD;
  return {w: b.w - dw, e: b.e + dw,
          s: Math.max(-85.0511, b.s - dh), n: Math.min(85.0511, b.n + dh)};
}
function covers(outer, b) {
  return b.w >= outer.w && b.e <= outer.e && b.s >= outer.s && b.n <= outer.n;
}
let cache = null;  // {want, bounds, layers}
function layersFor(vs) {
  const want = G.resForZoom(vs.zoom);
  const view = viewBounds(vs);
  if (cache && cache.want === want && covers(cache.bounds, view)) {
    return cache.layers;
  }
  const bounds = padBounds(view);
  const layers = build(want, bounds);
  cache = {want, bounds, layers};
  return layers;
}

function build(want, b) {
  let res = want;
  let cells = G.cells(res, b, DATA);
  const limit = (G.limit || 3000) * PAD_AREA;
  const minRes = G.minRes || 0, noun = G.noun || 'cells';
  // Step coarser until the current level is a manageable size.
  while (cells.length > limit && res > minRes) {
    res -= 1; cells = G.cells(res, b, DATA);
  }
  if (G.maxRender && cells.length > G.maxRender * PAD_AREA) {
    badge.innerHTML = '<b>' + G.name + '</b> &middot; zoom in to render ' + noun;
    return [basemap];
  }
  const tipName = G.tipName || G.name;
  cells.forEach(d => {
    d.poly = unwrap(d.poly);
    d.tip = tipName + ' ' + d.id + (d.sub ? '<br>' + d.sub : '');
  });
  // Finer level (res + fineStep; one step finer by default, but a grid whose
  // resolutions step by less than aperture-4 can preview two steps so the
  // nesting reads). Drawn first with a light, thin border so the current
  // level's darker cells sit on top and the nesting stays visible.
  const fineStep = G.fineStep || 1;
  const fineRes = res + fineStep;
  // Skip the finer preview when it cannot help: past the grid's max resolution
  // (G.maxRes), or when one finer step would explode the cell count. High-
  // aperture grids (Plus Codes step x400 per level) declare G.fineRatio so the
  // blow-up is caught *before* generating — otherwise the page locks building
  // hundreds of thousands of polygons it would then discard.
  const fineLimit = (G.fineLimit || 12000) * PAD_AREA;
  const skipFine = (G.maxRes != null && fineRes > G.maxRes) ||
    (G.fineRatio && cells.length * G.fineRatio > fineLimit);
  const fine = skipFine ? [] : G.cells(fineRes, b, DATA);
  const fineData = fine.length <= fineLimit ? fine : [];
  fineData.forEach(d => { d.poly = unwrap(d.poly); });
  const layers = [
    basemap,
    new PolygonLayer({
      id: 'fine', data: fineData, getPolygon: d => d.poly,
      stroked: true, filled: false,
      getLineColor: [165, 165, 165], getLineWidth: 0.7,
      lineWidthUnits: 'pixels', lineWidthMinPixels: 0.7, pickable: false
    }),
    new PolygonLayer({
      id: 'cur', data: cells, getPolygon: d => d.poly,
      // Transparent fill (not unfilled) so the whole cell area is hoverable.
      stroked: true, filled: true, getFillColor: [0, 0, 0, 0],
      getLineColor: [34, 34, 34], getLineWidth: 1,
      lineWidthUnits: 'pixels', lineWidthMinPixels: 1,
      pickable: true, autoHighlight: true,
      highlightColor: [HOVER[0], HOVER[1], HOVER[2], 140]
    })
  ];
  const cur = G.label(res), nxt = skipFine ? '' : G.label(fineRes);
  badge.innerHTML = '<b>' + G.name + '</b> &middot; ' + cur + ' &middot; ' +
    cells.length + ' ' + noun +
    (nxt ? ' <span style="color:#999">(+ ' + nxt + ')</span>' : '');
  return layers;
}

// Persist the view in the page URL as #zoom/lat/lon so a particular grid view
// is shareable and reproducible. The map is a same-origin `srcdoc` iframe, so it
// reads/writes the hosting page's hash via window.top; the zoom carries the
// resolution (resForZoom). Wrapped in try/catch in case the frame is ever
// embedded cross-origin.
function readHash() {
  try {
    const p = (window.top.location.hash || '').replace(/^#/, '').split('/').map(Number);
    if (p.length === 3 && p.every(Number.isFinite)) {
      return {zoom: p[0], latitude: p[1], longitude: p[2]};
    }
  } catch (e) {}
  return null;
}
let hashPending = false;
function writeHash(vs) {
  if (hashPending) return;
  hashPending = true;
  requestAnimationFrame(() => {
    hashPending = false;
    const h = '#' + vs.zoom.toFixed(2) + '/' + vs.latitude.toFixed(4) +
      '/' + vs.longitude.toFixed(4);
    try {
      const loc = window.top.location;
      window.top.history.replaceState(null, '', loc.pathname + loc.search + h);
    } catch (e) {}
  });
}
const INIT = Object.assign(
  {longitude: __LON__, latitude: __LAT__, zoom: __ZOOM__}, readHash() || {});
function start() {
  // Coalesce camera events to one layer update per animation frame; most
  // frames hit the bounds cache and hand deck the same layer instances (a
  // no-op diff), so cells regenerate only on a resolution change or when the
  // view escapes the padded bounds.
  let pendingVS = null, rafId = 0;
  const deckgl = new DeckGL({
    container: 'map', initialViewState: INIT,
    controller: G.minZoom ? {minZoom: G.minZoom} : true,
    getTooltip: ({object}) => object && {html: object.tip},
    layers: layersFor(INIT),
    onViewStateChange: ({viewState}) => {
      writeHash(viewState);
      pendingVS = viewState;
      if (!rafId) {
        rafId = requestAnimationFrame(() => {
          rafId = 0;
          deckgl.setProps({layers: layersFor(pendingVS)});
        });
      }
    }
  });
}
// When the grid's cells come from the WASM core, wait for it to instantiate.
const ready = window.__M3S_PENDING__
  ? new Promise(r => window.addEventListener('m3s-ready', r, {once: true}))
  : Promise.resolve();
ready.then(start);

const fs = document.getElementById('fs');
fs.onclick = () => {
  const el = document.getElementById('map');
  if (document.fullscreenElement) document.exitFullscreen();
  else if (el.requestFullscreen) el.requestFullscreen();
};
"""

_DOC = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  html, body { margin: 0; padding: 0; height: 100%; }
  #map { position: absolute; inset: 0; }
  #badge { position: absolute; top: 8px; right: 8px; z-index: 1;
    background: #fff; padding: 4px 8px; border-radius: 4px;
    font: 12px sans-serif; box-shadow: 0 1px 4px rgba(0,0,0,.3); }
  #fs { position: absolute; top: 8px; left: 8px; z-index: 1; cursor: pointer;
    background: #fff; width: 26px; height: 26px; line-height: 26px;
    text-align: center; border-radius: 4px; font: 15px sans-serif;
    box-shadow: 0 1px 4px rgba(0,0,0,.3); user-select: none; }
  .deck-tooltip { font: 12px sans-serif !important; }
</style>
__SCRIPTS__
<script src="__DECK__"></script>
</head>
<body>
<div id="map"></div>
<div id="fs" title="Fullscreen">&#9974;</div>
<div id="badge"></div>
__WASM__
<script>__GRIDJS__</script>
<script>__HARNESS__</script>
</body></html>"""


def _rgb(hex_color):
    """``'#ffeb3b'`` -> ``[255, 235, 59]`` for deck.gl highlight colours."""
    h = hex_color.lstrip("#")
    return [int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)]


class DeckExplorer:
    """A zoom-driven, two-resolution deck.gl grid explorer for the gallery.

    Parameters
    ----------
    center : tuple of float
        ``(lon, lat)`` of the initial view centre (GIS-native order).
    zoom : float
        Initial Web-Mercator zoom level.
    grid_js : str
        JavaScript that assigns ``window.__GRID__`` (see module docstring).
    scripts : sequence of str, optional
        Extra CDN script URLs (e.g. ``h3-js``, ``proj4``, ``a5-js``).
    data : object, optional
        JSON-serialisable data passed to ``__GRID__.cells`` as its third
        argument, for grids whose cells are pre-computed by M3S (S2, MGRS).
    hover : str, optional
        Hex colour used to highlight the hovered cell.
    height : int, optional
        Iframe height in pixels.
    """

    def __init__(
        self,
        *,
        center,
        zoom,
        grid_js,
        scripts=(),
        data=None,
        hover="#ffeb3b",
        height=600,
        wasm=False,
    ):
        self.lon, self.lat = center
        self.zoom = zoom
        self.grid_js = grid_js
        self.scripts = tuple(scripts)
        self.data = data
        self.hover = _rgb(hover)
        self.height = height
        # When True, the grid's ``cells`` come from the shared core's WASM build
        # (``window.__M3S__``), inlined into the iframe; the harness waits for it.
        self.wasm = wasm

    def _doc(self):
        harness = (
            _HARNESS.replace("__HOVER__", json.dumps(self.hover))
            .replace(
                "__DATA__", json.dumps(self.data) if self.data is not None else "null"
            )
            .replace("__LON__", repr(self.lon))
            .replace("__LAT__", repr(self.lat))
            .replace("__ZOOM__", repr(self.zoom))
        )
        scripts = "\n".join(
            '<script src="{}"></script>'.format(s) for s in self.scripts
        )
        return (
            _DOC.replace("__SCRIPTS__", scripts)
            .replace("__DECK__", _DECK_CDN)
            .replace("__WASM__", _wasm_loader() if self.wasm else "")
            .replace("__GRIDJS__", self.grid_js)
            .replace("__HARNESS__", harness)
        )

    def _repr_html_(self):
        srcdoc = html.escape(self._doc(), quote=True)
        return (
            '<iframe srcdoc="{}" style="width:100%;height:{}px;border:none;" '
            "allowfullscreen></iframe>"
        ).format(srcdoc, self.height)
