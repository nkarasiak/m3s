// Node entry point. The generated nodejs build (../pkg) is CommonJS and loads
// synchronously, so `ready()` resolves immediately — the same `await ready()`
// line works on both Node and the web.

import { createRequire } from "node:module";
import { setCore } from "./engine.js";

const require = createRequire(import.meta.url);
setCore(require("../pkg/m3s_core_js.js"));

/** Resolves immediately on Node (the core is already loaded). */
export function ready() {
  return Promise.resolve();
}

export * from "./public.js";
