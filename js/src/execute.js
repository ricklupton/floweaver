/**
 * Execute a WeaverSpec against flow data to produce SankeyData.
 *
 * This is the JS equivalent of floweaver.compiler.execute.execute_weave().
 * It takes a compiled WeaverSpec (deserialized from JSON) and an array of
 * flow records, and produces the same SankeyData structure.
 */

import { evaluateTree } from "./tree.js";
import { applyColor } from "./color.js";

/**
 * Execute a WeaverSpec against flow data.
 *
 * @param {object} spec  - WeaverSpec as a plain JS object (from JSON)
 * @param {object[]} flows - Array of flow records, each {source, target, material, value, ...}
 * @returns {object} SankeyData-compatible result
 */
export function executeWeave(spec, flows) {
  const routingTree = spec.routing_tree;

  // 1. Route every flow row through the decision tree
  const edgeFlowMap = routeFlows(flows, routingTree);

  // 2. Build links, separating elsewhere links
  const links = [];
  const fromElsewhere = {}; // nodeId -> [link, ...]
  const toElsewhere = {}; // nodeId -> [link, ...]

  for (const [edgeIndexStr, flowIndices] of Object.entries(edgeFlowMap)) {
    const edgeIndex = Number(edgeIndexStr);
    const edge = spec.edges[edgeIndex];

    if (flowIndices.length === 0) continue;

    const matchingRows = flowIndices.map((i) => flows[i]);
    const data = aggregate(matchingRows, spec.measures);
    const linkWidth = data[spec.display.link_width] ?? 0.0;
    const color = applyColor(edge, data, spec.display);
    const title = edge.type; // matches Python _compute_title

    const link = {
      source: edge.source,
      target: edge.target,
      type: edge.type,
      time: edge.time,
      link_width: linkWidth,
      data: data,
      title: title,
      color: color,
      opacity: 1.0,
      original_flows: flowIndices,
    };

    if (edge.source == null) {
      if (!fromElsewhere[edge.target]) fromElsewhere[edge.target] = [];
      fromElsewhere[edge.target].push(link);
    } else if (edge.target == null) {
      if (!toElsewhere[edge.source]) toElsewhere[edge.source] = [];
      toElsewhere[edge.source].push(link);
    } else {
      links.push(link);
    }
  }

  // 3. Track used nodes
  const nodesInRegularEdges = new Set();
  for (const link of links) {
    nodesInRegularEdges.add(link.source);
    nodesInRegularEdges.add(link.target);
  }

  const used = new Set(nodesInRegularEdges);
  for (const k of Object.keys(fromElsewhere)) used.add(k);
  for (const k of Object.keys(toElsewhere)) used.add(k);

  // 4. Build nodes
  const nodes = [];
  for (const [nodeId, nodeSpec] of Object.entries(spec.nodes)) {
    if (used.has(nodeId)) {
      nodes.push({
        id: nodeId,
        title: nodeSpec.title,
        direction: nodeSpec.direction,
        hidden: nodeSpec.hidden,
        style: nodeSpec.style,
        from_elsewhere_links: fromElsewhere[nodeId] || [],
        to_elsewhere_links: toElsewhere[nodeId] || [],
      });
    }
  }

  // 5. Build groups
  const groups = buildGroups(spec.groups, spec.nodes, nodesInRegularEdges);

  // 6. Filter ordering
  const ordering = filterOrdering(spec.ordering, used);

  return {
    nodes: nodes,
    links: links,
    groups: groups,
    ordering: ordering,
  };
}

/**
 * Route all flow rows through the decision tree.
 *
 * @param {object[]} flows - Array of flow record objects
 * @param {object} tree - Routing tree from the spec
 * @returns {Object<number, number[]>} edge_index -> [row_indices]
 */
function routeFlows(flows, tree) {
  const edgeAccumulators = {};

  for (let i = 0; i < flows.length; i++) {
    const row = flows[i];
    const edgeIds = evaluateTree(tree, row);

    if (edgeIds) {
      for (const edgeId of edgeIds) {
        if (!edgeAccumulators[edgeId]) edgeAccumulators[edgeId] = [];
        edgeAccumulators[edgeId].push(i);
      }
    }
  }

  return edgeAccumulators;
}

/**
 * Aggregate flow data according to measure specifications.
 *
 * @param {object[]} rows - Matching flow records
 * @param {object[]} measures - [{column, aggregation}, ...]
 * @returns {object} {column: aggregated_value}
 */
function aggregate(rows, measures) {
  const result = {};

  for (const m of measures) {
    const col = m.column;
    const values = rows.map((r) => r[col]).filter((v) => v != null);

    if (values.length === 0) {
      result[col] = 0.0;
      continue;
    }

    if (m.aggregation === "sum") {
      result[col] = values.reduce((a, b) => a + b, 0);
    } else if (m.aggregation === "mean") {
      result[col] = values.reduce((a, b) => a + b, 0) / values.length;
    } else {
      throw new Error(`Unknown aggregation: ${m.aggregation}`);
    }
  }

  return result;
}

/**
 * Build groups in the format expected by SankeyData.
 */
function buildGroups(groupSpecs, nodeSpecs, usedNodes) {
  const groups = [];

  for (const g of groupSpecs) {
    const nodesInGroup = g.nodes.filter((n) => usedNodes.has(n));
    if (nodesInGroup.length === 0) continue;

    const groupType = nodeSpecs[nodesInGroup[0]].type;

    let include;
    if (nodesInGroup.length === 1) {
      const nodeTitle = nodeSpecs[nodesInGroup[0]].title;
      const groupTitle = g.title || g.id;
      include = nodeTitle !== groupTitle;
    } else {
      include = true;
    }

    if (include) {
      groups.push({
        id: g.id,
        title: g.title != null ? g.title : "",
        type: groupType,
        nodes: nodesInGroup,
      });
    }
  }

  return groups;
}

/**
 * Filter ordering to only include used nodes.
 */
function filterOrdering(ordering, usedNodes) {
  const filtered = [];

  for (const layer of ordering) {
    const filteredLayer = [];
    for (const band of layer) {
      const filteredBand = band.filter((n) => usedNodes.has(n));
      filteredLayer.push(filteredBand);
    }
    if (filteredLayer.some((band) => band.length > 0)) {
      filtered.push(filteredLayer);
    }
  }

  return filtered;
}
