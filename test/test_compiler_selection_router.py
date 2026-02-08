import pytest
import pandas as pd
from floweaver import (
    ProcessGroup,
    Bundle,
    Elsewhere,
)
from floweaver.compiler.rules import Rules, Includes, Excludes
from floweaver.compiler.selection_router import (
    build_bundle_selection_query,
    build_selection_rules,
    resolve_candidates,
    SingleBundleMatch,
    ElsewhereBundlePairMatch,
)


def test_simple_selection_query():
    """Test building selection rules for simple case."""

    nodes = {
        "a": ProcessGroup(selection=["a1", "a2"]),
        "b": ProcessGroup(selection=["b1", "b2"]),
    }
    bundle = Bundle("a", "b")
    query = build_bundle_selection_query(bundle, nodes, None)

    assert query == {
        "source": Includes({"a1", "a2"}),
        "target": Includes({"b1", "b2"}),
    }


def test_selection_query_with_filters():
    """Test that filter dimensions create additional queries."""

    nodes = {
        "a": ProcessGroup(selection=["a1", "a2"]),
        "b": ProcessGroup(selection=["b1", "b2"]),
    }
    bundle = Bundle("a", "b", flow_selection="material == 'steel'")
    query = build_bundle_selection_query(bundle, nodes, None)

    assert query == {
        "source": Includes({"a1", "a2"}),
        "target": Includes({"b1", "b2"}),
        "material": Includes({"steel"}),
    }


def test_selection_query_from_elsewhere():
    """Test from-elsewhere bundles"""

    nodes = {
        "a": ProcessGroup(selection=["a1", "a2"]),
    }
    bundle = Bundle("a", Elsewhere)
    query = build_bundle_selection_query(bundle, nodes, None)

    assert query == {
        "source": Includes({"a1", "a2"}),
        "target": Excludes({"a1", "a2"}),
    }


def test_selection_query_to_elsewhere():
    """Test to-elsewhere bundles"""

    nodes = {
        "a": ProcessGroup(selection=["a1", "a2"]),
    }
    bundle = Bundle(Elsewhere, "a")
    query = build_bundle_selection_query(bundle, nodes, None)

    assert query == {
        "source": Excludes({"a1", "a2"}),
        "target": Includes({"a1", "a2"}),
    }


def test_selection_expansion_simple():
    """Test expansion using query strings and dimension tables."""
    nodes = {
        "production": ProcessGroup(selection="type == 'production'"),
        "consumption": ProcessGroup(selection="type == 'consumption'"),
    }
    bundle = Bundle("production", "consumption")
    dim_process = pd.DataFrame(
        {
            "id": ["a1", "a2", "b1", "b2", "c1", "c2"],
            "type": [
                "production",
                "production",
                "consumption",
                "consumption",
                "waste",
                "waste",
            ],
            "sector": [
                "mining",
                "mining",
                "manufacturing",
                "manufacturing",
                "disposal",
                "disposal",
            ],
        }
    ).set_index("id")

    query = build_bundle_selection_query(bundle, nodes, dim_process)

    assert query == {
        "source": Includes({"a1", "a2"}),
        "target": Includes({"b1", "b2"}),
    }


class TestResolveCandidates:
    def test_explicit_normal_bundles_prioritised_over_implicit(self):
        bundles = {
            "explicit": Bundle("a", "b"),
            "__implicit_elsewhere": Bundle(Elsewhere, target="b"),
        }
        assert resolve_candidates(
            ["explicit", "__implicit_elsewhere"], bundles
        ) == SingleBundleMatch("explicit")

    def test_explicit_normal_bundles_prioritised_over_explicit_elsewhere(self):
        bundles = {
            "explicit_normal": Bundle("a", "b"),
            "explicit_elsewhere": Bundle(Elsewhere, target="b"),
        }
        assert resolve_candidates(
            ["explicit_normal", "explicit_elsewhere"], bundles
        ) == SingleBundleMatch("explicit_normal")

    def test_single_candidates_are_used(self):
        bundles = {
            "explicit_normal": Bundle("a", "b"),
            "explicit_elsewhere": Bundle(Elsewhere, target="b"),
            "__implicit_elsewhere": Bundle(Elsewhere, target="b"),
            "__implicit_normal": Bundle("a", target="b"),
        }
        for k in bundles:
            assert resolve_candidates([k], bundles) == SingleBundleMatch(k)

    def test_elsewhere_bundles_can_be_paired(self):
        bundles = {
            "from_elsewhere": Bundle(Elsewhere, "b"),
            "to_elsewhere": Bundle("a", target=Elsewhere),
        }
        assert resolve_candidates(
            ["from_elsewhere", "to_elsewhere"], bundles
        ) == ElsewhereBundlePairMatch("from_elsewhere", "to_elsewhere")

    def test_elsewhere_bundles_can_be_paired_implicit(self):
        bundles = {
            "explicit": Bundle("a", Elsewhere),
            "__>node1": Bundle(Elsewhere, "b"),
        }
        assert resolve_candidates(
            ["explicit", "__>node1"], bundles
        ) == ElsewhereBundlePairMatch("__>node1", "explicit")

    def test_error_if_bundles_duplicated(self):
        bundles = {
            "bundle1": Bundle("a", "b"),
            "bundle2": Bundle("c", "d"),
        }
        with pytest.raises(ValueError):
            resolve_candidates(["bundle1", "bundle2"], bundles)


