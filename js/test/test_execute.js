import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { executeWeave, evaluateTree, routeRow } from "../src/index.js";

describe("evaluateTree", () => {
  it("handles a leaf node", () => {
    const tree = { value: [0, 1] };
    assert.deepStrictEqual(evaluateTree(tree, { source: "a" }), [0, 1]);
  });

  it("branches on attribute value", () => {
    const tree = {
      attr: "source",
      branches: {
        a: { value: [0] },
        b: { value: [1] },
      },
      default: { value: [] },
    };
    assert.deepStrictEqual(evaluateTree(tree, { source: "a" }), [0]);
    assert.deepStrictEqual(evaluateTree(tree, { source: "b" }), [1]);
    assert.deepStrictEqual(evaluateTree(tree, { source: "c" }), []);
  });

  it("handles nested branches", () => {
    const tree = {
      attr: "source",
      branches: {
        a: {
          attr: "target",
          branches: {
            x: { value: [0] },
          },
          default: { value: [1] },
        },
      },
      default: { value: [2] },
    };
    assert.deepStrictEqual(
      evaluateTree(tree, { source: "a", target: "x" }),
      [0]
    );
    assert.deepStrictEqual(
      evaluateTree(tree, { source: "a", target: "y" }),
      [1]
    );
    assert.deepStrictEqual(
      evaluateTree(tree, { source: "b", target: "x" }),
      [2]
    );
  });
});

