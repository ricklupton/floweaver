"""Tests for routing over value classes."""

import pytest
from hypothesis import example, given, settings, strategies as st

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
from floweaver.compiler.combined_router import build_router
from floweaver.compiler.rules import Includes, Excludes
from floweaver.compiler.tree import TwoStageRouter
from floweaver.compiler.value_classes import compute_value_classes, ValueClasses

import hypothesis_strategies as fst


# =============================================================================
# Computing and applying value classes
# =============================================================================


def test_values_in_the_same_sets_share_a_class():
    classes = compute_value_classes(
        {
            "source": [{"a", "b", "c"}, {"c", "d"}],
            "material": [{"m"}],
        }
    )
    source = classes.tables["source"]
    assert source["a"] == source["b"]  # both only in the first set
    assert len({source["a"], source["c"], source["d"]}) == 3
    assert set(classes.tables["material"]) == {"m"}


def test_classify_query_preserves_includes_and_excludes():
    classes = compute_value_classes({"source": [{"a", "b"}, {"c"}]})
    ab, c = classes.tables["source"]["a"], classes.tables["source"]["c"]
    assert classes.classify_query({"source": Excludes({"a", "b", "c"})}) == {
        "source": Excludes({ab, c})
    }
    assert classes.classify_query({"source": Includes({"a", "b"})}) == {
        "source": Includes({ab})
    }


def test_lookup_unmentioned_value_is_none():
    classes = compute_value_classes({"source": [{"a"}]})
    assert classes.lookup("source", "a") == "c0"
    assert classes.lookup("source", "zzz") is None
    # Attributes without a table are passed through
    assert classes.lookup("other", "zzz") == "zzz"


def test_classify_value_not_included_raises():
    classes = compute_value_classes({"source": [{"a"}]})
    with pytest.raises(ValueError, match="not included"):
        classes.classify_values("source", {"a", "b"})


def test_class_ids_follow_sorted_values():
    # Class ids are assigned in order of the sorted values, so they don't
    # depend on the order of the sets
    sets = [{"x", "y"}, {"y", "z"}, {"w"}]
    expected = {"w": "c0", "x": "c1", "y": "c2", "z": "c3"}
    assert compute_value_classes({"source": sets}).tables["source"] == expected
    assert compute_value_classes({"source": sets[::-1]}).tables["source"] == expected


def test_dict_roundtrip():
    classes = compute_value_classes({"source": [{"a", "b"}, {"c"}]})
    assert ValueClasses.from_dict(classes.to_dict()) == classes


# =============================================================================
# Routing over value classes is identical to routing over values
# =============================================================================


def _build_router(sdd, use_value_classes):
    GV = view_graph(sdd)
    new_waypoints, new_bundles = elsewhere_bundles(sdd)
    GV2 = augment(GV, new_waypoints, new_bundles)
    return build_router(
        GV2,
        dict(sdd.bundles, **new_bundles),
        dict(sdd.nodes, **new_waypoints),
        sdd.flow_partition,
        sdd.time_partition,
        None,
        use_value_classes=use_value_classes,
    )


# Values used by the generated SankeyDefinitions, plus values that no rule
# mentions.
row_strategy = st.fixed_dictionaries(
    {
        "source": st.sampled_from(
            [f"p{i:02d}" for i in range(1, 25)] + ["q01", "unknown"]
        ),
        "target": st.sampled_from(
            [f"p{i:02d}" for i in range(1, 25)] + ["q01", "unknown"]
        ),
        "material": st.sampled_from(["m", "n", "unknown"]),
        "category": st.sampled_from(["cat1", "cat2", "cat3", "cat4", "unknown"]),
    }
)


def _pair_sdd():
    """Partitioned groups linked by Elsewhere pairs and a partitioned waypoint."""
    nodes = {
        "A": ProcessGroup(["p01", "p02"], Partition.Simple("process", ["p01"])),
        "B": ProcessGroup(["p03", "p04"]),
        "C": ProcessGroup(["p05"]),
        "w": Waypoint(Partition.Simple("source", ["p07", "p08"])),
    }
    bundles = [
        Bundle("A", "B", flow_selection="material == 'm'"),
        Bundle(Elsewhere, "C", waypoints=["w"]),
        Bundle("B", Elsewhere),
    ]
    return SankeyDefinition(
        nodes,
        bundles,
        [["w"], ["A"], ["B"], ["C"]],
        flow_partition=Partition.Simple("material", ["m"]),
    )


@settings(print_blob=True, deadline=None, max_examples=200)
@given(fst.sankey_definitions(), st.lists(row_strategy, min_size=1, max_size=50))
@example(
    _pair_sdd(),
    [
        {"source": "p01", "target": "p03", "material": "m", "category": "cat1"},
        {"source": "p02", "target": "p04", "material": "n", "category": "cat1"},
        {"source": "p01", "target": "p05", "material": "m", "category": "cat1"},
        {"source": "p07", "target": "p05", "material": "n", "category": "cat1"},
        {"source": "unknown", "target": "p05", "material": "m", "category": "cat1"},
        {"source": "p03", "target": "unknown", "material": "x", "category": "cat1"},
    ],
)
def test_value_classes_do_not_change_routing(sdd, rows):
    try:
        router_values, edges_values = _build_router(sdd, use_value_classes=False)
    except ValueError:
        # Invalid definitions (e.g. overlapping explicit bundles) are rejected
        # whether or not value classes are used.
        return
    router_classes, edges_classes = _build_router(sdd, use_value_classes=True)

    assert isinstance(router_classes, TwoStageRouter)
    assert router_classes.value_classes is not None
    assert sorted(edges_classes, key=repr) == sorted(edges_values, key=repr)
    for row in rows:
        assert tuple(edges_classes[i] for i in router_classes.evaluate(row)) == tuple(
            edges_values[i] for i in router_values.evaluate(row)
        ), row
