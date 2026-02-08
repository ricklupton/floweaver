#!/usr/bin/env node
/**
 * CLI helper: reads a JSON object from stdin with {spec, flows} and writes
 * the executeWeave result to stdout as JSON.
 *
 * Usage:
 *   echo '{"spec": {...}, "flows": [...]}' | node run_spec.js
 */

import { executeWeave } from "./src/index.js";
import { readFileSync } from "node:fs";

const input = JSON.parse(readFileSync("/dev/stdin", "utf-8"));
const result = executeWeave(input.spec, input.flows);
process.stdout.write(JSON.stringify(result));