describe("executeWeave", () => {
  it("produces correct output for a simple two-node spec", () => {
    const spec = {
      version: "2.0",
      nodes: {
        a: {
          title: "A",
          type: "process",
          group: "ga",
          style: "default",
          direction: "R",
          hidden: false,
        },
        b: {
          title: "B",
          type: "process",
          group: "gb",
          style: "default",
          direction: "R",
          hidden: false,
        },
      },
      groups: [
        { id: "ga", title: "Group A", nodes: ["a"] },
        { id: "gb", title: "Group B", nodes: ["b"] },
      ],
      bundles: [{ id: "b0", source: "ga", target: "gb" }],
      ordering: [[["a"]], [["b"]]],
      edges: [
        {
          source: "a",
          target: "b",
          type: "*",
          time: "*",
          bundle_ids: ["b0"],
        },
      ],
      measures: [{ column: "value", aggregation: "sum" }],
      display: {
        link_width: "value",
        link_color: {
          type: "categorical",
          attr: "type",
          lookup: { "*": "#aabbcc" },
          default: "#cccccc",
        },
      },
      routing_tree: {
        attr: "source",
        branches: {
          a: {
            attr: "target",
            branches: {
              b: { value: [0] },
            },
            default: { value: [] },
          },
        },
        default: { value: [] },
      },
    };

    const flows = [
      { source: "a", target: "b", value: 5 },
      { source: "a", target: "b", value: 3 },
      { source: "x", target: "y", value: 10 },
    ];

    const result = executeWeave(spec, flows);

    assert.equal(result.links.length, 1);
    assert.equal(result.links[0].source, "a");
    assert.equal(result.links[0].target, "b");
    assert.equal(result.links[0].link_width, 8);
    assert.equal(result.links[0].color, "#aabbcc");
    assert.deepStrictEqual(result.links[0].data, { value: 8 });
    assert.deepStrictEqual(result.links[0].original_flows, [0, 1]);

    assert.equal(result.nodes.length, 2);
    const nodeIds = result.nodes.map((n) => n.id).sort();
    assert.deepStrictEqual(nodeIds, ["a", "b"]);
  });

  it("handles elsewhere links", () => {
    const spec = {
      version: "2.0",
      nodes: {
        a: {
          title: "A",
          type: "process",
          group: "ga",
          style: "default",
          direction: "R",
          hidden: false,
        },
      },
      groups: [],
      bundles: [{ id: "b0", source: "Elsewhere", target: "ga" }],
      ordering: [[["a"]]],
      edges: [
        {
          source: null,
          target: "a",
          type: "*",
          time: "*",
          bundle_ids: ["b0"],
        },
      ],
      measures: [{ column: "value", aggregation: "sum" }],
      display: {
        link_width: "value",
        link_color: {
          type: "categorical",
          attr: "type",
          lookup: {},
          default: "#cccccc",
        },
      },
      routing_tree: { value: [0] },
    };

    const flows = [
      { source: "x", target: "a", value: 7 },
      { source: "y", target: "a", value: 3 },
    ];

    const result = executeWeave(spec, flows);

    assert.equal(result.links.length, 0);
    assert.equal(result.nodes.length, 1);
    assert.equal(result.nodes[0].id, "a");
    assert.equal(result.nodes[0].from_elsewhere_links.length, 1);
    assert.equal(result.nodes[0].from_elsewhere_links[0].link_width, 10);
  });

  it("handles mean aggregation", () => {
    const spec = {
      version: "2.0",
      nodes: {
        a: {
          title: "A",
          type: "process",
          group: null,
          style: "default",
          direction: "R",
          hidden: false,
        },
        b: {
          title: "B",
          type: "process",
          group: null,
          style: "default",
          direction: "R",
          hidden: false,
        },
      },
      groups: [],
      bundles: [],
      ordering: [[["a"]], [["b"]]],
      edges: [
        {
          source: "a",
          target: "b",
          type: "*",
          time: "*",
          bundle_ids: [],
        },
      ],
      measures: [
        { column: "value", aggregation: "sum" },
        { column: "intensity", aggregation: "mean" },
      ],
      display: {
        link_width: "value",
        link_color: {
          type: "categorical",
          attr: "type",
          lookup: {},
          default: "#cccccc",
        },
      },
      routing_tree: { value: [0] },
    };

    const flows = [
      { source: "a", target: "b", value: 10, intensity: 2 },
      { source: "a", target: "b", value: 20, intensity: 4 },
    ];

    const result = executeWeave(spec, flows);
    assert.equal(result.links[0].data.value, 30);
    assert.equal(result.links[0].data.intensity, 3);
  });

  it("drops ordering waypoints with no flows but keeps those with flows", () => {
    // A waypoint `w` sits in the spec ordering "in case it is needed".
    // For datasets where flows route through it, it must be kept; for
    // datasets where it carries no flow, it must be dropped from both the
    // node list and the ordering so it does not leave an invisible gap in
    // the layout.
    const spec = {
      version: "2.0",
      nodes: {
        a: {
          title: "A",
          type: "process",
          group: "ga",
          style: "default",
          direction: "R",
          hidden: false,
        },
        w: {
          title: "",
          type: "group",
          group: "gw",
          style: "group",
          direction: "R",
          hidden: true,
        },
        c: {
          title: "C",
          type: "process",
          group: "gc",
          style: "default",
          direction: "R",
          hidden: false,
        },
      },
      groups: [],
      bundles: [],
      ordering: [[["a"]], [["w"]], [["c"]]],
      edges: [
        { source: "a", target: "w", type: "*", time: "*", bundle_ids: [] },
        { source: "w", target: "c", type: "*", time: "*", bundle_ids: [] },
      ],
      measures: [{ column: "value", aggregation: "sum" }],
      display: {
        link_width: "value",
        link_color: {
          type: "categorical",
          attr: "type",
          lookup: {},
          default: "#cccccc",
        },
      },
      // a -> c flows route through both edges (a->w and w->c)
      routing_tree: {
        attr: "source",
        branches: {
          a: {
            attr: "target",
            branches: { c: { value: [0, 1] } },
            default: { value: [] },
          },
        },
        default: { value: [] },
      },
    };

    // With flows through the waypoint: it is kept in nodes and ordering.
    const withFlow = executeWeave(spec, [{ source: "a", target: "c", value: 5 }]);
    assert.deepStrictEqual(
      withFlow.nodes.map((n) => n.id).sort(),
      ["a", "c", "w"]
    );
    assert.deepStrictEqual(withFlow.ordering, [[["a"]], [["w"]], [["c"]]]);

    // Without any matching flows: the waypoint (and the empty layer it would
    // have occupied) is dropped entirely.
    const noFlow = executeWeave(spec, [{ source: "x", target: "y", value: 5 }]);
    assert.deepStrictEqual(noFlow.nodes, []);
    assert.deepStrictEqual(noFlow.ordering, []);
  });

  it("handles quantitative color spec", () => {
    const spec = {
      version: "2.0",
      nodes: {
        a: {
          title: "A",
          type: "process",
          group: null,
          style: "default",
          direction: "R",
          hidden: false,
        },
        b: {
          title: "B",
          type: "process",
          group: null,
          style: "default",
          direction: "R",
          hidden: false,
        },
      },
      groups: [],
      bundles: [],
      ordering: [[["a"]], [["b"]]],
      edges: [
        {
          source: "a",
          target: "b",
          type: "*",
          time: "*",
          bundle_ids: [],
        },
      ],
      measures: [{ column: "value", aggregation: "sum" }],
      display: {
        link_width: "value",
        link_color: {
          type: "quantitative",
          attr: "value",
          palette: ["#000000", "#ffffff"],
          domain: [0, 100],
          intensity: null,
        },
      },
      routing_tree: { value: [0] },
    };

    const flows = [{ source: "a", target: "b", value: 50 }];

    const result = executeWeave(spec, flows);
    // At t=0.5, should be midpoint between #000000 and #ffffff
    assert.equal(result.links[0].color, "#7f7f7f");
  });
});

