"""Test the full decision tree combining selections and partitions."""

from floweaver import (
    SankeyDefinition,
    ProcessGroup,
    Waypoint,
    Bundle,
    Partition,
    Elsewhere,
)
from floweaver.augment_view_graph import elsewhere_bundles, augment
from floweaver.view_graph import view_graph
from floweaver.compiler.rules import Rules, Includes, Excludes
from floweaver.compiler.spec import EdgeSpec
from floweaver.compiler.combined_router import (
    build_bundle_routing_rules,
    EdgeKey,
    build_router,
)
from floweaver.compiler.tree import TwoStageRouter, LeafNode
from floweaver.compiler.spec import WeaverSpec


def _build_view_graph(sdd):
    """Helper: build the augmented view graph and merged data from a SankeyDefinition."""
    GV = view_graph(sdd)
    new_waypoints, new_bundles = elsewhere_bundles(sdd)
    GV2 = augment(GV, new_waypoints, new_bundles)
    all_bundles = dict(sdd.bundles, **new_bundles)
    all_nodes = dict(sdd.nodes, **new_waypoints)
    return GV2, all_bundles, all_nodes


def _bundle_rules(sdd):
    GV2, all_bundles, all_nodes = _build_view_graph(sdd)
    return build_bundle_routing_rules(
        GV2, all_bundles, all_nodes, sdd.flow_partition, sdd.time_partition, None
    )


def _router(sdd, use_value_classes=True):
    GV2, all_bundles, all_nodes = _build_view_graph(sdd)
    return build_router(
        GV2,
        all_bundles,
        all_nodes,
        sdd.flow_partition,
        sdd.time_partition,
        None,
        use_value_classes=use_value_classes,
    )


def test_bundle_routing_rules_simple():
    nodes = {
        "a": ProcessGroup(selection=["a1"]),
        "b": ProcessGroup(selection=["b1", "b2"]),
    }
    bundles = {0: Bundle("a", "b")}
    sdd = SankeyDefinition(nodes, bundles, [[["a"], ["b"]]])

    # Rules within a bundle don't repeat the bundle's selection
    assert _bundle_rules(sdd) == {
        0: Rules([({}, (EdgeKey("a^*", "b^*", "*", "*"),))]),
    }


def test_bundle_routing_rules_pruned_to_bundle_selection():
    """Partition rules that no row in the bundle can match are dropped."""
    nodes = {
        "a": ProcessGroup(["a1", "a2"], Partition.Simple("source", ["a1", "a2"])),
        "b": ProcessGroup(["b1"]),
    }
    bundles = {0: Bundle("a", "b", flow_selection="material == 'm'")}
    sdd = SankeyDefinition(
        nodes,
        bundles,
        [[["a"], ["b"]]],
        flow_partition=Partition.Simple("material", ["m", "n"]),
    )

    # No rules for the catch-all source group "a^_" (the bundle only selects
    # a1 and a2), or for flow types "n" and "_" (it only selects material m)
    assert _bundle_rules(sdd) == {
        0: Rules(
            [
                (
                    {"source": Includes({"a1"}), "material": Includes({"m"})},
                    (EdgeKey("a^a1", "b^*", "m", "*"),),
                ),
                (
                    {"source": Includes({"a2"}), "material": Includes({"m"})},
                    (EdgeKey("a^a2", "b^*", "m", "*"),),
                ),
            ]
        ),
    }


