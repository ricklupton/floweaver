"""Compile a SankeyDefinition into a WeaverSpec with routing tree.

This module implements the compile() function that transforms a high-level
SankeyDefinition into a low-level WeaverSpec that uses decision trees for
efficient flow routing.

The compilation process:
1. Expand ProcessGroups to explicit process ID sets
2. Collect explicit values for branch points
3. Build bundle tree (two-pass: non-Elsewhere, then Elsewhere)
4. Attach partition trees for bundles with groupby
5. Generate EdgeSpec objects for visual elements
"""

from ..sankey_definition import (
    SankeyDefinition,
    ProcessGroup,
)
from ..augment_view_graph import augment, elsewhere_bundles
from ..view_graph import view_graph
from ..color_scales import CategoricalScale, QuantitativeScale
from .combined_router import build_router
from .spec import (
    WeaverSpec,
    NodeSpec,
    GroupSpec,
    BundleSpec,
    EdgeSpec as EdgeSpec,
    MeasureSpec,
    DisplaySpec,
    CategoricalColorSpec,
    QuantitativeColorSpec,
)
from .execute import execute_weave as execute_weave


def compile_sankey_definition(
    sankey_definition: SankeyDefinition,
    measures="value",
    link_width=None,
    link_color=None,
    palette=None,
    add_elsewhere_waypoints=True,
    dimension_tables=None,
):
    """Compile a SankeyDefinition into a WeaverSpec with routing tree.

    This pre-expands all partitions and builds a decision tree for efficient
    flow routing at execution time.

    Parameters
    ----------
    sankey_definition : SankeyDefinition
        The high-level definition of the Sankey diagram.
    measures : str, list, or dict
        Measures to aggregate.
    link_width : str, optional
        Measure name to use for link width.
    link_color : str or ColorScale, optional
        Color scale for links.
    palette : str or list, optional
        Color palette.
    add_elsewhere_waypoints : bool
        Whether to add waypoints for elsewhere flows.
    dimension_tables: dict
        Dimension tables for resolving query strings.

    Returns
    -------
    WeaverSpec
        The compiled spec with routing tree.
    """
    # Calculate the view graph
    GV = view_graph(sankey_definition)

    # Add implicit elsewhere bundles
    new_waypoints, new_bundles = elsewhere_bundles(
        sankey_definition, add_elsewhere_waypoints
    )
    GV2 = augment(GV, new_waypoints, new_bundles)

    # Merge bundles and nodes
    all_bundles = dict(sankey_definition.bundles, **new_bundles)
    all_nodes = dict(sankey_definition.nodes, **new_waypoints)

    # Normalize measures
    measure_specs = _normalize_measures(measures)

    # Default link width
    if link_width is None:
        link_width = measure_specs[0].column

    # Expand nodes and ordering, based on partitions
    nodes, groups = _expand_nodes(GV2, sankey_definition)
    ordering = _expand_ordering(GV2)

    # Create bundle specs
    bundle_specs = _create_bundle_specs(all_bundles)

    # Build routing tree for selections and partitions
    dim_process = dimension_tables.get("process") if dimension_tables else None

    tree, edge_specs = build_router(
        GV2,
        all_bundles,
        all_nodes,
        sankey_definition.flow_partition,
        sankey_definition.time_partition,
        dim_process,
    )

    # Resolve color specification
    color_spec = _resolve_color_spec(link_color, palette, edge_specs)

    # Create display spec
    display = DisplaySpec(link_width=link_width, link_color=color_spec)

    return WeaverSpec(
        version="2.0",  # New version with routing tree
        nodes=nodes,
        groups=groups,
        bundles=bundle_specs,
        ordering=ordering,
        edges=edge_specs,
        measures=measure_specs,
        display=display,
        routing_tree=tree,
    )


# =============================================================================
# Helpers
# =============================================================================


def _normalize_measures(measures):
    """Normalize measures to list of MeasureSpec objects."""
    if isinstance(measures, str):
        return [MeasureSpec(column=measures, aggregation="sum")]
    elif isinstance(measures, list):
        return [MeasureSpec(column=m, aggregation="sum") for m in measures]
    elif isinstance(measures, dict):
        return [MeasureSpec(column=k, aggregation=v) for k, v in measures.items()]
    elif callable(measures):
        raise ValueError("callable measures not supported for compilation")
    else:
        raise ValueError("measures must be str, list, dict or callable")


def _expand_nodes(view_graph, sankey_definition):
    """Expand view graph nodes into NodeSpecs with partition expansion."""
    nodes = {}
    groups = []

    for u in view_graph.nodes:
        attr = view_graph.nodes[u]
        node = attr["node"]
        partition = node.partition
        group_nodes = []

        for node_id, label in _nodes_from_partition(u, partition):
            if partition is None:
                title = u if node.title is None else node.title
            else:
                title = label

            node_type = "process" if isinstance(node, ProcessGroup) else "group"
            style = node_type
            hidden = label == "_"

            nodes[node_id] = NodeSpec(
                title=title,
                type=node_type,
                group=u,
                style=style,
                direction=node.direction,
                hidden=hidden,
            )
            group_nodes.append(node_id)

        # Group title: use explicit title if set, otherwise empty string
        # (matching results_graph.py behavior: node.title or '')
        group_title = node.title or ""

        groups.append(
            GroupSpec(
                id=u,
                title=group_title,
                nodes=group_nodes,
            )
        )

    return nodes, groups