def q(s, t, **kwargs):
    kwargs_includes = {k: Includes({v}) for k, v in kwargs.items()}
    return {"source": Includes({s}), "target": Includes({t}), **kwargs_includes}


def test_build_selection_rules():
    """Test building selection rules for simple case."""

    nodes = {
        "a": ProcessGroup(selection=["a1", "a2"]),
        "b": ProcessGroup(selection=["b1", "b2"]),
    }
    bundles = {0: Bundle("a", "b")}
    rules = build_selection_rules(bundles, nodes, None)

    assert rules == Rules(
        [
            (q("a1", "b1"), SingleBundleMatch(0)),
            (q("a1", "b2"), SingleBundleMatch(0)),
            (q("a2", "b1"), SingleBundleMatch(0)),
            (q("a2", "b2"), SingleBundleMatch(0)),
        ]
    )


def test_build_selection_rules_flow_selection():
    """Test that bundles with flow selections."""
    nodes = {
        "a": ProcessGroup(selection=["a1"]),
        "b": ProcessGroup(selection=["b1"]),
    }
    bundles = {
        0: Bundle("a", "b", flow_selection="type == 'one'"),
        1: Bundle("a", "b", flow_selection="type == 'another'"),
    }
    rules = build_selection_rules(bundles, nodes, None)

    assert rules == Rules(
        [
            (q("a1", "b1", type="one"), SingleBundleMatch(0)),
            (q("a1", "b1", type="another"), SingleBundleMatch(1)),
        ]
    )


def test_build_selection_rules_raises_on_overlap():
    nodes = {
        "a": ProcessGroup(selection=["a1"]),
        "b": ProcessGroup(selection=["b1"]),
    }
    bundles = {
        0: Bundle("a", "b", flow_selection="type == 'one'"),
        1: Bundle("a", "b"),  # no flow selection
    }

    with pytest.raises(ValueError, match="Multiple explicit bundles"):
        build_selection_rules(bundles, nodes, None)


def test_build_selection_rules_elsewhere_pair():
    """Test that bundles with flow selections."""
    nodes = {
        "a": ProcessGroup(selection=["a1"]),
        "b": ProcessGroup(selection=["b1"]),
    }
    bundles = {
        0: Bundle("a", Elsewhere),
        1: Bundle(Elsewhere, "b"),
    }
    rules = build_selection_rules(bundles, nodes, None)

    assert rules == Rules(
        [
            # a1 -> b1: both bundles match, forms pair
            (
                {"source": Includes({"a1"}), "target": Includes({"b1"})},
                ElsewhereBundlePairMatch(
                    from_elsewhere_bundle_id=1, to_elsewhere_bundle_id=0
                ),
            ),
            # a1 -> elsewhere (outside both groups): only "a to elsewhere" bundle
            (
                {"source": Includes({"a1"}), "target": Excludes({"a1", "b1"})},
                SingleBundleMatch(bundle_id=0),
            ),
            # elsewhere -> b1: only "elsewhere to b" bundle
            (
                {"source": Excludes({"a1", "b1"}), "target": Includes({"b1"})},
                SingleBundleMatch(bundle_id=1),
            ),
        ]
    )


# TODO: not testing flow_selection currently
