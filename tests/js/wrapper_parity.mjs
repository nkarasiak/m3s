// Wrapper-level parity gate: proves the ergonomic JS wrapper
// (bindings/js/wrapper) does not distort the core it wraps. Layered on top of
// parity.cjs (which proves core == Python): here we pin the wrapper's
// coordinate-order swap, capability contract (non-hierarchical grids throw),
// area delegation, and public surface.
//
//   node tests/js/wrapper_parity.mjs
//
// Reuses the golden vectors in tests/golden/*.json.

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import * as m3s from "../../bindings/js/wrapper/index.node.js";

await m3s.ready();

const HERE = path.dirname(fileURLToPath(import.meta.url));
const GOLDEN = path.join(HERE, "..", "golden");
const load = (g) => JSON.parse(fs.readFileSync(path.join(GOLDEN, `${g}.json`), "utf8"));
const loadBbox = (g) =>
  JSON.parse(fs.readFileSync(path.join(GOLDEN, `${g}_bbox.json`), "utf8"));

// golden name -> wrapper singleton
const GRID = {
  geohash: m3s.Geohash,
  h3: m3s.H3,
  quadkey: m3s.Quadkey,
  slippy: m3s.Slippy,
  gars: m3s.GARS,
  maidenhead: m3s.Maidenhead,
  csquares: m3s.CSquares,
  pluscode: m3s.PlusCode,
  eaquad: m3s.EAQuad,
  mgrs: m3s.MGRS,
  a5: m3s.A5,
  s2: m3s.S2,
};
const GRID_NAMES = Object.keys(GRID);

// Same order-independent ring comparison as parity.cjs.
const DEFAULT_RING_TOL = 1e-9;
const RING_ABS_TOL = { mgrs: 1e-4 };
const ringsClose = (a, b, tol) => {
  if (a.length !== b.length) return false;
  const key = (p) => `${p[0].toFixed(3)},${p[1].toFixed(3)}`;
  const sa = [...a].sort((p, q) => key(p).localeCompare(key(q)));
  const sb = [...b].sort((p, q) => key(p).localeCompare(key(q)));
  return sa.every(
    (p, i) => Math.abs(p[0] - sb[i][0]) <= tol && Math.abs(p[1] - sb[i][1]) <= tol
  );
};
const ids = (cells) => cells.map((c) => c.id).sort();
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);

let pass = 0;
const fails = [];
const check = (label, fn) => {
  try {
    fn();
    pass++;
  } catch (e) {
    fails.push(`${label}: ${e && e.message ? e.message : e}`);
  }
};

// 1. Per-grid cell parity *through the wrapper*. The golden stores (lat, lon);
//    the wrapper takes (lon, lat) — calling fromPoint(rec.lon, rec.lat) is the
//    arg-swap this test exists to pin.
for (const g of GRID_NAMES) {
  const grid = GRID[g];
  for (const rec of load(g)) {
    check(`${g}-${rec.id}-point`, () => {
      const c = grid.fromPoint(rec.lon, rec.lat, rec.precision);
      if (c.id !== rec.id) throw new Error(`point id ${c.id} != ${rec.id}`);
      if (c.precision !== rec.cell_precision) throw new Error("point precision");
    });
    check(`${g}-${rec.id}-fromId`, () => {
      const r = grid.fromId(rec.id);
      if (r.id !== rec.id) throw new Error("fromId id");
      const tol = RING_ABS_TOL[g] ?? DEFAULT_RING_TOL;
      if (!ringsClose(r.ring, rec.ring, tol)) throw new Error("ring mismatch");
    });
    // Wrapper neighbors mirror Python: depth-1 includeSelf=true == core ring ∪
    // {self}; includeSelf=false drops the origin (even on the slippy world tile,
    // whose core ring wraps to itself).
    check(`${g}-${rec.id}-neighbors`, () => {
      const withSelf = ids(grid.neighbors(rec.id, 1, true).cells);
      const expected = [...new Set([...rec.neighbors, rec.id])].sort();
      if (!eq(withSelf, expected)) throw new Error("neighbors+self");
      const got = ids(grid.neighbors(rec.id, 1, false).cells);
      if (got.includes(rec.id)) throw new Error("includeSelf=false kept origin");
      if (!eq(got, expected.filter((x) => x !== rec.id))) throw new Error("neighbors");
    });
    if (rec.children !== undefined) {
      check(`${g}-${rec.id}-children`, () => {
        if (!eq(ids(grid.children(rec.id).cells), [...rec.children].sort()))
          throw new Error("children");
      });
    }
    if (rec.parent !== undefined) {
      check(`${g}-${rec.id}-parent`, () => {
        if (grid.parent(rec.id).id !== rec.parent) throw new Error("parent");
      });
    }
    // area is delegated to the core, never recomputed
    check(`${g}-${rec.id}-area`, () => {
      const c = grid.fromId(rec.id);
      if (c.areaKm2 !== m3s.geodesicAreaKm2(c.ring))
        throw new Error("areaKm2 not delegated to core");
    });
  }
}

