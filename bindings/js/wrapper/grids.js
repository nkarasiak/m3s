import { Grid, A5Grid } from "./grid.js";

// [canonical name, core prefix, hierarchical]. Names match the precision-bounds
// registry keys; the singleton export names mirror the Python facade (m3s.H3).
export const A5 = new A5Grid("a5", "a5", true);
export const Geohash = new Grid("geohash", "gh", true);
export const H3 = new Grid("h3", "h3", true);
export const MGRS = new Grid("mgrs", "mgrs", false);
export const S2 = new Grid("s2", "s2", true);
export const Quadkey = new Grid("quadkey", "qk", true);
export const Slippy = new Grid("slippy", "sl", true);
export const CSquares = new Grid("csquares", "cs", true);
export const GARS = new Grid("gars", "gars", false);
export const Maidenhead = new Grid("maidenhead", "mh", false);
export const PlusCode = new Grid("pluscode", "pc", true);
export const EAQuad = new Grid("eaquad", "eaq", true);
export const RHEALPix = new Grid("rhealpix", "rhp", true);

/** All grid singletons keyed by their public name. */
export const GRIDS = {
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
};
