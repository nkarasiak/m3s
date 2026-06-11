import { core } from "./engine.js";

/**
 * Unpack a core columnar bulk result `{ids, coords, offsets, precisions}`
 * (one string + three typed arrays per call — no per-cell serde) into raw
 * `{id, ring, precision}` objects, the shape {@link Cell} wraps.
 */
export function unpackCells(packed) {
  const { ids, coords, offsets, precisions } = packed;
  if (!ids) return [];
  const idList = ids.split("\n");
  const out = new Array(idList.length);
  for (let i = 0; i < idList.length; i++) {
    const ring = [];
    for (let v = offsets[i]; v < offsets[i + 1]; v++) {
      ring.push([coords[2 * v], coords[2 * v + 1]]);
    }
    out[i] = { id: idList[i], ring, precision: precisions[i] };
  }
  return out;
}

/**
 * A single grid cell, wrapping the core `{ id, ring, precision }` with computed
 * getters. Mirrors the Python `GridCell`: GIS-native `[lon, lat]` order, area
 * delegated to the shared core (so JS and Python report identical km²).
 */
export class Cell {
  constructor(raw, gridName) {
    this._raw = raw;
    this.gridName = gridName;
    this._area = null;
  }

  get id() {
    return this._raw.id;
  }

  get precision() {
    return this._raw.precision;
  }

  /** Closed ring `[[lon, lat], ...]` exactly as the core returns it. */
  get ring() {
    return this._raw.ring;
  }

  /** Open ring (closing vertex dropped) — convenient for deck.gl / centroids. */
  get ringOpen() {
    const r = this._raw.ring;
    const n = r.length;
    if (n > 1 && r[0][0] === r[n - 1][0] && r[0][1] === r[n - 1][1]) {
      return r.slice(0, -1);
    }
    return r.slice();
  }

  /** Geodesic area in km², delegated to the shared core (parity with Python). */
  get areaKm2() {
    if (this._area === null) {
      this._area = core().geodesic_area_km2(this._raw.ring);
    }
    return this._area;
  }

  /** GIS-native `[lon, lat]` centroid, matching Python `GridCell.centroid`. */
  get centroid() {
    const r = this.ringOpen;
    let x = 0;
    let y = 0;
    for (const [lon, lat] of r) {
      x += lon;
      y += lat;
    }
    return [x / r.length, y / r.length];
  }

  /** `[minLon, minLat, maxLon, maxLat]`, matching Python `.bounds` order. */
  get bounds() {
    let minLon = Infinity;
    let minLat = Infinity;
    let maxLon = -Infinity;
    let maxLat = -Infinity;
    for (const [lon, lat] of this.ringOpen) {
      if (lon < minLon) minLon = lon;
      if (lat < minLat) minLat = lat;
      if (lon > maxLon) maxLon = lon;
      if (lat > maxLat) maxLat = lat;
    }
    return [minLon, minLat, maxLon, maxLat];
  }

  /** GeoJSON Polygon Feature (closed ring, lon/lat). */
  toGeoJSON() {
    return {
      type: "Feature",
      properties: { id: this.id, precision: this.precision, grid: this.gridName },
      geometry: { type: "Polygon", coordinates: [this._raw.ring] },
    };
  }

  toString() {
    return `Cell(${this.gridName} ${this.id} p${this.precision})`;
  }
}
