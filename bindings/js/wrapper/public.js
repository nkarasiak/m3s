// The platform-agnostic public surface, re-exported by both entry points.
// The two index.*.js files add the platform-specific `ready()` and wire the core.

import { core } from "./engine.js";

export { Cell } from "./cell.js";
export { CellCollection } from "./cell-collection.js";
export { Grid } from "./grid.js";
export { precisionBounds } from "./precision.js";
export {
  A5,
  Geohash,
  H3,
  MGRS,
  S2,
  Quadkey,
  Slippy,
  CSquares,
  GARS,
  Maidenhead,
  PlusCode,
  EAQuad,
  RHEALPix,
  GRIDS,
} from "./grids.js";

/** Geodesic area of a closed `[[lon,lat], ...]` ring, in km² (raw core passthrough). */
export function geodesicAreaKm2(ring) {
  return core().geodesic_area_km2(ring);
}