def test_bundle_routing_rules_shared_segment():
    material_partition = Partition.Simple("material", ["m"])
    nodes = {
        "a": ProcessGroup(["a1", "a2"], Partition.Simple("source", ["a1", "a2"])),
        "b": ProcessGroup(["b1"], Partition.Simple("material", ["m", "n"])),
        "c": ProcessGroup(["c1"]),
        "via": Waypoint(),
    }
    bundles = {
        "ab": Bundle("a", "b", waypoints=["via"]),
        "cb": Bundle("c", "b", waypoints=["via"]),
    }
    ordering = [[["a", "c"], ["via"], ["b"]]]
    sdd = SankeyDefinition(nodes, bundles, ordering, flow_partition=material_partition)

    def rule(source, material, first, second):
        query = {"material": material}
        if source is not None:
            query["source"] = Includes({source})
        return (query, (first, second))

    m, n, other = Includes({"m"}), Includes({"n"}), Excludes({"m", "n"})
    assert _bundle_rules(sdd) == {
        "ab": Rules(
            [
                rule(
                    s,
                    material,
                    EdgeKey(f"a^{s}", "via^*", flow_type, "*"),
                    EdgeKey("via^*", f"b^{b_group}", flow_type, "*"),
                )
                for s in ["a1", "a2"]
                for material, flow_type, b_group in [
                    (m, "m", "m"),
                    (n, "_", "n"),
                    (other, "_", "_"),
                ]
            ]
        ),
        "cb": Rules(
            [
                rule(
                    None,
                    material,
                    EdgeKey("c^*", "via^*", flow_type, "*"),
                    EdgeKey("via^*", f"b^{b_group}", flow_type, "*"),
                )
                for material, flow_type, b_group in [
                    (m, "m", "m"),
                    (n, "_", "n"),
                    (other, "_", "_"),
                ]
            ]
        ),
    }


def test_router_selection_tree_routes_to_bundles():
    nodes = {
        "a": ProcessGroup(selection=["a1"]),
        "b": ProcessGroup(selection=["b1"]),
        "c": ProcessGroup(selection=["c1"]),
    }
    bundles = {0: Bundle("a", "b"), 1: Bundle("a", "c")}
    sdd = SankeyDefinition(nodes, bundles, [[["a"], ["b", "c"]]])
    # Without value classes, so the trees can be evaluated on values directly
    router, _ = _router(sdd, use_value_classes=False)

    assert isinstance(router, TwoStageRouter)
    assert set(router.bundle_trees) == {"0", "1"}
    select = router.selection_tree.evaluate
    assert tuple(select({"source": "a1", "target": "b1"})) == ("0",)
    assert tuple(select({"source": "a1", "target": "c1"})) == ("1",)
    assert tuple(select({"source": "b1", "target": "c1"})) == ()


def test_router_elsewhere_pair():
    """A flow matched by a pair of Elsewhere bundles is routed through both,
    from-Elsewhere first."""
    nodes = {
        "a": ProcessGroup(selection=["a1"]),
        "b": ProcessGroup(selection=["b1"]),
    }
    bundles = {0: Bundle("a", Elsewhere), 1: Bundle(Elsewhere, "b")}
    sdd = SankeyDefinition(nodes, bundles, [[["a"], ["b"]]])
    router, edge_specs = _router(sdd, use_value_classes=False)

    def eval_specs(data):
        return tuple(edge_specs[i] for i in router.evaluate(data))

    assert tuple(router.selection_tree.evaluate({"source": "a1", "target": "b1"})) == (
        "1",
        "0",
    )
    assert eval_specs({"source": "a1", "target": "b1"}) == (
        EdgeSpec(None, "b^*", "*", "*", [1]),
        EdgeSpec("a^*", None, "*", "*", [0]),
    )
    assert eval_specs({"source": "a1", "target": "x"}) == (
        EdgeSpec("a^*", None, "*", "*", [0]),
    )
    assert eval_specs({"source": "x", "target": "b1"}) == (
        EdgeSpec(None, "b^*", "*", "*", [1]),
    )


