import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { executeWeave, evaluateTree } from "../src/index.js";

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
