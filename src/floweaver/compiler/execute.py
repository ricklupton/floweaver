"""Execute a WeaverSpec against flow data to produce SankeyData.

This module implements the execute_weave() function that takes a compiled
WeaverSpec and executes it against actual flow data (from a Dataset) to
produce SankeyData results.

The spec contains pre-expanded nodes and edges with explicit include/exclude
filters. The executor simply:
1. Filters flows according to each edge's filters
2. Aggregates measures for matching flows
3. Applies display styling (colors, widths)
4. Builds the SankeyData output
"""


from ..sankey_data import SankeyData, SankeyNode, SankeyLink
from ..ordering import Ordering
from .combined_router import route_flows
from .spec import (
    CategoricalColorSpec,
    QuantitativeColorSpec,
)


def execute_weave(spec, dataset):
    """Execute a WeaverSpec against flow data to produce SankeyData.

    Parameters
    ----------
    spec : WeaverSpec
        The compiled spec with routing tree.
    dataset : Dataset or DataFrame
        The flow data.

    Returns
    -------
    SankeyData
        The resulting Sankey diagram data with nodes and links.
    """
    # Get the flows table
    if hasattr(dataset, '_table'):
        flows = dataset._table
    else:
        flows = dataset

    return _execute_with_routing_tree(spec, flows, dataset)


def _execute_with_routing_tree(spec, flows, dataset):
    """Execute using the new routing tree system."""
    routing_tree = spec.routing_tree

    # Route all flows to edges
    edge_flow_map = route_flows(flows, routing_tree)

    # Aggregate flows for each edge
    links = []
    from_elsewhere = {}  # node_id -> list of links
    to_elsewhere = {}    # node_id -> list of links

    for edge_index, flow_indices in edge_flow_map.items():
        edge = spec.edges[edge_index]
        matching = flows.iloc[flow_indices]

        if len(matching) > 0:
            data = _aggregate(matching, spec.measures)
            link_width = data.get(spec.display.link_width, 0.0)
            color = _apply_color(edge, data, spec.display)
            title = _compute_title(edge, spec.bundles)

            link = SankeyLink(
                source=edge.source,
                target=edge.target,
                type=edge.type,
                time=edge.time,
                link_width=link_width,
                data=data,
                title=title,
                color=color,
                opacity=1.0,
                original_flows=flow_indices,
            )

            if edge.source is None:
                from_elsewhere.setdefault(edge.target, []).append(link)
            elif edge.target is None:
                to_elsewhere.setdefault(edge.source, []).append(link)
            else:
                links.append(link)

    # Build nodes with elsewhere links
    # Track nodes that appear in regular edges (degree > 0)
    nodes_in_regular_edges = set()
    for link in links:
        nodes_in_regular_edges.add(link.source)
        nodes_in_regular_edges.add(link.target)

    # Track all used nodes (including those with only elsewhere edges)
    used = set(nodes_in_regular_edges)
    used.update(from_elsewhere.keys())
    used.update(to_elsewhere.keys())

    nodes = []
    for node_id, node_spec in spec.nodes.items():
        if node_id in used:
            nodes.append(SankeyNode(
                id=node_id,
                title=node_spec.title,
                direction=node_spec.direction,
                hidden=node_spec.hidden,
                style=node_spec.style,
                from_elsewhere_links=from_elsewhere.get(node_id, []),
                to_elsewhere_links=to_elsewhere.get(node_id, []),
            ))

    # Build groups
    # Pass nodes_in_regular_edges to filter out nodes with only elsewhere edges
    # (matching old behavior where degree-0 nodes are filtered from groups)
    groups = _build_groups(spec.groups, spec.nodes, nodes_in_regular_edges)

    # Filter ordering
    ordering = _filter_ordering(spec.ordering, used)

    return SankeyData(
        nodes=nodes,
        links=links,
        groups=groups,
        ordering=ordering,
        dataset=dataset if hasattr(dataset, '_table') else None,
    )




def _aggregate(df, measures):
    """Aggregate flow data according to measure specifications.

    Parameters
    ----------
    df : DataFrame
        The matching flows.
    measures : list of MeasureSpec
        Measure specifications with column names and aggregation functions.

    Returns
    -------
    dict
        Aggregated values keyed by column name.
    """
    result = {}
    for m in measures:
        col = m.column
        if col not in df.columns:
            result[col] = 0.0
            continue

        if m.aggregation == 'sum':
            result[col] = df[col].sum()
        elif m.aggregation == 'mean':
            result[col] = df[col].mean()
        else:
            raise ValueError(f'Unknown aggregation: {m.aggregation}')

    return result


