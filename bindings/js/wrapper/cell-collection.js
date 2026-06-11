/**
 * An iterable collection of {@link Cell}s, mirroring the subset of the Python
 * `GridCellCollection` that does not depend on GeoPandas/Shapely. Cross-grid
 * conversion, `to_gdf`, `dissolve`, `save`, `plot`/`explore` are Python-only.
 */
export class CellCollection {
  constructor(cells, grid) {
    this.cells = cells;
    this._grid = grid;
  }

  [Symbol.iterator]() {
    return this.cells[Symbol.iterator]();
  }

  get length() {
    return this.cells.length;
  }

  at(i) {
    return this.cells.at(i);
  }

  slice(a, b) {
    return new CellCollection(this.cells.slice(a, b), this._grid);
  }

  toIds() {
    return this.cells.map((c) => c.id);
  }

  get ids() {
    return this.toIds();
  }

  /** Array of closed rings `[[ [lon,lat], ... ], ...]`. */
  toPolygons() {
    return this.cells.map((c) => c.ring);
  }

  toGeoJSON() {
    return {
      type: "FeatureCollection",
      features: this.cells.map((c) => c.toGeoJSON()),
    };
  }

  filter(pred) {
    return new CellCollection(this.cells.filter(pred), this._grid);
  }

  map(fn) {
    return this.cells.map(fn);
  }

  /** Drop duplicate cells by id. */
  unique() {
    const seen = new Set();
    const out = [];
    for (const c of this.cells) {
      if (!seen.has(c.id)) {
        seen.add(c.id);
        out.push(c);
      }
    }
    return new CellCollection(out, this._grid);
  }

  /** Union of every cell's neighbours (origin cells included). */
  neighbors(depth = 1) {
    const seen = new Map();
    for (const c of this.cells) {
      for (const n of this._grid.neighbors(c, depth, true)) {
        seen.set(n.id, n);
      }
    }
    return new CellCollection([...seen.values()], this._grid);
  }

  /** Refine every cell to a finer precision (hierarchical grids only). */
  refine(precision) {
    const out = new Map();
    for (const c of this.cells) {
      for (const ch of this._grid._refineCell(c, precision)) {
        out.set(ch.id, ch);
      }
    }
    return new CellCollection([...out.values()], this._grid);
  }

  /** Coarsen every cell to a coarser precision (hierarchical grids only). */
  coarsen(precision) {
    const out = new Map();
    for (const c of this.cells) {
      const p = this._grid._coarsenCell(c, precision);
      out.set(p.id, p);
    }
    return new CellCollection([...out.values()], this._grid);
  }

  get totalAreaKm2() {
    return this.cells.reduce((s, c) => s + c.areaKm2, 0);
  }

  get bounds() {
    let minLon = Infinity;
    let minLat = Infinity;
    let maxLon = -Infinity;
    let maxLat = -Infinity;
    for (const c of this.cells) {
      const [a, b, cc, d] = c.bounds;
      if (a < minLon) minLon = a;
      if (b < minLat) minLat = b;
      if (cc > maxLon) maxLon = cc;
      if (d > maxLat) maxLat = d;
    }
    return [minLon, minLat, maxLon, maxLat];
  }
}
