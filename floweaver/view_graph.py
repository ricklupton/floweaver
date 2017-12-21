from .layered_graph import LayeredGraph
from .utils import pairwise
from .sankey_definition import Elsewhere
from .dummy_nodes import add_dummy_nodes


def view_graph(sankey_definition):
    G = LayeredGraph()

    for k, node in sankey_definition.nodes.items():
        G.add_node(k, node=node)

    G.ordering = sankey_definition.ordering
    G = _add_bundles_to_graph(G, sankey_definition.bundles,
                              _bundle_order(sankey_definition))

    return G


def _add_bundles_to_graph(G, bundles, sort_key):
    for k, bundle in sorted(bundles.items(), key=sort_key):
        nodes = (bundle.source, ) + bundle.waypoints + (bundle.target, )
        for iw, (a, b) in enumerate(pairwise(nodes)):
            # No need to add waypoints to get to Elsewhere -- it is
            # everywhere!
            if a is not Elsewhere and b is not Elsewhere:
                G = add_dummy_nodes(G, a, b, k, iw, _dummy_kw(bundle))

    # check flow partitions are compatible
    for v, w, data in G.edges(data=True):
        flow_partitions = list({bundles[b].flow_partition
                                for b in data['bundles']})
        if len(flow_partitions) > 1:
            raise ValueError('Multiple flow partitions in bundles: {}'.format(
                ', '.join(str(b) for b in data['bundles'])))
        if flow_partitions[0]:
            data['flow_partition'] = flow_partitions[0]

    return G


def _dummy_kw(bundle):
    return dict(title='', partition=bundle.default_partition or None)


def _bundle_order(sankey_definition):
    def keyfunc(item):
        k, bundle = item
        if bundle.to_elsewhere or bundle.from_elsewhere:
            # bundle to elsewhere: last
            return (2, 0)

        r0, _, _ = sankey_definition.ordering.indices(bundle.source)
        r1, _, _ = sankey_definition.ordering.indices(bundle.target)
        if r1 > r0:
            # forwards bundles: shortest first
            return (0, r1 - r0)
        else:
            # backwards bundles: after forwards bundles, longest first
            return (1, r1 - r0)

    return keyfunc
