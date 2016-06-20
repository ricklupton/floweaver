import networkx as nx

from .node import Node
from .bundle import Bundle, Elsewhere
from .ordering import new_node_indices


def elsewhere_bundles(view_definition):
    # Build set of existing bundles to/from elsewhere
    has_to_elsewhere = set()
    has_from_elsewhere = set()
    for bundle in view_definition.bundles:
        assert not (bundle.source is Elsewhere and bundle.target is Elsewhere)
        if bundle.target is Elsewhere:
            if bundle.source in has_to_elsewhere:
                raise ValueError('duplicate bundles to elsewhere from {}'.format(bundle.source))
            has_to_elsewhere.add(bundle.source)
        if bundle.source is Elsewhere:
            if bundle.target in has_from_elsewhere:
                raise ValueError('duplicate bundles from elsewhere to {}'.format(bundle.target))
            has_from_elsewhere.add(bundle.target)

    # For each node, add new bundles to/from elsewhere if not already
    # existing. Each one should have a waypoint of rank +/- 1.
    R = len(view_definition.order)
    new_bundles = []

    # Add elsewhere bundles to all nodes if there are no bundles to start with
    no_bundles = (len(view_definition.bundles) == 0)

    for u, node in view_definition.nodes.items():
        if not node.selection:
            continue  # no waypoints
        d_rank = +1 if node.direction == 'R' else -1
        r = view_definition.rank(u)

        if no_bundles or (0 <= r + d_rank < R and u not in has_to_elsewhere):
            waypoint = 'from {}'.format(u)
            assert waypoint not in view_definition.nodes
            new_bundles.append(Bundle(u, Elsewhere, waypoints=[waypoint]))

        if no_bundles or (0 <= r - d_rank < R and u not in has_from_elsewhere):
            waypoint = 'to {}'.format(u)
            # assert waypoint not in d2.nodes
            # d2.nodes[waypoint] = Node(direction=node.direction)
            new_bundles.append(Bundle(Elsewhere, u, waypoints=[waypoint]))

    return new_bundles



def _rank(order, u):
    for r, bands in enumerate(order):
        for rank in bands:
            if u in rank:
                return r
    raise ValueError('node not in order')


def augment(G, order, new_bundles):
    """Add waypoints for new_bundles to G and order"""

    # copy G and order
    G = G.copy()
    order = [
        [rank[:] for rank in bands]
        for bands in order
    ]
    new_nodes = {}

    R = len(order)
    for bundle in new_bundles:
        assert len(bundle.waypoints) == 1
        w = bundle.waypoints[0]

        if bundle.to_elsewhere:
            u = G.node[bundle.source]['node']
            r = _rank(order, bundle.source)
            d_rank = +1 if u.direction == 'R' else -1
            assert w not in G.node
            new_nodes[w] = Node(direction=u.direction)
            G.add_node(w, node=new_nodes[w])

            r = check_order_edges(order, r, d_rank)

            this_rank = order[r + d_rank]
            prev_rank = order[r]
            G.add_edge(bundle.source, w, bundles=[bundle])
            i, j = new_node_indices(G, this_rank, prev_rank, w,
                                    side='below') # if d == 'L' else 'above')
            this_rank[i].insert(j, w)

        elif bundle.from_elsewhere:
            u = G.node[bundle.target]['node']
            r = _rank(order, bundle.target)
            d_rank = +1 if u.direction == 'R' else -1
            assert w not in G.node
            new_nodes[w] = Node(direction=u.direction)
            G.add_node(w, node=new_nodes[w])

            r = check_order_edges(order, r, -d_rank)

            this_rank = order[r - d_rank]
            prev_rank = order[r]
            G.add_edge(w, bundle.target, bundles=[bundle])
            i, j = new_node_indices(G, this_rank, prev_rank, w,
                                    side='below') # if d == 'L' else 'above')
            this_rank[i].insert(j, w)

        else:
            assert False, "Should not call augment() with non-elsewhere bundle"

    return G, order, new_nodes


def check_order_edges(order, r, dr):
    nb = len(order[0]) if order else 1
    if r + dr >= len(order):
        order.append([[] for i in range(nb)])
    elif r + dr < 0:
        order.insert(0, [[] for i in range(nb)])
        r += 1
    return r
