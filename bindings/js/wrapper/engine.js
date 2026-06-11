// The single seam between the hand-written wrapper and the generated WASM core.
//
// Both entry points (index.node.js, index.web.js) call setCore() once the core
// is loaded; everything else reads it through core(). Keeping the reference in
// one module means the wrapper source never imports pkg/ or pkg-web/ directly,
// so a single source serves both Node and the browser.

let _core = null;

/** Wire the generated WASM module. Called once by the platform entry point. */
export function setCore(core) {
  _core = core;
}

/**
 * The generated core, or a clear error if `ready()` has not resolved yet.
 * Node resolves `ready()` immediately; on the web it awaits `init()`.
 */
export function core() {
  if (!_core) {
    throw new Error(
      "m3s: call `await ready()` before using grids (WASM not initialized)."
    );
  }
  return _core;
}