// 2. Non-hierarchical grids must throw on children()/parent().
for (const g of ["gars", "maidenhead", "mgrs"]) {
  const grid = GRID[g];
  check(`${g}-children-throws`, () => {
    let threw = false;
    try {
      grid.children("x");
    } catch {
      threw = true;
    }
    if (!threw) throw new Error("children() did not throw");
  });
  check(`${g}-parent-throws`, () => {
    let threw = false;
    try {
      grid.parent("x");
    } catch {
      threw = true;
    }
    if (!threw) throw new Error("parent() did not throw");
  });
}

// 3. Bbox parity through fromBbox. Golden bbox is [minLat,minLon,maxLat,maxLon];
//    the wrapper takes GIS order [minLon,minLat,maxLon,maxLat] — reorder here.
for (const g of GRID_NAMES) {
  const grid = GRID[g];
  for (const rec of loadBbox(g)) {
    check(`${g}-bbox-p${rec.precision}`, () => {
      const [minLat, minLon, maxLat, maxLon] = rec.bbox;
      const got = ids(grid.fromBbox([minLon, minLat, maxLon, maxLat], rec.precision).cells);
      if (!eq(got, [...rec.cells].sort())) throw new Error("bbox cells");
    });
  }
}

// 4. precisionBounds() reproduces the frozen golden.
check("precision_bounds", () => {
  const golden = JSON.parse(
    fs.readFileSync(path.join(GOLDEN, "precision_bounds.json"), "utf8")
  );
  const toSorted = (o) =>
    Object.fromEntries(Object.entries(o).sort(([a], [b]) => a.localeCompare(b)));
  if (!eq(toSorted(m3s.precisionBounds()), toSorted(golden)))
    throw new Error("precision_bounds mismatch");
});

// 5. Public surface contract: expose exactly the frozen top-level set; every
//    grid/cell/collection public symbol present; every Python-only name absent.
check("surface", () => {
  const surface = JSON.parse(
    fs.readFileSync(path.join(GOLDEN, "js_wrapper_surface.json"), "utf8")
  );
  const topLevel = Object.keys(m3s).sort();
  if (!eq(topLevel, [...surface.topLevel].sort()))
    throw new Error(
      `top-level mismatch; extra: ${topLevel.filter((k) => !surface.topLevel.includes(k))} ` +
        `missing: ${surface.topLevel.filter((k) => !topLevel.includes(k))}`
    );

  const sampleCell = m3s.H3.fromPoint(-74.006, 40.7128, 7);
  const sampleColl = m3s.H3.neighbors(sampleCell, 1);

  for (const k of surface.gridPublic) {
    if (!(k in m3s.H3)) throw new Error(`grid missing ${k}`);
  }
  for (const k of surface.cellPublic) {
    if (!(k in sampleCell)) throw new Error(`cell missing ${k}`);
  }
  for (const k of surface.collectionPublic) {
    if (!(k in sampleColl)) throw new Error(`collection missing ${k}`);
  }
  // Negative: Python-only features stay out of every public object.
  const targets = [m3s, m3s.H3, sampleCell, sampleColl];
  for (const k of surface.absent) {
    for (const t of targets) {
      if (k in t) throw new Error(`Python-only "${k}" leaked into the JS surface`);
    }
  }
});

console.log(`PASS ${pass}  FAIL ${fails.length}`);
if (fails.length) {
  for (const f of fails) console.error("  " + f);
  process.exit(1);
}
