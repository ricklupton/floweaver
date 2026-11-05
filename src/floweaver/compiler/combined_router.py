"""Functions to combine Bundle selections and partitions into a flow router.

Routing happens in two stages (see :class:`TwoStageRouter`):

1. The selection tree routes each data row to the Bundle (or pair of Elsewhere
   Bundles) it belongs to.
2. Each Bundle's tree routes the row to the edges of that Bundle, according to
   the partitions of the nodes it passes through and the flow/time partitions.
"""

from __future__ import annotations
from typing import TypeVar, Mapping, Any, TypeAlias
from collections import defaultdict
import pandas as pd

from ..sankey_definition import (
    Bundle,
    BundleID,
    ProcessGroup,
    Waypoint,
)
from ..partition import Partition
from .spec import EdgeSpec
from .rules import Rules, intersect_queries, is_satisfiable
from .selection_router import (
    build_selection_rules,
    build_bundle_selection_query,
    BundleMatch,
    SingleBundleMatch,
    ElsewhereBundlePairMatch,
)
from .partition_router import (
    EdgeKey,
    build_segment_routing,
    merge_segment_routings,
    partition_value_sets,
)
from .tree import build_tree, Node, TwoStageRouter
from .value_classes import ValueClasses, compute_value_classes

T = TypeVar("T")

# Decision tree mapping data rows to edge-spec indices (the single combined
# tree produced by earlier versions of the compiler)
RoutingTree: TypeAlias = Node[tuple[int, ...]]

# Anything that routes data rows to edge-spec indices
Router: TypeAlias = RoutingTree | TwoStageRouter

SourceTargetPair: TypeAlias = tuple[str | None, str | None]


###################################################################
# Main functions
###################################################################


def build_bundle_routing_rules(
    view_graph,
    bundles: Mapping[BundleID, Bundle],
    nodes: Mapping[str, ProcessGroup | Waypoint],
    flow_partition: Partition | None,
    time_partition: Partition | None,
    dim_process: pd.DataFrame | None,
    value_classes: ValueClasses | None = None,
) -> dict[BundleID, Rules[tuple[EdgeKey, ...]]]:
    """Build rules routing data rows to edges, for each Bundle.

    The rules for each Bundle assume the row has already been selected for that
    Bundle; rules that cannot match any row selected by the Bundle are dropped.

    If `value_classes` is given, rules are expressed in terms of value classes
    rather than values.
    """
    edge_routing, bundle_edges = _build_edge_routing_from_view_graph(
        view_graph, bundles, flow_partition, time_partition, value_classes
    )

    result = {}
    for bundle_id, edges in bundle_edges.items():
        rules = merge_segment_routings(*[edge_routing[e] for e in edges])
        selection = build_bundle_selection_query(bundles[bundle_id], nodes, dim_process)
        if value_classes is not None:
            selection = value_classes.classify_query(selection)
        result[bundle_id] = Rules(
            [
                (query, keys)
                for query, keys in rules
                if is_satisfiable(intersect_queries(query, selection))
            ]
        )
    return result


def build_router(
    view_graph,
    bundles: Mapping[BundleID, Bundle],
    nodes: Mapping[str, ProcessGroup | Waypoint],
    flow_partition: Partition | None,
    time_partition: Partition | None,
    dim_process: pd.DataFrame | None,
    use_value_classes: bool = True,
) -> tuple[TwoStageRouter, list[EdgeSpec]]:
    """Build the router and list of edges for a view graph.

    By default, rules and trees are built over classes of values that the
    rules treat identically (see :mod:`.value_classes`), which keeps them
    small. Setting `use_value_classes` to False builds them over the values
    themselves; the routing is identical, but can be much slower to compile.
    """
    value_classes = (
        compute_value_classes(
            _routing_value_sets(
                view_graph, bundles, nodes, flow_partition, time_partition, dim_process
            )
        )
        if use_value_classes
        else None
    )

    # Stage 1: route data to bundle(s)
    selection_rules = build_selection_rules(bundles, nodes, dim_process, value_classes)
    selection_tree = build_tree(
        selection_rules.filter(lambda match: match is not None).map(
            _bundle_ids_for_match
        ),
        default_value=(),
    )

    # Stage 2: route data within each bundle to edges
    bundle_rules = build_bundle_routing_rules(
        view_graph,
        bundles,
        nodes,
        flow_partition,
        time_partition,
        dim_process,
        value_classes,
    )
    indexed_rules, edge_specs = _extract_edge_specs(bundle_rules)
    bundle_trees = {
        str(bundle_id): build_tree(rules, default_value=())
        for bundle_id, rules in indexed_rules.items()
    }

    return TwoStageRouter(selection_tree, bundle_trees, value_classes), edge_specs


