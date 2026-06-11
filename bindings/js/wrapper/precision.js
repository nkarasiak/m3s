import { core } from "./engine.js";

// serde-wasm-bindgen serializes the Rust HashMap as a JS Map; normalize to a
// plain object once so callers never touch a Map. Values are [min, max, default].
let _bounds = null;

function allBounds() {
  if (!_bounds) {
    const m = core().all_precision_bounds();
    const entries = m instanceof Map ? [...m.entries()] : Object.entries(m);
    _bounds = Object.fromEntries(entries);
  }
  return _bounds;
}

/**
 * Precision bounds for every grid (single source of truth, from the core).
 *
 * @param {string} [name] canonical grid name, e.g. "h3"
 * @returns {object|number[]} all bounds `{name: [min,max,default]}`, or the
 *   `[min, max, default]` triple for a single grid.
 */
export function precisionBounds(name) {
  const b = allBounds();
  return name === undefined ? { ...b } : b[name];
}
