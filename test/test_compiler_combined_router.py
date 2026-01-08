"""Test the full decision tree combining selections and partitions."""

import pytest
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
    build_routing_rules,
    EdgeKey,
    TaggedEdgeKey,
    build_router,
)


def _build_view_graph(sdd):
    """Helper: build the augmented view graph and merged data from a SankeyDefinition."""
    GV = view_graph(sdd)
    new_waypoints, new_bundles = elsewhere_bundles(sdd)
    GV2 = augment(GV, new_waypoints, new_bundles)
    all_bundles = dict(sdd.bundles, **new_bundles)
    all_nodes = dict(sdd.nodes, **new_waypoints)
    return GV2, all_bundles, all_nodes


def q(s, t, other_excludes=None, **kwargs):
    kwargs_includes = {k: Includes({v}) for k, v in kwargs.items()}
    if s is None:
        # from elsewhere
        return {
            "source": Excludes({t} | set(other_excludes or [])),
            "target": Includes({t}),
            **kwargs_includes,
        }
    elif t is None:
        # to elsewhere
        return {
            "source": Includes({s}),
            "target": Excludes({s} | set(other_excludes or [])),
            **kwargs_includes,
        }
    else:
        return {"source": Includes({s}), "target": Includes({t}), **kwargs_includes}


def test_build_combined_rules_simple():
    """Test building combined rules for simple case."""

    nodes = {
        "a": ProcessGroup(selection=["a1"]),
        "b": ProcessGroup(selection=["b1", "b2"]),
    }
    bundles = {0: Bundle("a", "b")}
    sdd = SankeyDefinition(nodes, bundles, [[["a"], ["b"]]])
    GV2, all_bundles, all_nodes = _build_view_graph(sdd)
    rules = build_routing_rules(
        GV2, all_bundles, all_nodes, sdd.flow_partition, sdd.time_partition, None
    )

    assert rules == Rules(
        [
            (
                q("a1", "b1"),
                (TaggedEdgeKey(EdgeKey("a^*", "b^*", "*", "*"), bundle_id=0),),
            ),
            (
                q("a1", "b2"),
                (TaggedEdgeKey(EdgeKey("a^*", "b^*", "*", "*"), bundle_id=0),),
            ),
        ]
    )


def test_build_combined_rules_elsewhere():
    """Paired Elsewhere flows show the need for potentially different bundle_ids
    for the same rule."""

    nodes = {
        "a": ProcessGroup(selection=["a1"]),
        "b": ProcessGroup(selection=["b1"]),
    }
    bundles = {0: Bundle("a", Elsewhere), 1: Bundle(Elsewhere, "b")}
    sdd = SankeyDefinition(nodes, bundles, [[["a"], ["b"]]])
    GV2, all_bundles, all_nodes = _build_view_graph(sdd)
    rules = build_routing_rules(
        GV2, all_bundles, all_nodes, sdd.flow_partition, sdd.time_partition, None
    )

    assert rules == Rules(
        [
            (
                q("a1", "b1"),
                (
                    TaggedEdgeKey(EdgeKey(None, "b^*", "*", "*"), bundle_id=1),
                    TaggedEdgeKey(EdgeKey("a^*", None, "*", "*"), bundle_id=0),
                ),
            ),
            (
                q("a1", None, other_excludes={"b1"}),
                (TaggedEdgeKey(EdgeKey("a^*", None, "*", "*"), bundle_id=0),),
            ),
            (
                q(None, "b1", other_excludes={"a1"}),
                (TaggedEdgeKey(EdgeKey(None, "b^*", "*", "*"), bundle_id=1),),
            ),
        ]
    )


