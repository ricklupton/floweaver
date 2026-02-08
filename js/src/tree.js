/**
 * Decision tree evaluation.
 *
 * Trees are deserialized from JSON produced by the Python compiler.
 * Each node is either a LeafNode (with a `value`) or a BranchNode
 * (with `attr`, `branches`, and `default`).
 */

/**
 * Evaluate a decision tree node against a data row.
 *
 * @param {object} node - Tree node (LeafNode or BranchNode from JSON)
 * @param {object} row  - Data row as {column: value}
 * @returns {*} The leaf value reached by traversal
 */
export function evaluateTree(node, row) {
  // Leaf node
  if ("value" in node) {
    return node.value;
  }

  // Branch node
  const val = row[node.attr];
  if (val != null && node.branches[val] !== undefined) {
    return evaluateTree(node.branches[val], row);
  }
  return evaluateTree(node.default, row);
}
