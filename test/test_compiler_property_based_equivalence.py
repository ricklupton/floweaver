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

import numpy as np
from hypothesis import (
    given,
    strategies as st,
    settings,
    assume,
    event,
    note,
)

from floweaver import (
    Bundle,
)
from floweaver.compiler.tree import build_tree
from floweaver.compiler.selection_router import build_selection_rules
from floweaver.compiler.combined_router import (
    SingleBundleMatch,
    ElsewhereBundlePairMatch,
)
from floweaver.augment_view_graph import elsewhere_bundles
from floweaver.weave import weave, weave_compiled

import hypothesis_strategies as fst
from helpers import assert_sankey_data_equivalent


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

    assert_sankey_data_equivalent(new_result, old_result, allow_known_improvements=True)


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
    new_waypoints, new_bundles = elsewhere_bundles(sdd)
    bundles2: dict[str | int, Bundle] = dict(sdd.bundles, **new_bundles)

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