def route_flows(flows_df: pd.DataFrame, tree: Router) -> dict[int, list[int]]:
    """Route all flows to their edges, returning edge -> row indices mapping.

    Parameters
    ----------
    flows_df : DataFrame
        Flow data as a pandas DataFrame.
    tree : TwoStageRouter or RoutingTree
        The compiled router.

    Returns
    -------
    dict
        Mapping from edge_id to list of row indices that route to that edge.
    """
    edge_accumulators = {}
    for idx, edge_ids in _iter_routed_rows(flows_df, tree):
        for edge_id in edge_ids:
            if edge_id not in edge_accumulators:
                edge_accumulators[edge_id] = []
            edge_accumulators[edge_id].append(idx)
    return edge_accumulators


def route_flow_paths(
    flows_df: pd.DataFrame, tree: Router
) -> dict[tuple[int, ...], list]:
    """Route all flows, returning path -> row indices mapping.

    Unlike :func:`route_flows`, this keeps the ordered tuple of edges that each
    flow passes through (its "path"). For a flow in a single Bundle, the path is
    the chain of edges from the Bundle's source to its target. For a flow
    matched by a pair of to-Elsewhere and from-Elsewhere Bundles, the path is
    the from-Elsewhere chain followed by the to-Elsewhere chain.

    Flows that are not routed to any edge are omitted.

    Parameters
    ----------
    flows_df : DataFrame
        Flow data as a pandas DataFrame.
    tree : TwoStageRouter or RoutingTree
        The compiled router.

    Returns
    -------
    dict
        Mapping from path (tuple of edge ids) to list of row indices.
    """
    paths: dict[tuple[int, ...], list] = {}
    for idx, edge_ids in _iter_routed_rows(flows_df, tree):
        if edge_ids:
            paths.setdefault(tuple(edge_ids), []).append(idx)
    return paths


def _iter_routed_rows(flows_df: pd.DataFrame, tree: Router):
    """Yield (row index, edge ids) for each row of `flows_df`."""
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
        yield row_tuple[0], tree.evaluate(row_tuple, get_value)


###################################################################
# Helpers
###################################################################


def _build_edge_routing_from_view_graph(
    view_graph,
    bundles: Mapping[BundleID, Bundle],
    flow_partition: Partition | None = None,
    time_partition: Partition | None = None,
    value_classes: ValueClasses | None = None,
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
                value_classes=value_classes,
            )
        for bid in data["bundles"]:
            bundle_edges_unordered[bid].append(key)

    # Elsewhere stubs (bundles without waypoints, stored on nodes)
    for u, data in view_graph.nodes(data=True):
        node = data["node"]
        for bid in data.get("to_elsewhere_bundles", []):
            key = (u, None)
            if key not in edge_routing:
                edge_routing[key] = build_segment_routing(
                    source_node=u,
                    target_node=None,
                    source_partition=node.partition,
                    target_partition=None,
                    value_classes=value_classes,
                )
            bundle_edges_unordered[bid] = [key]

        for bid in data.get("from_elsewhere_bundles", []):
            key = (None, u)
            if key not in edge_routing:
                edge_routing[key] = build_segment_routing(
                    source_node=None,
                    target_node=u,
                    source_partition=None,
                    target_partition=node.partition,
                    value_classes=value_classes,
                )
            bundle_edges_unordered[bid] = [key]

    # Order each bundle's edges into a chain
    bundle_edges: dict[Any, list[SourceTargetPair]] = {}
    for bid, edges in bundle_edges_unordered.items():
        if len(edges) <= 1:
            bundle_edges[bid] = edges
        else:
            bundle = bundles[bid]
            start = None if bundle.from_elsewhere else bundle.source
            bundle_edges[bid] = _order_edge_chain(edges, start)

    return edge_routing, bundle_edges


