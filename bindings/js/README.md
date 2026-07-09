# m3s — JavaScript / WASM

> [!WARNING]
> This project is a vibe-coded experiment built entirely with [Claude Code](https://claude.com/claude-code) as a test of AI-assisted development. It is **not production-tested or audited**. For a mature, production-grade unified grid library, use [**vgrid**](https://github.com/opengeoshub/vgrid) instead.

An ergonomic JS API over the shared **m3s** Rust core. The grid classes mirror
the Python facade (`m3s.H3`, `m3s.Geohash`, …) in camelCase and produce
**identical results** — JS and Python consume the same `m3s-core` crate.

This is a thin layer: it wraps the generated WASM functions into classes and
computed getters and never reimplements grid math.

## Install

```bash
npm install @nkarasiak/m3s
```

The package ships both a Node (CommonJS WASM) and a browser (ESM WASM) build;
the right one is selected automatically through the `exports` map.

## Use

```js
import * as m3s from "@nkarasiak/m3s";
await m3s.ready();                                   // awaits WASM init (no-op on Node)

const cell = m3s.H3.fromPoint(-74.0060, 40.7128, 7); // (lon, lat, precision)
console.log(cell.id, cell.areaKm2);

const cells = m3s.Geohash.fromBbox([-74.02, 40.70, -73.93, 40.80], 6);
console.log(cells.length, cells.toIds());
```

`await m3s.ready()` is required on the web (it awaits WASM init) and harmless on
Node, so the same line works everywhere.

## Build from source

```bash
cd bindings/js
wasm-pack build --target nodejs --out-dir pkg      # Node build  (used by index.node.js)
wasm-pack build --target web    --out-dir pkg-web  # Web build   (used by index.web.js)
```

## API at a glance

- **Grids:** `A5 Geohash H3 MGRS S2 Quadkey Slippy CSquares GARS Maidenhead
  PlusCode EAQuad RHEALPix`
- **Grid methods:** `fromPoint(lon, lat, p?)` · `fromBbox([minLon,minLat,maxLon,maxLat], p?)`
  · `fromId(id)` · `fromIds([...])` · `fromGeometry(geom, p?)` ·
  `neighbors(cellOrId, depth=1, includeSelf=true)` · `children`/`parent`
  (hierarchical grids only) · `withPrecision(p)` · getters `name
  defaultPrecision precisionRange hierarchical`. A5 also: `cellAreaM2(p)`.
- **Cell:** `id precision ring ringOpen areaKm2 centroid bounds toGeoJSON()`
- **CellCollection:** iterable · `length at slice toIds ids toPolygons toGeoJSON
  filter map unique neighbors(depth) refine(p) coarsen(p) totalAreaKm2 bounds`
- **Top-level:** `ready() precisionBounds(name?) geodesicAreaKm2(ring) Cell
  CellCollection Grid`

## Coordinate order

The wrapper boundary is **GIS-native `(lon, lat)`**, matching the Python API,
Shapely and GeoJSON. Cell `ring`/`centroid`/`bounds` are `[lon, lat]` too.

## What's Python-only

The core supports point→cell and bbox→cells. These stay Python-only and are
**deliberately absent** here:

- true polygon fill (`fromGeometry` reduces a polygon to its bounding box)
- precision strategies (`find_precision`, `find_precision_for_area/use_case`)
- GeoPandas / pandas export (`to_gdf`, `to_dataframe`), `save`, `plot`/`explore`
- `dissolve`, cross-grid conversion (`to_h3`, `to_geohash`, …)
- the h3-py verb vocabulary, `GridBuilder`, `MultiGridComparator`, `PrecisionSelector`