describe("routeRow", () => {
  it("uses a combined routing_tree (older specs)", () => {
    const spec = {
      routing_tree: {
        attr: "source",
        branches: { a: { value: [0, 1] } },
        default: { value: [] },
      },
    };
    assert.deepStrictEqual(routeRow(spec, { source: "a" }), [0, 1]);
    assert.deepStrictEqual(routeRow(spec, { source: "x" }), []);
  });

  it("routes in two stages: selection tree, then bundle trees", () => {
    const spec = {
      selection_tree: {
        attr: "source",
        branches: {
          a: { value: ["b0"] },
          // Elsewhere pair: from-Elsewhere bundle first, then to-Elsewhere
          c: { value: ["from", "to"] },
        },
        default: { value: [] },
      },
      bundle_trees: {
        b0: {
          attr: "material",
          branches: { m: { value: [0, 1] } },
          default: { value: [0, 2] },
        },
        from: { value: [3] },
        to: { value: [4] },
      },
    };
    assert.deepStrictEqual(routeRow(spec, { source: "a", material: "m" }), [0, 1]);
    assert.deepStrictEqual(routeRow(spec, { source: "a", material: "n" }), [0, 2]);
    assert.deepStrictEqual(routeRow(spec, { source: "c" }), [3, 4]);
    assert.deepStrictEqual(routeRow(spec, { source: "x" }), []);
  });
});

describe("executeWeave with two-stage routing", () => {
  it("produces the same links as a combined routing tree", () => {
    const base = {
      version: "2.1",
      nodes: {
        a: { title: "A", type: "process", group: "ga", style: "default", direction: "R", hidden: false },
        b: { title: "B", type: "process", group: "gb", style: "default", direction: "R", hidden: false },
      },
      groups: [],
      bundles: [{ id: "0", source: "ga", target: "gb" }],
      ordering: [[["a"]], [["b"]]],
      edges: [{ source: "a", target: "b", type: "*", time: "*", bundle_ids: ["0"] }],
      measures: [{ column: "value", aggregation: "sum" }],
      display: {
        link_width: "value",
        link_color: { type: "categorical", attr: "type", lookup: {}, default: "#cccccc" },
      },
    };
    const selection = {
      attr: "source",
      branches: { a: { attr: "target", branches: { b: { value: ["0"] } }, default: { value: [] } } },
      default: { value: [] },
    };
    const twoStage = { ...base, selection_tree: selection, bundle_trees: { 0: { value: [0] } } };
    const combined = {
      ...base,
      routing_tree: {
        attr: "source",
        branches: { a: { attr: "target", branches: { b: { value: [0] } }, default: { value: [] } } },
        default: { value: [] },
      },
    };
    const flows = [
      { source: "a", target: "b", value: 5 },
      { source: "a", target: "c", value: 7 },
      { source: "a", target: "b", value: 3 },
    ];
    const result = executeWeave(twoStage, flows);
    assert.deepStrictEqual(result, executeWeave(combined, flows));
    assert.equal(result.links.length, 1);
    assert.equal(result.links[0].link_width, 8);
    assert.deepStrictEqual(result.links[0].original_flows, [0, 2]);
  });
});

describe("routeRow with value classes", () => {
  it("looks up each value's class before evaluating the trees", () => {
    const spec = {
      value_classes: {
        source: { a1: "c0", a2: "c0", b1: "c1" },
        material: { m: "c0" },
      },
      selection_tree: {
        attr: "source",
        branches: { c0: { value: ["0"] } },
        default: { value: [] },
      },
      bundle_trees: {
        0: {
          attr: "material",
          branches: { c0: { value: [0] } },
          default: { value: [1] },
        },
      },
    };
    assert.deepStrictEqual(routeRow(spec, { source: "a1", material: "m" }), [0]);
    assert.deepStrictEqual(routeRow(spec, { source: "a2", material: "x" }), [1]);
    // Values not in the tables follow default branches
    assert.deepStrictEqual(routeRow(spec, { source: "zz", material: "m" }), []);
    // Even if the value is also a class id, or an Object property name
    assert.deepStrictEqual(routeRow(spec, { source: "c0", material: "m" }), []);
    assert.deepStrictEqual(routeRow(spec, { source: "constructor" }), []);
  });
});