def _order_edge_chain(
    edges: list[SourceTargetPair],
    start: str | None = None,
) -> list[SourceTargetPair]:
    """Order a list of (source, target) edges into a linear chain.

    The chain starts at `start` if given (the Bundle's source). Otherwise it
    starts at the node which is the source of an edge but not the target of
    any, which is not well defined for a Bundle that returns to its own
    source, so `start` must be given for those.
    """
    by_source = {v: (v, w) for v, w in edges}
    if start is None:
        targets = {w for _, w in edges}
        sources = {v for v, _ in edges}
        (start,) = sources - targets

    ordered = []
    current = start
    # A Bundle from a node back to itself passes through its start twice, so
    # stop after visiting every edge rather than when the chain runs out.
    while len(ordered) < len(edges):
        edge = by_source[current]
        ordered.append(edge)
        current = edge[1]
    return ordered


def _routing_value_sets(
    view_graph,
    bundles: Mapping[BundleID, Bundle],
    nodes: Mapping[str, ProcessGroup | Waypoint],
    flow_partition: Partition | None,
    time_partition: Partition | None,
    dim_process: pd.DataFrame | None,
) -> dict[str, list[frozenset]]:
    """All the sets of values used by routing rules, for each attribute."""
    value_sets: dict[str, list[frozenset]] = defaultdict(list)

    def add(sets: Mapping[str, list[frozenset]]):
        for attr, values in sets.items():
            value_sets[attr].extend(values)

    # Bundle selections
    for bundle in bundles.values():
        query = build_bundle_selection_query(bundle, nodes, dim_process)
        add({attr: [constraint.values] for attr, constraint in query.items()})

    # Node partitions (which may apply on either side of an edge)
    for u in view_graph.nodes:
        add(
            partition_value_sets(
                view_graph.nodes[u]["node"].partition, ("source", "target")
            )
        )

    # Flow and time partitions
    for _, _, data in view_graph.edges(data=True):
        add(partition_value_sets(data.get("flow_partition")))
    add(partition_value_sets(flow_partition))
    add(partition_value_sets(time_partition))

    return value_sets


def _bundle_ids_for_match(bundle_match: BundleMatch) -> tuple[str, ...]:
    """Bundle ids (as strings) to route a row through, in path order."""
    match bundle_match:
        case SingleBundleMatch(bundle_id):
            return (str(bundle_id),)

        case ElsewhereBundlePairMatch(from_elsewhere_id, to_elsewhere_id):
            return (str(from_elsewhere_id), str(to_elsewhere_id))

    raise ValueError("Expected BundleMatch")


def _extract_edge_specs(
    bundle_rules: dict[BundleID, Rules[tuple[EdgeKey, ...]]],
) -> tuple[dict[BundleID, Rules[tuple[int, ...]]], list[EdgeSpec]]:
    """
    Extract unique edges and replace EdgeKeys with indices.

    Edges are deduplicated by EdgeKey, so multiple bundles sharing a segment
    will share the same edge.

    Returns:
        - Rules for each bundle with edge indices instead of EdgeKeys
        - List of EdgeSpecs (index in list = edge id)
    """
    # Collect all bundle_ids per EdgeKey
    edge_to_bundles: dict[EdgeKey, set[BundleID]] = {}
    for bundle_id, rules in bundle_rules.items():
        for _, keys in rules:
            for key in keys:
                edge_to_bundles.setdefault(key, set()).add(bundle_id)

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

    indexed_rules = {
        bundle_id: rules.map(lambda keys: tuple(edge_to_index[k] for k in keys))
        for bundle_id, rules in bundle_rules.items()
    }
    return indexed_rules, edge_specs
