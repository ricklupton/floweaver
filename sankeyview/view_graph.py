import networkx as nx

from .utils import pairwise
from .bundle import Elsewhere
from .dummy_nodes import add_dummy_nodes


def view_graph(view_definition):
    G = nx.DiGraph()

    for k, node in view_definition.nodes.items():
        G.add_node(k, node=node)

    order = view_definition.copy().order
    bundles = sorted(view_definition.bundles, key=_bundle_order(view_definition))
    for bundle in bundles:
        G, order = _add_bundle_to_graph(G, order, bundle)

    return G, order


def _add_bundle_to_graph(G, order, bundle):
    nodes = (bundle.source,) + bundle.waypoints + (bundle.target,)
    for a, b in pairwise(nodes):
        if a is Elsewhere or b is Elsewhere:
            # No need to add waypoints to get to Elsewhere -- it is
            # everywhere!
            continue

        grouping = bundle.default_grouping or None
        G, order = add_dummy_nodes(G, order, a, b, bundle,
                                   node_kwargs=dict(title='', grouping=grouping))

    return G, order


def _bundle_order(view_definition):
    def keyfunc(bundle):
        if bundle.to_elsewhere or bundle.from_elsewhere:
            # bundle to elsewhere: last
            return (2, 0)

        r0 = view_definition.rank(bundle.source)
        r1 = view_definition.rank(bundle.target)
        if r1 > r0:
            # forwards bundles: shortest first
            return (0, r1 - r0)
        else:
            # backwards bundles: after forwards bundles, longest first
            return (1, r1 - r0)
    return keyfunc
