import { core } from "./engine.js";
import { Cell, unpackCells } from "./cell.js";
import { CellCollection } from "./cell-collection.js";
import { precisionBounds } from "./precision.js";

// fromGeometry reduces polygons to their bounding box (the only area query the
// core supports). Warn once so the limitation is visible without spamming logs.
let _polyWarned = false;
function warnPolygon() {
  if (!_polyWarned) {
    _polyWarned = true;
    console.warn(
      "m3s(JS): polygon input is reduced to its bounding box. True polygon " +
        "fill, find_precision, and GeoPandas export are Python-only."
    );
  }
}

function ringBounds(ring) {
  let minLon = Infinity;
  let minLat = Infinity;
  let maxLon = -Infinity;
  let maxLat = -Infinity;
  for (const [lon, lat] of ring) {
    if (lon < minLon) minLon = lon;
    if (lat < minLat) minLat = lat;
    if (lon > maxLon) maxLon = lon;
    if (lat > maxLat) maxLat = lat;
  }
  return [minLon, minLat, maxLon, maxLat];
}

function geojsonBounds(geom) {
  const coords = [];
  const walk = (a) => (typeof a[0] === "number" ? coords.push(a) : a.forEach(walk));
  walk(geom.coordinates);
  return ringBounds(coords);
}

/**
 * One spatial grid system. Wraps the core's `<prefix>_*` functions into an
 * ergonomic, camelCase API mirroring the Python `GridWrapper` (m3s.H3, etc.).
 *
 * The wrapper boundary is GIS-native (lon, lat); the core takes (lat, lon), so
 * every call swaps the pair exactly once here.
 */
export class Grid {
  constructor(name, prefix, hierarchical, precision = null) {
    this.name = name;
    this._prefix = prefix;
    this.hierarchical = hierarchical;
    this._precision = precision;
  }

  _fn(op) {
    const fn = core()[`${this._prefix}_${op}`];
    if (typeof fn !== "function") {
      throw new Error(`m3s: core has no ${this._prefix}_${op} (grid ${this.name})`);
    }
    return fn;
  }

  _wrapErr(op, arg, e) {
    const cls = this.name[0].toUpperCase() + this.name.slice(1);
    return new Error(`${cls}.${op}(${arg}): ${e && e.message ? e.message : e}`);
  }

  _requireHierarchical(op) {
    if (!this.hierarchical) {
      const cls = this.name[0].toUpperCase() + this.name.slice(1);
      throw new Error(`${cls} is not hierarchical; ${op}() is unavailable`);
    }
  }

  get precisionRange() {
    const b = precisionBounds(this.name);
    return [b[0], b[1]];
  }

  get defaultPrecision() {
    return this._precision != null ? this._precision : precisionBounds(this.name)[2];
  }

  withPrecision(p) {
    return new this.constructor(this.name, this._prefix, this.hierarchical, p);
  }

  _checkPrecision(p) {
    const [lo, hi] = this.precisionRange;
    if (p < lo || p > hi) {
      throw new Error(`${this.name}: precision ${p} out of range [${lo}, ${hi}]`);
    }
  }

  fromPoint(lon, lat, precision = this.defaultPrecision) {
    this._checkPrecision(precision);
    try {
      return new Cell(this._fn("cell_from_point")(lat, lon, precision), this.name);
    } catch (e) {
      throw this._wrapErr("fromPoint", `${lon}, ${lat}, ${precision}`, e);
    }
  }

  fromBbox(bbox, precision = this.defaultPrecision) {
    this._checkPrecision(precision);
    const [minLon, minLat, maxLon, maxLat] = bbox;
    try {
      const raw = unpackCells(
        this._fn("cells_in_bbox")(minLat, minLon, maxLat, maxLon, precision)
      );
      return new CellCollection(
        raw.map((r) => new Cell(r, this.name)),
        this
      );
    } catch (e) {
      throw this._wrapErr("fromBbox", JSON.stringify(bbox), e);
    }
  }

  fromId(id) {
    try {
      return new Cell(this._fn("cell_from_id")(id), this.name);
    } catch (e) {
      throw this._wrapErr("fromId", JSON.stringify(id), e);
    }
  }

  fromIds(ids) {
    return new CellCollection(
      ids.map((id) => this.fromId(id)),
      this
    );
  }

