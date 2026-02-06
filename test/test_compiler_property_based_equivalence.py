"""Property-based equivalence tests using hypothesis.

These tests automatically generate random datasets and Sankey definitions to
verify that weave() and weave_compiled() produce equivalent results across a
wide range of inputs.

Generators aim to create realistic scenarios including:
- Flows that don't match any bundles
- Bundles with no matching flows
- Process IDs in flows but not in process groups
- Random mix of partitions and waypoints
- Edge cases that might break implementations
"""

import pandas as pd
import numpy as np
from hypothesis import (
    given,
    strategies as st,
    settings,
    assume,
    reproduce_failure,
    event,
    note,
)

from floweaver import (
    SankeyDefinition,
    ProcessGroup,
    Waypoint,
    Bundle,
    Partition,
    Dataset,
    Elsewhere,
)
from floweaver.compiler.tree import build_tree
from floweaver.compiler.selection_router import build_selection_rules
from floweaver.compiler.combined_router import (
    SingleBundleMatch,
    ElsewhereBundlePairMatch,
)
from floweaver.view_graph import view_graph
from floweaver.augment_view_graph import augment, elsewhere_bundles
from floweaver.weave import weave, weave_compiled

import hypothesis_strategies as fst


def sankey_data_equivalent(new_result, old_result):
    """Compare SankeyData objects with detailed assertion messages."""
    assert new_result.ordering == old_result.ordering, (
        f"Ordering mismatch: {new_result.ordering} != {old_result.ordering}"
    )

    # Compare nodes with tolerance for floating point differences
    new_nodes_sorted = sorted(new_result.nodes, key=lambda n: n.id)
    old_nodes_sorted = sorted(old_result.nodes, key=lambda n: n.id)
    assert len(new_nodes_sorted) == len(old_nodes_sorted), (
        f"Node count mismatch: {len(new_nodes_sorted)} != {len(old_nodes_sorted)}"
    )

    for new_node, old_node in zip(new_nodes_sorted, old_nodes_sorted):
        assert new_node.id == old_node.id, (
            f"Node id mismatch: {new_node.id} != {old_node.id}"
        )
        assert new_node.title == old_node.title
        assert new_node.direction == old_node.direction
        # The new implementation correctly sets hidden=True for catch-all partition
        # nodes (label='_'), while the old defaults to False. Accept this improvement.
        if new_node.hidden != old_node.hidden:
            assert new_node.id.endswith("^_"), (
                f"hidden mismatch for non-catch-all node: {new_node.id}"
            )
            assert new_node.hidden == True and old_node.hidden == False, (
                f"unexpected hidden values: new={new_node.hidden}, old={old_node.hidden}"
            )
        assert new_node.style == old_node.style

        # Compare elsewhere links with float tolerance
        assert len(new_node.from_elsewhere_links) == len(old_node.from_elsewhere_links)
        assert len(new_node.to_elsewhere_links) == len(old_node.to_elsewhere_links)

        for new_link, old_link in zip(
            new_node.from_elsewhere_links, old_node.from_elsewhere_links
        ):
            assert new_link.source == old_link.source
            assert new_link.target == old_link.target
            assert set(new_link.original_flows) == set(old_link.original_flows)
            # The old implementation has a bug where flows can be counted multiple times
            # when they match overlapping elsewhere bundles. The new implementation
            # correctly deduplicates. If unique flows match but link_width differs,
            # check if it's due to duplicates in the old result.
            if not np.isclose(new_link.link_width, old_link.link_width, rtol=1e-14):
                old_has_duplicates = len(old_link.original_flows) > len(
                    set(old_link.original_flows)
                )
                new_has_duplicates = len(new_link.original_flows) > len(
                    set(new_link.original_flows)
                )
                assert old_has_duplicates and not new_has_duplicates, (
                    f"link_width mismatch not due to old duplicates: {new_link.link_width} vs {old_link.link_width}"
                )

        for new_link, old_link in zip(
            new_node.to_elsewhere_links, old_node.to_elsewhere_links
        ):
            assert new_link.source == old_link.source
            assert new_link.target == old_link.target
            assert set(new_link.original_flows) == set(old_link.original_flows)
            # Same duplicate handling as above
            if not np.isclose(new_link.link_width, old_link.link_width, rtol=1e-14):
                old_has_duplicates = len(old_link.original_flows) > len(
                    set(old_link.original_flows)
                )
                new_has_duplicates = len(new_link.original_flows) > len(
                    set(new_link.original_flows)
                )
                assert old_has_duplicates and not new_has_duplicates, (
                    f"link_width mismatch not due to old duplicates: {new_link.link_width} vs {old_link.link_width}"
                )

    new_groups = sorted(new_result.groups, key=lambda group: group["id"])
    old_groups = sorted(old_result.groups, key=lambda group: group["id"])
    assert new_groups == old_groups, f"Groups mismatch"

    # Check link properties
    def _link_props(link):
        return (
            link.source,
            link.target,
            link.type,
            link.time,
            link.title,
            link.color,
            set(link.original_flows),
        )

    new_props = sorted([_link_props(link) for link in new_result.links])
    old_props = sorted([_link_props(link) for link in old_result.links])
    assert new_props == old_props, (
        f"Link properties mismatch:\nNew: {new_props[:3]}\nOld: {old_props[:3]}"
    )

    # Check link values
    old_links_dict = {(l.source, l.target, l.type, l.time): l for l in old_result.links}
    new_links_dict = {(l.source, l.target, l.type, l.time): l for l in new_result.links}

    assert set(old_links_dict.keys()) == set(new_links_dict.keys()), (
        "Link keys don't match"
    )

    for key in old_links_dict:
        old_link = old_links_dict[key]
        new_link = new_links_dict[key]

        assert np.isclose(old_link.link_width, new_link.link_width, rtol=1e-14), (
            f"link_width mismatch for {key}: {old_link.link_width} vs {new_link.link_width}"
        )

        assert np.isclose(old_link.opacity, new_link.opacity, rtol=1e-14), (
            f"opacity mismatch for {key}: {old_link.opacity} vs {new_link.opacity}"
        )

        for measure_key in old_link.data:
            old_val = old_link.data[measure_key]
            new_val = new_link.data[measure_key]
            if isinstance(old_val, (int, float, np.number)):
                assert np.isclose(old_val, new_val, rtol=1e-14), (
                    f"data[{measure_key}] mismatch for {key}: {old_val} vs {new_val}"
                )