def test_router_json_roundtrip():
    nodes = {
        "a": ProcessGroup(["a1", "a2"], Partition.Simple("source", ["a1", "a2"])),
        "b": ProcessGroup(selection=["b1"]),
    }
    bundles = {0: Bundle("a", "b"), 1: Bundle(Elsewhere, "b")}
    sdd = SankeyDefinition(nodes, bundles, [[["a"], ["b"]]])
    router, _ = _router(sdd)
    router2 = TwoStageRouter.from_dict(router.to_dict())
    for row in [
        {"source": "a1", "target": "b1"},
        {"source": "a2", "target": "b1"},
        {"source": "x", "target": "b1"},
        {"source": "x", "target": "y"},
    ]:
        assert tuple(router2.evaluate(row)) == tuple(router.evaluate(row))


def test_spec_with_combined_routing_tree_still_loads():
    """Specs from earlier versions have a single combined `routing_tree`."""
    from floweaver import compile_sankey_definition

    nodes = {
        "a": ProcessGroup(selection=["a1"]),
        "b": ProcessGroup(selection=["b1"]),
    }
    sdd = SankeyDefinition(nodes, [Bundle("a", "b")], [["a"], ["b"]])
    data = compile_sankey_definition(sdd).to_json()
    assert "selection_tree" in data and "routing_tree" not in data

    # Replace the two-stage router with an equivalent combined tree
    del data["value_classes"], data["selection_tree"], data["bundle_trees"]
    data["routing_tree"] = {"value": [0]}
    spec = WeaverSpec.from_json(data)
    assert spec.routing_tree == LeafNode([0])
    assert WeaverSpec.from_json(spec.to_json()).to_json() == data


def test_routing_shared_segment():
    """Test that rows route to correct edges through shared segment."""
    material_partition = Partition.Simple("material", ["m"])
    nodes = {
        "a": ProcessGroup(["a1", "a2"], Partition.Simple("source", ["a1", "a2"])),
        "b": ProcessGroup(["b1"], Partition.Simple("material", ["m", "n"])),
        "c": ProcessGroup(["c1"]),
        "via": Waypoint(),
    }
    bundles = {
        "ab": Bundle("a", "b", waypoints=["via"]),
        "cb": Bundle("c", "b", waypoints=["via"]),
    }
    ordering = [[["a", "c"], ["via"], ["b"]]]
    sdd = SankeyDefinition(nodes, bundles, ordering, flow_partition=material_partition)
    GV2, all_bundles, all_nodes = _build_view_graph(sdd)

    tree, edge_specs = build_router(
        GV2, all_bundles, all_nodes, sdd.flow_partition, sdd.time_partition, None
    )

    def eval_specs(data):
        result = tree.evaluate(data)
        return tuple(edge_specs[i] for i in result or ())

    # Bundle ab: a1/a2 -> via -> b, material m
    assert eval_specs({"source": "a1", "target": "b1", "material": "m"}) == (
        EdgeSpec("a^a1", "via^*", "m", "*", ["ab"]),
        EdgeSpec("via^*", "b^m", "m", "*", ["ab", "cb"]),
    )
    assert eval_specs({"source": "a2", "target": "b1", "material": "m"}) == (
        EdgeSpec("a^a2", "via^*", "m", "*", ["ab"]),
        EdgeSpec("via^*", "b^m", "m", "*", ["ab", "cb"]),  # shared!
    )

    # Bundle ab: a1/a2 -> via -> b, material n
    assert eval_specs({"source": "a1", "target": "b1", "material": "n"}) == (
        EdgeSpec("a^a1", "via^*", "_", "*", ["ab"]),
        EdgeSpec("via^*", "b^n", "_", "*", ["ab", "cb"]),  # shared!
    )

    # Bundle ab: a1/a2 -> via -> b, material other (falls to default)
    assert eval_specs({"source": "a1", "target": "b1", "material": "x"}) == (
        EdgeSpec("a^a1", "via^*", "_", "*", ["ab"]),
        EdgeSpec("via^*", "b^_", "_", "*", ["ab", "cb"]),  # shared!
    )

    # Bundle cb: c1 -> via -> b, material m
    assert eval_specs({"source": "c1", "target": "b1", "material": "m"}) == (
        EdgeSpec("c^*", "via^*", "m", "*", ["cb"]),
        EdgeSpec("via^*", "b^m", "m", "*", ["ab", "cb"]),  # shared!
    )

    # Bundle cb: c1 -> via -> b, material n
    assert eval_specs({"source": "c1", "target": "b1", "material": "n"}) == (
        EdgeSpec("c^*", "via^*", "_", "*", ["cb"]),
        EdgeSpec("via^*", "b^n", "_", "*", ["ab", "cb"]),  # shared!
    )

    # No match: source not in any bundle
    assert eval_specs({"source": "x", "target": "b1", "material": "m"}) == ()

    # No match: target not in any bundle
    assert eval_specs({"source": "a1", "target": "x", "material": "m"}) == ()