def _apply_color(edge, data, display_spec):
    """Compute the color for a link based on the display spec.

    Parameters
    ----------
    edge : EdgeSpec
        The edge specification.
    data : dict
        Aggregated measure values.
    display_spec : DisplaySpec
        Display configuration with color spec.

    Returns
    -------
    str
        Hex color string.
    """
    color_spec = display_spec.link_color

    if isinstance(color_spec, CategoricalColorSpec):
        attr = color_spec.attribute
        if attr == 'type':
            value = edge.type
        elif attr == 'source':
            value = edge.source
        elif attr == 'target':
            value = edge.target
        elif attr == 'time':
            value = edge.time
        else:
            # Assume it's a measure
            value = data.get(attr)

        return color_spec.lookup.get(str(value), color_spec.default)

    elif isinstance(color_spec, QuantitativeColorSpec):
        value = data.get(color_spec.attribute, 0.0)

        if color_spec.intensity is not None:
            intensity_value = data.get(color_spec.intensity, 1.0)
            if intensity_value != 0:
                value = value / intensity_value

        domain = color_spec.domain
        if domain[1] != domain[0]:
            normed = (value - domain[0]) / (domain[1] - domain[0])
        else:
            normed = 0.5

        # Clamp to [0, 1]
        normed = max(0.0, min(1.0, normed))

        return _interpolate_color(color_spec.palette, normed)

    else:
        return '#cccccc'


def _interpolate_color(palette, t):
    """Interpolate a color from a palette.

    Parameters
    ----------
    palette : list of str
        List of hex color strings.
    t : float
        Value in [0, 1] for interpolation.

    Returns
    -------
    str
        Hex color string.
    """
    if not palette:
        return '#cccccc'

    # Map t to palette index
    idx = t * (len(palette) - 1)
    lo = int(idx)
    hi = min(lo + 1, len(palette) - 1)

    if lo == hi:
        return palette[lo]

    # Linear interpolation between adjacent colors
    frac = idx - lo
    c_lo = _hex_to_rgb(palette[lo])
    c_hi = _hex_to_rgb(palette[hi])

    r = int(c_lo[0] + frac * (c_hi[0] - c_lo[0]))
    g = int(c_lo[1] + frac * (c_hi[1] - c_lo[1]))
    b = int(c_lo[2] + frac * (c_hi[2] - c_lo[2]))

    return f'#{r:02x}{g:02x}{b:02x}'


def _hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def _compute_title(edge, bundle_specs):
    """Compute link title from bundle provenance.

    Parameters
    ----------
    edge : EdgeSpec
        The edge specification.
    bundle_specs : list of BundleSpec
        Bundle specifications for provenance.

    Returns
    -------
    str
        Title string (typically the flow type).
    """
    # For now, just use the type as title
    # In future could incorporate bundle info
    return edge.type


def _build_groups(group_specs, node_specs, used_nodes):
    """Build groups in the format expected by SankeyData.

    Parameters
    ----------
    group_specs : list of GroupSpec
        Group specifications from the WeaverSpec.
    node_specs : dict
        Mapping of node IDs to NodeSpec objects.
    used_nodes : set
        Set of node IDs that are actually used.

    Returns
    -------
    list of dict
        Groups in SankeyData format.
    """
    groups = []
    for g in group_specs:
        # Filter to only include groups with nodes that are used
        nodes_in_group = [n for n in g.nodes if n in used_nodes]

        if len(nodes_in_group) == 0:
            # Skip empty groups
            continue

        # Determine group type from the first node's type
        # (all nodes in a group have the same type since they come from the same ProcessGroup/Waypoint)
        group_type = node_specs[nodes_in_group[0]].type

        # Only include groups with more than one node, or where the group
        # title is different from the node title
        # Logic from results_graph.py:99
        # Treat empty string as equivalent to None - use group id for comparison
        if len(nodes_in_group) == 1:
            node_title = node_specs[nodes_in_group[0]].title
            group_title = g.title if g.title else g.id
            include = (node_title != group_title)
        else:
            include = True

        if include:
            groups.append({
                'id': g.id,
                'title': g.title if g.title is not None else '',
                'type': group_type,
                'nodes': nodes_in_group,
            })
    return groups


def _filter_ordering(ordering, used_nodes):
    """Filter ordering to only include used nodes.

    Parameters
    ----------
    ordering : list of list of list of str
        The ordering from the spec.
    used_nodes : set
        Set of node IDs that are actually used.

    Returns
    -------
    Ordering
        Filtered ordering.
    """
    filtered = []
    for layer in ordering:
        filtered_layer = []
        for band in layer:
            filtered_band = [n for n in band if n in used_nodes]
            filtered_layer.append(filtered_band)
        if any(band for band in filtered_layer):
            filtered.append(filtered_layer)
    return Ordering(filtered)