# ============================================================================
# Helper functions
# ============================================================================


def _create_explicit_palette(sdd, dataset):
    """Create an explicit color palette dict to ensure color consistency.

    The default link_color is CategoricalScale('type'), which colors by the 'type'
    attribute of edges. This comes from flow_partition if present, otherwise from
    the flow data itself.

    To ensure both implementations assign the same colors, we pre-create a
    deterministic mapping from type values to colors.
    """
    from palettable.colorbrewer.qualitative import Pastel1_8  # ty:ignore[unresolved-import]

    # Get flow data
    if hasattr(dataset, "_table"):
        flows_df = dataset._table
    else:
        flows_df = dataset

    # Determine which dimension will be used for edge types
    # If there's a global flow_partition, use its dimension
    # Otherwise, default to 'type' column in flow data
    if sdd.flow_partition is not None:
        # Extract dimension name from flow_partition
        # Flow partition groups have queries like (('material', ('m', 'n')),)
        partition_dim = None
        for group in sdd.flow_partition.groups:
            if group.query:
                partition_dim = group.query[0][0]  # First dimension name
                break

        if partition_dim and partition_dim in flows_df.columns:
            type_values = sorted(flows_df[partition_dim].unique())
        else:
            # Fallback to type column
            type_values = (
                sorted(flows_df["type"].unique()) if "type" in flows_df.columns else []
            )
    else:
        # No flow_partition, use 'type' column
        type_values = (
            sorted(flows_df["type"].unique()) if "type" in flows_df.columns else []
        )

    # Include "_" (catch-all partition label) and "*" (no partition) since
    # both implementations generate these as edge types and they need
    # consistent colors
    type_values = list(type_values)
    for extra in ["_", "*"]:
        if extra not in type_values:
            type_values.append(extra)

    # Create deterministic color mapping
    colors = Pastel1_8.hex_colors
    palette = {}
    for i, value in enumerate(type_values):
        palette[value] = colors[i % len(colors)]

    return palette


# ============================================================================
# Property-based test
# ============================================================================


