import networkx as nx

from .node import Node
from .bundle import Bundle, Elsewhere
from .ordering import new_node_indices


def elsewhere_bundles(view_definition):
    # Build set of existing bundles to/from elsewhere
    has_to_elsewhere = set()
    has_from_elsewhere = set()
    for bundle in view_definition.bundles.values():
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
    new_nodes = {}
    new_bundles = {}

    # Add elsewhere bundles to all nodes if there are no bundles to start with
    no_bundles = (len(view_definition.bundles) == 0)

    for u, node in view_definition.nodes.items():
        if not node.selection:
            continue  # no waypoints
        d_rank = +1 if node.direction == 'R' else -1
        r = view_definition.rank(u)

        if no_bundles or (0 <= r + d_rank < R and u not in has_to_elsewhere):
            dummy_id = '__{}>'.format(u)
            assert dummy_id not in view_definition.nodes
            new_nodes[dummy_id] = Node(direction=node.direction)
            new_bundles[dummy_id] = Bundle(u, Elsewhere, waypoints=[dummy_id])

        if no_bundles or (0 <= r - d_rank < R and u not in has_from_elsewhere):
            dummy_id = '__>{}'.format(u)
            assert dummy_id not in view_definition.nodes
            new_nodes[dummy_id] = Node(direction=node.direction)
            new_bundles[dummy_id] = Bundle(Elsewhere, u, waypoints=[dummy_id])

    return new_nodes, new_bundles



def _rank(order, u):
    for r, bands in enumerate(order):
        for rank in bands:
            if u in rank:
                return r
    raise ValueError('node not in order')


def augment(G, new_nodes, new_bundles):
    """Add waypoints for new_bundles to layered graph G"""

    # copy G and order
    G = G.copy()

    R = len(G.order)
    for k, bundle in new_bundles.items():
        assert len(bundle.waypoints) == 1
        w = bundle.waypoints[0]

        if bundle.to_elsewhere:
            u = G.node[bundle.source]['node']
            r = _rank(G.order, bundle.source)
            d_rank = +1 if u.direction == 'R' else -1
            G.add_node(w, node=new_nodes[w])

            r = check_order_edges(G.order, r, d_rank)

            this_rank = G.order[r + d_rank]
            prev_rank = G.order[r]
            G.add_edge(bundle.source, w, bundles=[k])
            i, j = new_node_indices(G, this_rank, prev_rank, w,
                                    side='below') # if d == 'L' else 'above')
            this_rank[i].insert(j, w)

        elif bundle.from_elsewhere:
            u = G.node[bundle.target]['node']
            r = _rank(G.order, bundle.target)
            d_rank = +1 if u.direction == 'R' else -1
            G.add_node(w, node=new_nodes[w])

            r = check_order_edges(G.order, r, -d_rank)

            this_rank = G.order[r - d_rank]
            prev_rank = G.order[r]
            G.add_edge(w, bundle.target, bundles=[k])
            i, j = new_node_indices(G, this_rank, prev_rank, w,
                                    side='below') # if d == 'L' else 'above')
            this_rank[i].insert(j, w)

        else:
            assert False, "Should not call augment() with non-elsewhere bundle"

    return G


def check_order_edges(order, r, dr):
    nb = len(order[0]) if order else 1
    if r + dr >= len(order):
        order.append([[] for i in range(nb)])
    elif r + dr < 0:
        order.insert(0, [[] for i in range(nb)])
        r += 1
    return r
