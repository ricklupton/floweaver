"""Functions to combine Bundle selections and partitions into decision trees."""

from __future__ import annotations
from typing import TypeVar, Callable, Optional, Mapping, Any, TypeAlias
import ast
from functools import reduce
from dataclasses import dataclass
from collections import defaultdict
import pandas as pd

from ..sankey_definition import SankeyDefinition, Bundle, ProcessGroup, Waypoint
from ..partition import Partition
from .spec import EdgeSpec
from .rules import Query, Rules, Includes, Excludes
from .selection_router import (
    build_selection_rules,
    BundleMatch,
    SingleBundleMatch,
    ElsewhereBundlePairMatch,
)
from .partition_router import (
    EdgeKey,
    build_segment_routing,
    merge_segment_routings,
)
from .tree import build_tree, Node

T = TypeVar("T")


@dataclass(frozen=True)
class TaggedEdgeKey:
    key: EdgeKey
    bundle_id: str


# Rules mapping data attributes to bundle/edgespec pairs
RoutingRules: TypeAlias = Rules[tuple[TaggedEdgeKey, ...]]

# Decision tree mapping data rows to edge-spec indices
RoutingTree: TypeAlias = Node[tuple[int, ...]]

SourceTargetPair: TypeAlias = tuple[str | None, str | None]


###################################################################
# Main functions
###################################################################


def build_routing_rules(
    view_graph,
    bundles: Mapping[Any, Bundle],
    nodes: Mapping[str, ProcessGroup | Waypoint],
    flow_partition: Partition | None,
    time_partition: Partition | None,
    dim_process: pd.DataFrame | None,
) -> RoutingRules:
    """Build routing rules from view graph."""

    # (1) Start with the selection rules mapping incoming data to bundle(s)
    selection_rules = build_selection_rules(bundles, nodes, dim_process)

    # (2) Determine partitions and granular routing to Sankey edges, for each bundle
    edge_routing, bundle_edges = _build_edge_routing_from_view_graph(
        view_graph, bundles, flow_partition, time_partition
    )

    bundle_partition_rules = _build_bundle_partition_routing(edge_routing, bundle_edges)

    # (3) Combine selection rules with the corresponding partition rules
    combined = selection_rules.expand(
        lambda bundle_match: _get_partition_rules_for_match(
            bundle_partition_rules, bundle_match
        )
    )

    return combined


def build_tree_from_rules(
    rules: RoutingRules,
) -> tuple[RoutingTree, list[EdgeSpec]]:
    # Extract edges and index
    indexed_rules, edge_specs = _extract_edge_specs(rules)

    # Build tree
    tree = build_tree(indexed_rules, default_value=())

    return tree, edge_specs


def build_router(
    view_graph,
    bundles: Mapping[Any, Bundle],
    nodes: Mapping[str, ProcessGroup | Waypoint],
    flow_partition: Partition | None,
    time_partition: Partition | None,
    dim_process: pd.DataFrame | None,
) -> tuple[RoutingTree, list[EdgeSpec]]:
    rules = build_routing_rules(
        view_graph, bundles, nodes, flow_partition, time_partition, dim_process
    )
    tree, edge_specs = build_tree_from_rules(rules)
    return tree, edge_specs


def route_flows(flows_df: pd.DataFrame, tree: RoutingTree) -> dict[int, list[int]]:
    """Route all flows to their edges, returning edge -> row indices mapping.

    Parameters
    ----------
    flows_df : DataFrame
        Flow data as a pandas DataFrame.
    tree : RoutingTree
        The compiled routing tree.

    Returns
    -------
    dict
        Mapping from edge_id to list of row indices that route to that edge.
    """
    edge_accumulators = {}

    # Build column name to index mapping for fast access
    # itertuples() returns (Index, col1, col2, ...) so column indices are offset by 1
    col_to_idx = {col: i + 1 for i, col in enumerate(flows_df.columns)}

    # Create a fast getter function that uses tuple indexing
    def get_value(row_tuple, attr_name):
        idx = col_to_idx.get(attr_name)
        if idx is not None:
            return row_tuple[idx]
        return None

    # Use itertuples() which is much faster than iterrows()
    # index=True means first element is the row index
    #
    # FIXME what if index is not integer?
    for row_tuple in flows_df.itertuples(index=True, name=None):
        idx = row_tuple[0]  # First element is the index

        # Route to find edge IDs
        edge_ids = tree.evaluate(row_tuple, get_value)

        # Add to accumulators
        for edge_id in edge_ids:
            if edge_id not in edge_accumulators:
                edge_accumulators[edge_id] = []
            edge_accumulators[edge_id].append(idx)

    return edge_accumulators


###################################################################
# Helpers
###################################################################