def _nodes_from_partition(u, partition):
    """Generate expanded node IDs from a partition."""
    if partition is None:
        return [("{}^*".format(u), "*")]
    else:
        return [("{}^{}".format(u, value), value) for value in partition.labels + ["_"]]


def _expand_ordering(view_graph):
    """Expand ordering to use expanded node IDs."""
    layers = []
    for bands in view_graph.ordering.layers:
        expanded_bands = []
        for band in bands:
            expanded_band = []
            for u in band:
                attr = view_graph.nodes[u]
                node = attr["node"]
                partition = node.partition
                for node_id, _ in _nodes_from_partition(u, partition):
                    expanded_band.append(node_id)
            expanded_bands.append(expanded_band)
        layers.append(expanded_bands)
    return layers


def _create_bundle_specs(bundles):
    """Create BundleSpec objects for provenance tracking."""
    bundle_specs = []
    for bundle_id, bundle in bundles.items():
        source = "Elsewhere" if bundle.from_elsewhere else bundle.source
        target = "Elsewhere" if bundle.to_elsewhere else bundle.target
        bundle_specs.append(
            BundleSpec(
                id=str(bundle_id),
                source=source,
                target=target,
            )
        )
    return bundle_specs


# def _wrap_tree_with_global_filters(bundle_tree, global_filters):
#     """Wrap the bundle tree with global flow_selection filters.

#     Creates a new root that filters on global attributes before routing to bundles.
#     Flows that don't match the global filters are blocked.

#     Parameters
#     ----------
#     bundle_tree : TreeNode
#         The existing bundle routing tree.
#     global_filters : dict
#         Global filter attributes and their values from flow_selection.
#         Format: {attr: [values]} for inclusion, {attr: {'exclude': [values]}} for exclusion.

#     Returns
#     -------
#     TreeNode
#         New root with global filter branches wrapping the bundle tree.
#     """
#     import copy

#     if not global_filters:
#         return bundle_tree

#     # Build a tree with one level per global filter attribute
#     # For simplicity, handle one filter at a time (could be extended for multiple)
#     attr, filter_spec = list(global_filters.items())[0]

#     # Create new root branching on the global filter attribute
#     new_root = TreeNode(attribute=attr, branches={})

#     # Check if this is an exclusion filter or inclusion filter
#     if isinstance(filter_spec, dict) and 'exclude' in filter_spec:
#         # Exclusion filter: block specific values, allow everything else
#         excluded_values = filter_spec['exclude']
#         for value in excluded_values:
#             new_root.branches[value] = TreeNode(state=LEAF_BLOCKED)
#         # Default branch goes to bundle tree
#         new_root.branches['default'] = bundle_tree
#     else:
#         # Inclusion filter: allow specific values, block everything else
#         included_values = filter_spec if isinstance(filter_spec, list) else []
#         for value in included_values:
#             new_root.branches[value] = copy.deepcopy(bundle_tree)
#         # Default branch blocks flows that don't match the global filter
#         new_root.branches['default'] = TreeNode(state=LEAF_BLOCKED)

#     return new_root


# =============================================================================
# Color resolution
# =============================================================================


def _resolve_color_spec(link_color, palette, edges):
    """Resolve color specification to a ColorSpec."""
    if link_color is None:
        link_color = CategoricalScale("type", palette=palette)
    elif isinstance(link_color, str):
        link_color = CategoricalScale(link_color, palette=palette)

    if isinstance(link_color, CategoricalScale):
        attr = link_color.attr

        if attr == "type":
            unique_values = sorted(set(e.type for e in edges if e.type != "_"))
        elif attr == "source":
            unique_values = sorted(set(e.source for e in edges if e.source is not None))
        elif attr == "target":
            unique_values = sorted(set(e.target for e in edges if e.target is not None))
        else:
            unique_values = []

        palette_colors = link_color.get_palette()
        lookup = dict(link_color.lookup) if link_color.lookup else {}

        # Handle empty palette case (no colors available)
        if palette_colors:
            next_idx = len(lookup) % len(palette_colors)
            for v in unique_values:
                if v not in lookup:
                    lookup[v] = palette_colors[next_idx % len(palette_colors)]
                    next_idx += 1

        default = link_color.default or "#cccccc"

        return CategoricalColorSpec(
            attribute=attr,
            lookup=lookup,
            default=default,
        )

    elif isinstance(link_color, QuantitativeScale):
        palette_cmap = link_color.palette
        n_colors = 9
        palette_colors = [
            _rgb2hex(palette_cmap(i / (n_colors - 1))) for i in range(n_colors)
        ]

        domain = link_color.domain or (0.0, 1.0)

        return QuantitativeColorSpec(
            attribute=link_color.attr,
            palette=palette_colors,
            domain=domain,
            intensity=link_color.intensity,
        )

    else:
        raise TypeError(
            "link_color must be a str, CategoricalScale, or QuantitativeScale"
        )


def _rgb2hex(rgb):
    """Convert RGB tuple to hex string."""
    import numpy as np

    if isinstance(rgb, str):
        return rgb
    else:
        return "#%02x%02x%02x" % tuple([int(np.round(val * 255)) for val in rgb[:3]])