@settings(print_blob=True, deadline=5000)
@given(fst.sankey_definitions(), st.data())
def test_general_equivalence(sdd, data):
    """Test equivalence on randomly generated, potentially messy scenarios.

    This test explores the full input space, including edge cases like:
    - Empty bundles (no matching flows)
    - Orphan flows (don't match any bundle)
    - Self-loops
    - Complex partition/waypoint combinations
    - Minimal vs maximal scenarios
    """
    dataset = data.draw(fst.datasets(sdd))

    # Create explicit palette to ensure consistent colors between implementations
    # Default link_color is CategoricalScale('type'), so we need to map flow types
    palette = _create_explicit_palette(sdd, dataset)

    old_result = weave(sdd, dataset, palette=palette)
    new_result = weave_compiled(sdd, dataset, palette=palette)

    sankey_data_equivalent(new_result, old_result)


# =============================================================================
# Property-based tests for bundle routing invariants
# =============================================================================


@settings(print_blob=True, deadline=5000, max_examples=300)
@given(fst.sankey_definitions(), st.data())
def test_routing_invariants(sdd, data):
    """Test that bundle routing matches the dataset.apply_view() implementation.

    For every flow routed, if it matches bundle(s) then the flow
    should appear in the bundle_flows mapping for those bundles.
    Conversely, if it doesn't match then the flow should not
    appear in any bundle_flows values.

    Limitations: since global filters are added later, they are
    not tested here.

    """
    # Currently global filters are added later, so avoid any
    # examples that include them for testing here
    assume(not sdd.flow_selection)

    dataset = data.draw(fst.datasets(sdd))

    # Reference result from old implementation
    # Calculate the view graph (adding dummy nodes)
    GV = view_graph(sdd)
    new_waypoints, new_bundles = elsewhere_bundles(sdd)
    GV2 = augment(GV, new_waypoints, new_bundles)

    bundles2: dict[str | int, Bundle] = dict(sdd.bundles, **new_bundles)
    # bundles2 = sdd.bundles

    bundle_flows, unused_flows = dataset.apply_view(
        sdd.nodes, bundles2, sdd.flow_selection
    )

    # Build the candidate tree
    selection_rules = build_selection_rules(bundles2, sdd.nodes, None)
    selection_tree = build_tree(selection_rules)

    # Test routing of each row for each bundle
    bundle_flows_routed = {}

    def _add_row(row, bundle_id):
        if bundle_id not in bundle_flows_routed:
            bundle_flows_routed[bundle_id] = []
        bundle_flows_routed[bundle_id].append(row.to_dict())

    unrouted_flows = []
    count_single_match = 0
    count_pair_match = 0
    for i, row in dataset._table.iterrows():
        m = selection_tree.evaluate(row)
        if m:
            if isinstance(m, SingleBundleMatch):
                _add_row(row, m.bundle_id)
                count_single_match += 1
            elif isinstance(m, ElsewhereBundlePairMatch):
                _add_row(row, m.from_elsewhere_bundle_id)
                _add_row(row, m.to_elsewhere_bundle_id)
                count_pair_match += 1
            else:
                assert False
        else:
            unrouted_flows.append(row.to_dict())

    for bundle_id, flows in bundle_flows.items():
        note(f"Flows for bundle {bundle_id}:\n{flows}")
    bundle_flows_dicts = {
        k: flows.to_dict("records")
        for k, flows in bundle_flows.items()
        if len(flows) > 0
    }

    unused_flows = {i: row.to_dict() for i, row in dataset._table.iterrows()}
    for k, flows in bundle_flows.items():
        for i, row in flows.iterrows():
            if i in unused_flows:
                del unused_flows[i]

    event("bundle_flows_length", payload=len(bundle_flows_dicts))
    event("unused_flows_length", payload=len(unused_flows))
    event("count_single_match", payload=count_single_match)
    event("count_pair_match", payload=count_pair_match)

    assert bundle_flows_routed == bundle_flows_dicts

    assert unrouted_flows == list(unused_flows.values())

    # flows_tested = set()

    # # Invariant 1: Each row that the old implementation assigns to a bundle should match
    # for bundle_id, rows in bundle_flows.items():
    #     for i, row in rows.iterrows():
    #         flows_tested.add(i)
    #         leaf = route_row_through_candidate_tree(candidate_tree, row)
    #         candidates = leaf.candidates
    #         assert bundle_id in candidates, f"bundle {bundle_id} has flow routed to {candidates!r}\n{row}"

    # # Invariant 2: Rows that didn't appear in the bundle_flows assignment should not match
    # for i, row in dataset._table.iterrows():
    #     if i in flows_tested:
    #         continue
    #     leaf = route_row_through_candidate_tree(candidate_tree, row)
    #     candidates = leaf.candidates
    #     assert len(candidates) == 0, f"row not in bundle_flows was routed to {candidates!r}\n{row}"