# def test_build_bundle_partition_routing():
#     # Test construction from pre-computed edge routing and bundle edges
#     material_partition = Partition.Simple("material", ["m"])
#     nodes = {
#         "a": ProcessGroup(["a1", "a2"], Partition.Simple("source", ["a1", "a2"])),
#         "b": ProcessGroup(["b1"], Partition.Simple("material", ["m", "n"])),
#         "via": Waypoint(),
#     }

#     # Build per-edge routing (as would be extracted from view graph)
#     seg1 = build_segment_routing(
#         source_node="a",
#         target_node="via",
#         source_partition=nodes["a"].partition,
#         target_partition=None,
#         material_partition=material_partition,
#     )

#     seg2 = build_segment_routing(
#         source_node="via",
#         target_node="b",
#         source_partition=None,
#         target_partition=nodes["b"].partition,
#         material_partition=material_partition,
#     )

#     edge_routing = {
#         ("a", "via"): seg1,
#         ("via", "b"): seg2,
#     }
#     bundle_edges = {
#         0: [("a", "via"), ("via", "b")],
#     }

#     bundle_rules = build_bundle_partition_routing(edge_routing, bundle_edges)

#     merged = merge_segment_routings(seg1, seg2)

#     # They should match
#     assert bundle_rules == {
#         0: merged,
#     }


def test_compile_scales_with_elsewhere_pairs_and_partitions():
    """Regression test: compiling once multiplied every selection region by its
    bundles' partition rules (squared for Elsewhere pairs), which was
    intractable for diagrams with many partitioned ProcessGroups linked only
    via Elsewhere."""
    import time
    import pandas as pd
    from floweaver import compile_sankey_definition, weave, weave_compiled

    n_groups, n_processes, n_materials = 20, 5, 10
    nodes = {}
    for g in range(n_groups):
        processes = [f"p{g}_{i}" for i in range(n_processes)]
        nodes[f"G{g}"] = ProcessGroup(processes, Partition.Simple("process", processes))
    sdd = SankeyDefinition(
        nodes,
        [],
        [[f"G{g}"] for g in range(n_groups)],
        flow_partition=Partition.Simple(
            "material", [f"m{i}" for i in range(n_materials)]
        ),
    )

    start = time.perf_counter()
    compile_sankey_definition(sdd)
    assert time.perf_counter() - start < 10

    # Results still match the original implementation
    flows = pd.DataFrame.from_records(
        [
            ("p0_1", "p3_2", "m1", 3),  # Elsewhere pair
            ("p3_2", "p19_4", "m9", 2),  # Elsewhere pair
            ("x", "p5_0", "m2", 1),  # from Elsewhere
            ("p7_3", "y", "other", 4),  # to Elsewhere
        ],
        columns=("source", "target", "material", "value"),
    )

    def elsewhere_links(result):
        return sorted(
            (link.source or "", link.target or "", link.type, link.link_width)
            for node in result.nodes
            for link in node.from_elsewhere_links + node.to_elsewhere_links
        ) + sorted(
            (link.source, link.target, link.type, link.link_width)
            for link in result.links
        )

    assert elsewhere_links(weave_compiled(sdd, flows)) == elsewhere_links(
        weave(sdd, flows)
    )
