// Web entry point. The generated web build (../pkg-web) is an ES module that
// must be initialized with `await init(...)` before any function runs, so
// `ready()` awaits that init. It is idempotent: concurrent callers share one
// init promise.

import init, * as wasmCore from "../pkg-web/m3s_core_js.js";
import { setCore } from "./engine.js";

let _ready;

/**
 * Initialize the WASM core. Call once (and `await` it) before using any grid.
 *
 * @param {string|URL|Request|Response|BufferSource} [wasmUrl] optional override
 *   for the `.wasm` location; defaults to the build's co-located binary.
 */
export function ready(wasmUrl) {
  return (_ready ??= init(wasmUrl).then(() => setCore(wasmCore)));
}

export * from "./public.js";
