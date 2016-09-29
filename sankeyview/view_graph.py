from .layered_graph import LayeredGraph
from .utils import pairwise
from .view_definition import Elsewhere
from .dummy_nodes import add_dummy_nodes


def view_graph(view_definition):
    G = LayeredGraph()

    for k, process_group in view_definition.process_groups.items():
        G.add_node(k, node=process_group)

    for k, waypoint in view_definition.waypoints.items():
        G.add_node(k, node=waypoint)

    G.ordering = view_definition.ordering
    implicit_waypoints = {}
    G = _add_bundles_to_graph(G, view_definition.bundles,
                              _bundle_order(view_definition),
                              implicit_waypoints)

    return G, implicit_waypoints


def _add_bundles_to_graph(G, bundles, sort_key, implicit_waypoints):
    for k, bundle in sorted(bundles.items(), key=sort_key):
        nodes = (bundle.source,) + bundle.waypoints + (bundle.target,)
        for iw, (a, b) in enumerate(pairwise(nodes)):
            if a is Elsewhere or b is Elsewhere:
                # No need to add waypoints to get to Elsewhere -- it is
                # everywhere!
                continue

            partition = bundle.default_partition or None
            G = add_dummy_nodes(G, a, b, k, iw, implicit_waypoints,
                                node_kwargs=dict(title='', partition=partition))

    # check flow partitions are compatible
    for v, w, data in G.edges(data=True):
        flow_partitions = list({bundles[b].flow_partition for b in data['bundles']})
        if len(flow_partitions) > 1:
            raise ValueError('Multiple flow partitions in bundles: {}'
                             .format(', '.join(str(b) for b in data['bundles'])))
        if flow_partitions[0]:
            data['flow_partition'] = flow_partitions[0]

    return G


def _bundle_order(view_definition):
    def keyfunc(item):
        k, bundle = item
        if bundle.to_elsewhere or bundle.from_elsewhere:
            # bundle to elsewhere: last
            return (2, 0)

        r0, _, _ = view_definition.ordering.indices(bundle.source)
        r1, _, _ = view_definition.ordering.indices(bundle.target)
        if r1 > r0:
            # forwards bundles: shortest first
            return (0, r1 - r0)
        else:
            # backwards bundles: after forwards bundles, longest first
            return (1, r1 - r0)
    return keyfunc
