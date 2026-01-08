"""Test to identify overlapping flow matches in compiled specs.

This test reproduces an issue where the same flow from the dataset is matched by
multiple links, which should never happen.

This occurred when using query-based ProcessGroup selections (e.g., 'type ==
"source"'), the implicit elsewhere bundles are not properly excluding flows that
are already covered by explicit bundles. This causes flows to be counted
multiple times.

"""

import pytest
import pandas as pd
import os

from floweaver import (
    SankeyDefinition,
    ProcessGroup,
    Waypoint,
    Bundle,
    Dataset,
    Elsewhere,
)
from floweaver.weave import weave_compiled


def check_original_flow_overlaps(result):
    """Check if any original flow appears in multiple links.

    Returns a dict mapping flow indices to lists of link indices that use them.
    """
    flow_to_links = {}

    for link_idx, link in enumerate(result.links):
        for flow_idx in link.original_flows:
            if flow_idx not in flow_to_links:
                flow_to_links[flow_idx] = []
            flow_to_links[flow_idx].append(link_idx)

    # Find overlaps
    overlaps = {flow_idx: link_indices
                for flow_idx, link_indices in flow_to_links.items()
                if len(link_indices) > 1}

    return overlaps


def test_minimal_filter_overlap():
    """Minimal test case: flow matched by explicit bundle AND implicit elsewhere bundle."""
    # Create minimal dataset
    flows = pd.DataFrame.from_records(
        [
            ('a1', 'b1', 'm', 3),
            ('a1', 'b2', 'm', 2),
        ],
        columns=('source', 'target', 'material', 'value'))
    dataset = Dataset(flows)

    # Simple two-node definition
    nodes = {
        'a': ProcessGroup(['a1']),
        'b': ProcessGroup(['b1', 'b2']),
    }

    bundles = [
        Bundle('a', 'b'),
    ]

    ordering = [['a'], ['b']]

    sdd = SankeyDefinition(nodes, bundles, ordering)

    # Run weave_compiled with elsewhere waypoints enabled
    result = weave_compiled(sdd, dataset, add_elsewhere_waypoints=True)

    # Check for overlaps
    overlaps = check_original_flow_overlaps(result)

    # Print diagnostic info
    if overlaps:
        print("\n=== OVERLAPPING FLOWS DETECTED ===")
        for flow_idx, link_indices in overlaps.items():
            flow = dataset._flows.loc[flow_idx]
            print(f"\nFlow {flow_idx}: {flow['source']} -> {flow['target']} " +
                  f"(material={flow.get('material', 'N/A')}, value={flow.get('value', 'N/A')})")
            print(f"  Matched by {len(link_indices)} links:")
            for link_idx in link_indices:
                link = result.links[link_idx]
                print(f"    Link {link_idx}: {link.source} -> {link.target} " +
                      f"(type={link.type})")

    # Assert no overlaps
    assert len(overlaps) == 0, \
        f"Found {len(overlaps)} flows matched by multiple links"


def test_query_selection_filter_overlap():
    """Test with query-based selection like in fruit example.

    This test verifies that implicit elsewhere bundles correctly exclude flows
    that are already covered by explicit bundles when using query-based selections.

    Each flow should be matched by exactly ONE link:
    - Flows from a1->b1 and a1->b2 should only match the explicit Bundle('a', 'b')
    - They should NOT match implicit elsewhere bundles
    """
    # Create dataset with dimension table
    flows = pd.DataFrame.from_records(
        [
            ('a1', 'b1', 'm', 3),
            ('a1', 'b2', 'm', 2),
        ],
        columns=('source', 'target', 'material', 'value'))

    dim_process = pd.DataFrame({
        'id': ['a1', 'b1', 'b2'],
        'type': ['source', 'dest', 'dest'],
    }).set_index('id')

    dataset = Dataset(flows, dim_process=dim_process)

    # Use query-based selection
    nodes = {
        'a': ProcessGroup('type == "source"'),
        'b': ProcessGroup('type == "dest"'),
    }

    bundles = [
        Bundle('a', 'b'),
    ]

    ordering = [['a'], ['b']]

    sdd = SankeyDefinition(nodes, bundles, ordering)

    # Build dimension_tables dict
    dimension_tables = {'process': dim_process}

    # Run weave_compiled with elsewhere waypoints enabled
    result = weave_compiled(sdd, dataset, dimension_tables=dimension_tables,
                           add_elsewhere_waypoints=True)

    # Check for overlaps
    overlaps = check_original_flow_overlaps(result)

    # Print diagnostic info
    if overlaps:
        print("\n=== OVERLAPPING FLOWS DETECTED ===")
        for flow_idx, link_indices in overlaps.items():
            flow = dataset._flows.loc[flow_idx]
            print(f"\nFlow {flow_idx}: {flow['source']} -> {flow['target']} " +
                  f"(material={flow.get('material', 'N/A')}, value={flow.get('value', 'N/A')})")
            print(f"  Matched by {len(link_indices)} links:")
            for link_idx in link_indices:
                link = result.links[link_idx]
                print(f"    Link {link_idx}: {link.source} -> {link.target} " +
                      f"(type={link.type})")

    # Assert no overlaps
    assert len(overlaps) == 0, \
        f"Found {len(overlaps)} flows matched by multiple links"
