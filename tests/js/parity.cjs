// ADR 0001 P0 parity gate, JS half: the WASM build must reproduce the SAME
// golden vectors as the Rust-backed Python (tests/golden/*.json), proving
// JS == Python because both consume one Rust core.
//
//   node tests/js/parity.cjs
//
// Mirrors tests/test_core_parity.py: ids/precision/neighbour/child/parent sets
// exact; ring vertices order-independent within an absolute degree tolerance
// (RING_ABS_TOL). Area is excluded (ADR §3 geodesic re-baseline).

const fs = require("fs");
const path = require("path");
const wasm = require("../../bindings/js/pkg");

const GOLDEN = path.join(__dirname, "..", "golden");

const FNS = {
  geohash: {
    point: wasm.gh_cell_from_point,
    fromId: wasm.gh_cell_from_id,
    neighbors: wasm.gh_neighbors,
    children: wasm.gh_children,
    parent: wasm.gh_parent,
  },
  h3: {
    point: wasm.h3_cell_from_point,
    fromId: wasm.h3_cell_from_id,
    neighbors: wasm.h3_neighbors,
    children: wasm.h3_children,
    parent: wasm.h3_parent,
  },
  quadkey: {
    point: wasm.qk_cell_from_point,
    fromId: wasm.qk_cell_from_id,
    neighbors: wasm.qk_neighbors,
    children: wasm.qk_children,
    parent: wasm.qk_parent,
  },
  slippy: {
    point: wasm.sl_cell_from_point,
    fromId: wasm.sl_cell_from_id,
    neighbors: wasm.sl_neighbors,
    children: wasm.sl_children,
    parent: wasm.sl_parent,
  },
  gars: {
    point: wasm.gars_cell_from_point,
    fromId: wasm.gars_cell_from_id,
    neighbors: wasm.gars_neighbors,
  },
  maidenhead: {
    point: wasm.mh_cell_from_point,
    fromId: wasm.mh_cell_from_id,
    neighbors: wasm.mh_neighbors,
  },
  csquares: {
    point: wasm.cs_cell_from_point,
    fromId: wasm.cs_cell_from_id,
    neighbors: wasm.cs_neighbors,
    children: wasm.cs_children,
    parent: wasm.cs_parent,
  },
  pluscode: {
    point: wasm.pc_cell_from_point,
    fromId: wasm.pc_cell_from_id,
    neighbors: wasm.pc_neighbors,
    children: wasm.pc_children,
    parent: wasm.pc_parent,
  },
  eaquad: {
    point: wasm.eaq_cell_from_point,
    fromId: wasm.eaq_cell_from_id,
    neighbors: wasm.eaq_neighbors,
    children: wasm.eaq_children,
    parent: wasm.eaq_parent,
  },
  mgrs: {
    point: wasm.mgrs_cell_from_point,
    fromId: wasm.mgrs_cell_from_id,
    neighbors: wasm.mgrs_neighbors,
  },
  a5: {
    point: wasm.a5_cell_from_point,
    fromId: wasm.a5_cell_from_id,
    neighbors: wasm.a5_neighbors,
    children: wasm.a5_children,
    parent: wasm.a5_parent,
  },
};

// Ring vertices compared with an absolute degree tolerance. Default 1e-9 (~0.1
// mm) absorbs last-ULP native-vs-wasm libm noise. MGRS is looser (~metre) for
// its UTM-round-trip ring. Ids/neighbours always match exactly.
const DEFAULT_RING_TOL = 1e-9;
const RING_ABS_TOL = { mgrs: 1e-4 };

const load = (g) =>
  JSON.parse(fs.readFileSync(path.join(GOLDEN, `${g}.json`), "utf8")).map(
    (rec) => [g, rec]
  );

// Order-independent vertex match within an absolute degree tolerance.
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

const ALL = [
  ...load("geohash"),
  ...load("h3"),
  ...load("quadkey"),
  ...load("slippy"),
  ...load("gars"),
  ...load("maidenhead"),
  ...load("csquares"),
  ...load("pluscode"),
  ...load("eaquad"),
  ...load("mgrs"),
  ...load("a5"),
];

for (const [grid, rec] of ALL) {
  const fns = FNS[grid];
  const label = `${grid}-${rec.id}`;
  try {
    const c = fns.point(rec.lat, rec.lon, rec.precision);
    if (c.id !== rec.id) throw `point id ${c.id} != ${rec.id}`;
    if (c.precision !== rec.cell_precision) throw `point precision`;

    const r = fns.fromId(rec.id);
    if (r.id !== rec.id) throw `fromId id`;
    if (r.precision !== rec.cell_precision) throw `fromId precision`;
    if (!ringsClose(r.ring, rec.ring, RING_ABS_TOL[grid] ?? DEFAULT_RING_TOL))
      throw `ring mismatch`;

    if (!eq(ids(fns.neighbors(rec.id)), rec.neighbors)) throw `neighbors`;
    if (rec.children !== undefined && !eq(ids(fns.children(rec.id)), rec.children))
      throw `children`;
    if (rec.parent !== undefined && fns.parent(rec.id).id !== rec.parent)
      throw `parent`;

    pass++;
  } catch (e) {
    fails.push(`${label}: ${e}`);
  }
}

console.log(`PASS ${pass}  FAIL ${fails.length}`);
if (fails.length) {
  for (const f of fails) console.error("  " + f);
  process.exit(1);
}
