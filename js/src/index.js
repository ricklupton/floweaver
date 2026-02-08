/**
 * floweaver-executor
 *
 * Execute a compiled WeaverSpec against flow data to produce Sankey diagram
 * data. This is the JS counterpart of floweaver.compiler.execute — it takes
 * a spec that has been compiled in Python and serialized to JSON, plus a
 * dataset (array of flow records), and produces a SankeyData result.
 *
 * Usage (ESM):
 *   import { executeWeave } from "floweaver-executor";
 *   const result = executeWeave(spec, flows);
 *
 * Usage (script tag):
 *   <script src="floweaver-executor.umd.js"></script>
 *   const result = floweaver.executeWeave(spec, flows);
 */

export { executeWeave } from "./execute.js";
export { evaluateTree } from "./tree.js";
export { applyColor, interpolateColor } from "./color.js";