def _build_edge_routing_from_view_graph(
    view_graph,
    bundles: Mapping[Any, Bundle],
    flow_partition: Partition | None = None,
    time_partition: Partition | None = None,
) -> tuple[
    dict[SourceTargetPair, Rules[EdgeKey]],
    dict[Any, list[SourceTargetPair]],
]:
    """Extract per-edge partition routing and per-bundle edge chains from a view graph.

    Returns
    -------
    edge_routing : dict
        Mapping from (source, target) to partition routing rules.
    bundle_edges : dict
        Mapping from bundle_id to ordered list of (source, target) edge keys.
    """
    edge_routing: dict[SourceTargetPair, Rules[EdgeKey]] = {}
    bundle_edges_unordered: dict[Any, list[SourceTargetPair]] = defaultdict(list)

    # Regular edges from the view graph
    for v, w, data in view_graph.edges(data=True):
        key = (v, w)
        if key not in edge_routing:
            v_node = view_graph.nodes[v]["node"]
            w_node = view_graph.nodes[w]["node"]
            edge_fp = data.get("flow_partition") or flow_partition
            edge_routing[key] = build_segment_routing(
                source_node=v,
                target_node=w,
                source_partition=v_node.partition,
                target_partition=w_node.partition,
                material_partition=edge_fp,
                time_partition=time_partition,
            )
        for bid in data["bundles"]:
            bundle_edges_unordered[bid].append(key)

    # Elsewhere stubs (bundles without waypoints, stored on nodes)
    for u, data in view_graph.nodes(data=True):
        node = data["node"]
        for bid in data.get("to_elsewhere_bundles", []):
            bundle = bundles[bid]
            key = (u, None)
            if key not in edge_routing:
                edge_routing[key] = build_segment_routing(
                    source_node=u,
                    target_node=None,
                    source_partition=node.partition,
                    target_partition=None,
                )
            bundle_edges_unordered[bid] = [key]

        for bid in data.get("from_elsewhere_bundles", []):
            bundle = bundles[bid]
            key = (None, u)
            if key not in edge_routing:
                edge_routing[key] = build_segment_routing(
                    source_node=None,
                    target_node=u,
                    source_partition=None,
                    target_partition=node.partition,
                )
            bundle_edges_unordered[bid] = [key]

    # Order each bundle's edges into a chain
    bundle_edges: dict[Any, list[SourceTargetPair]] = {}
    for bid, edges in bundle_edges_unordered.items():
        if len(edges) <= 1:
            bundle_edges[bid] = edges
        else:
            bundle_edges[bid] = _order_edge_chain(edges)

    return edge_routing, bundle_edges


def _order_edge_chain(
    edges: list[SourceTargetPair],
) -> list[SourceTargetPair]:
    """Order a list of (source, target) edges into a linear chain."""
    by_source = {v: (v, w) for v, w in edges}
    targets = {w for _, w in edges}
    sources = {v for v, _ in edges}
    start = (sources - targets).pop()

    ordered = []
    current = start
    while current in by_source:
        edge = by_source[current]
        ordered.append(edge)
        current = edge[1]
    return ordered


def _build_bundle_partition_routing(
    edge_routing: dict[tuple[str | None, str | None], Rules[EdgeKey]],
    bundle_edges: dict[Any, list[tuple[str | None, str | None]]],
) -> dict[Any, Rules[tuple[TaggedEdgeKey, ...]]]:
    """Build bundle partition rules from pre-computed per-edge routing.

    Parameters
    ----------
    edge_routing : dict
        Mapping from (source, target) edge key to partition routing rules.
        Keys use None for elsewhere endpoints, e.g. (node_id, None).
    bundle_edges : dict
        Mapping from bundle_id to ordered list of (source, target) edge keys.
    """
    bundle_partition_rules: dict[Any, Rules[tuple[EdgeKey]]] = {}
    for bundle_id, edges in bundle_edges.items():
        segment_rules = [edge_routing[e] for e in edges]
        bundle_partition_rules[bundle_id] = merge_segment_routings(*segment_rules)

    # Associate the bundle ID with the matching edge keys
    bundle_partition_rules_tagged = {
        bundle_id: rules.map(
            lambda keys: tuple(TaggedEdgeKey(key, bundle_id) for key in keys)
        )
        for bundle_id, rules in bundle_partition_rules.items()
    }

    return bundle_partition_rules_tagged


def _get_partition_rules_for_match(
    bundle_partition_rules: dict[str, Rules[tuple[TaggedEdgeKey, ...]]],
    bundle_match: BundleMatch | None,
) -> Rules[tuple[TaggedEdgeKey, ...]]:
    """Combine selection and partition rules."""
    match bundle_match:
        case SingleBundleMatch(bundle_id):
            return bundle_partition_rules[bundle_id]

        case ElsewhereBundlePairMatch(from_elsewhere_id, to_elsewhere_id):
            from_rules = bundle_partition_rules[from_elsewhere_id]
            to_rules = bundle_partition_rules[to_elsewhere_id]
            return from_rules.expand_product(to_rules, lambda a, b: a + b)

        case None:
            return Rules([])

    raise ValueError("Expected BundleMatch or None")


def _extract_edge_specs(
    routing_rules: RoutingRules,
) -> tuple[Rules[tuple[int, ...]], list[EdgeSpec]]:
    """
    Extract unique edges and replace TaggedEdgeKeys with indices.

    Edges are deduplicated by EdgeKey (not bundle), so multiple bundles
    sharing a segment will share the same edge.

    Returns:
        - Rules with edge indices instead of EdgeKeys
        - List of EdgeSpecs (index in list = edge id)
    """
    # First pass: collect all bundle_ids per EdgeKey
    edge_to_bundles: dict[EdgeKey, set[str]] = {}

    for _, tagged_edges in routing_rules:
        for tagged in tagged_edges:
            if tagged.key not in edge_to_bundles:
                edge_to_bundles[tagged.key] = set()
            edge_to_bundles[tagged.key].add(tagged.bundle_id)

    # Second pass: build EdgeSpecs and index mapping
    edge_to_index: dict[EdgeKey, int] = {}
    edge_specs: list[EdgeSpec] = []

    for key, bundle_ids in edge_to_bundles.items():
        edge_to_index[key] = len(edge_specs)
        edge_specs.append(
            EdgeSpec(
                source=key.s,
                target=key.t,
                type=key.m,
                time=key.z,
                bundle_ids=sorted(bundle_ids),
            )
        )

    # Replace edges with indices (now keyed by EdgeKey, not TaggedEdgeKey)
    indexed_rules: Rules[tuple[int, ...]] = routing_rules.map(
        lambda tagged_keys: tuple(edge_to_index[tagged.key] for tagged in tagged_keys)
    )

    return indexed_rules, edge_specs