  /**
   * Universal entry. Accepts a `[lon, lat]` point, a `[minLon, minLat, maxLon,
   * maxLat]` bbox, a ring `[[lon,lat], ...]`, or GeoJSON Point/Polygon/Feature.
   * Polygons are reduced to their bounding box (see {@link warnPolygon}).
   */
  fromGeometry(geometry, precision = this.defaultPrecision) {
    if (geometry && typeof geometry === "object" && !Array.isArray(geometry)) {
      const geom = geometry.type === "Feature" ? geometry.geometry : geometry;
      if (geom && geom.type === "Point") {
        const [lon, lat] = geom.coordinates;
        return this.fromPoint(lon, lat, precision);
      }
      if (geom && geom.coordinates) {
        warnPolygon();
        return this.fromBbox(geojsonBounds(geom), precision);
      }
      throw new Error("m3s: unsupported GeoJSON geometry for fromGeometry");
    }
    if (Array.isArray(geometry)) {
      if (geometry.length === 2 && typeof geometry[0] === "number") {
        return this.fromPoint(geometry[0], geometry[1], precision);
      }
      if (geometry.length === 4 && typeof geometry[0] === "number") {
        return this.fromBbox(geometry, precision);
      }
      if (Array.isArray(geometry[0])) {
        warnPolygon();
        return this.fromBbox(ringBounds(geometry), precision);
      }
    }
    throw new Error(
      "m3s: fromGeometry accepts [lon,lat], [minLon,minLat,maxLon,maxLat], a " +
        "ring, or GeoJSON Point/Polygon"
    );
  }

  /** BFS neighbours up to `depth`, like Python `GridWrapper.neighbors`. */
  neighbors(cellOrId, depth = 1, includeSelf = true) {
    const startId = typeof cellOrId === "string" ? cellOrId : cellOrId.id;
    const startCell =
      typeof cellOrId === "string" ? this.fromId(cellOrId) : cellOrId;
    const all = new Map([[startId, startCell]]);
    let ring = new Map([[startId, startCell]]);
    for (let d = 0; d < depth; d++) {
      const next = new Map();
      for (const id of ring.keys()) {
        let raw;
        try {
          raw = unpackCells(this._fn("neighbors")(id));
        } catch (e) {
          throw this._wrapErr("neighbors", JSON.stringify(id), e);
        }
        for (const r of raw) {
          if (!all.has(r.id)) {
            const cell = new Cell(r, this.name);
            all.set(r.id, cell);
            next.set(r.id, cell);
          }
        }
      }
      ring = next;
    }
    if (!includeSelf) all.delete(startId);
    return new CellCollection([...all.values()], this);
  }

  children(cellOrId) {
    this._requireHierarchical("children");
    const id = typeof cellOrId === "string" ? cellOrId : cellOrId.id;
    try {
      const raw = unpackCells(this._fn("children")(id));
      return new CellCollection(
        raw.map((r) => new Cell(r, this.name)),
        this
      );
    } catch (e) {
      throw this._wrapErr("children", JSON.stringify(id), e);
    }
  }

  parent(cellOrId) {
    this._requireHierarchical("parent");
    const id = typeof cellOrId === "string" ? cellOrId : cellOrId.id;
    try {
      return new Cell(this._fn("parent")(id), this.name);
    } catch (e) {
      throw this._wrapErr("parent", JSON.stringify(id), e);
    }
  }

  // Used by CellCollection.refine/coarsen.
  _refineCell(cell, precision) {
    this._requireHierarchical("refine");
    if (precision <= cell.precision) return [cell];
    let current = [cell];
    for (let p = cell.precision; p < precision; p++) {
      const next = [];
      for (const c of current) {
        for (const r of unpackCells(this._fn("children")(c.id))) {
          next.push(new Cell(r, this.name));
        }
      }
      current = next;
    }
    return current;
  }

  _coarsenCell(cell, precision) {
    this._requireHierarchical("coarsen");
    if (precision >= cell.precision) return cell;
    let current = cell;
    for (let p = cell.precision; p > precision; p--) {
      current = new Cell(this._fn("parent")(current.id), this.name);
    }
    return current;
  }
}

/** A5 is equal-area, so it exposes the core's analytic cell area. */
export class A5Grid extends Grid {
  cellAreaM2(precision = this.defaultPrecision) {
    this._checkPrecision(precision);
    return core().a5_cell_area_m2(precision);
  }
}