def test_build_combined_rules_shared_segment():
    # Test construction from full SDD
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
    rules = build_routing_rules(
        GV2, all_bundles, all_nodes, sdd.flow_partition, sdd.time_partition, None
    )

    # They should match
    assert rules == Rules(
        [
            (
                {
                    "source": Includes({"a1"}),
                    "target": Includes({"b1"}),
                    "material": Includes({"m"}),
                },
                (
                    TaggedEdgeKey(
                        key=EdgeKey(s="a^a1", t="via^*", m="m", z="*"), bundle_id="ab"
                    ),
                    TaggedEdgeKey(
                        key=EdgeKey(s="via^*", t="b^m", m="m", z="*"), bundle_id="ab"
                    ),
                ),
            ),
            (
                {
                    "source": Includes({"a1"}),
                    "target": Includes({"b1"}),
                    "material": Includes({"n"}),
                },
                (
                    TaggedEdgeKey(
                        key=EdgeKey(s="a^a1", t="via^*", m="_", z="*"), bundle_id="ab"
                    ),
                    TaggedEdgeKey(
                        key=EdgeKey(s="via^*", t="b^n", m="_", z="*"), bundle_id="ab"
                    ),
                ),
            ),
            (
                {
                    "source": Includes({"a1"}),
                    "target": Includes({"b1"}),
                    "material": Excludes({"m", "n"}),
                },
                (
                    TaggedEdgeKey(
                        key=EdgeKey(s="a^a1", t="via^*", m="_", z="*"), bundle_id="ab"
                    ),
                    TaggedEdgeKey(
                        key=EdgeKey(s="via^*", t="b^_", m="_", z="*"), bundle_id="ab"
                    ),
                ),
            ),
            (
                {
                    "source": Includes({"a2"}),
                    "target": Includes({"b1"}),
                    "material": Includes({"m"}),
                },
                (
                    TaggedEdgeKey(
                        key=EdgeKey(s="a^a2", t="via^*", m="m", z="*"), bundle_id="ab"
                    ),
                    TaggedEdgeKey(
                        key=EdgeKey(s="via^*", t="b^m", m="m", z="*"), bundle_id="ab"
                    ),
                ),
            ),
            (
                {
                    "source": Includes({"a2"}),
                    "target": Includes({"b1"}),
                    "material": Includes({"n"}),
                },
                (
                    TaggedEdgeKey(
                        key=EdgeKey(s="a^a2", t="via^*", m="_", z="*"), bundle_id="ab"
                    ),
                    TaggedEdgeKey(
                        key=EdgeKey(s="via^*", t="b^n", m="_", z="*"), bundle_id="ab"
                    ),
                ),
            ),
            (
                {
                    "source": Includes({"a2"}),
                    "target": Includes({"b1"}),
                    "material": Excludes({"m", "n"}),
                },
                (
                    TaggedEdgeKey(
                        key=EdgeKey(s="a^a2", t="via^*", m="_", z="*"), bundle_id="ab"
                    ),
                    TaggedEdgeKey(
                        key=EdgeKey(s="via^*", t="b^_", m="_", z="*"), bundle_id="ab"
                    ),
                ),
            ),
            (
                {
                    "source": Includes({"c1"}),
                    "target": Includes({"b1"}),
                    "material": Includes({"m"}),
                },
                (
                    TaggedEdgeKey(
                        key=EdgeKey(s="c^*", t="via^*", m="m", z="*"), bundle_id="cb"
                    ),
                    TaggedEdgeKey(
                        key=EdgeKey(s="via^*", t="b^m", m="m", z="*"), bundle_id="cb"
                    ),
                ),
            ),
            (
                {
                    "source": Includes({"c1"}),
                    "target": Includes({"b1"}),
                    "material": Includes({"n"}),
                },
                (
                    TaggedEdgeKey(
                        key=EdgeKey(s="c^*", t="via^*", m="_", z="*"), bundle_id="cb"
                    ),
                    TaggedEdgeKey(
                        key=EdgeKey(s="via^*", t="b^n", m="_", z="*"), bundle_id="cb"
                    ),
                ),
            ),
            (
                {
                    "source": Includes({"c1"}),
                    "target": Includes({"b1"}),
                    "material": Excludes({"m", "n"}),
                },
                (
                    TaggedEdgeKey(
                        key=EdgeKey(s="c^*", t="via^*", m="_", z="*"), bundle_id="cb"
                    ),
                    TaggedEdgeKey(
                        key=EdgeKey(s="via^*", t="b^_", m="_", z="*"), bundle_id="cb"
                    ),
                ),
            ),
        ]
    )


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
