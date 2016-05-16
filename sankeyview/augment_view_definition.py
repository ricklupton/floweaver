import networkx as nx

from .node import Node
from .bundle import Bundle, Elsewhere
from .ordering import new_node_indices


def augment(view_definition):
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
    d2 = view_definition.copy()
    R = len(view_definition.order)

    # XXX maybe unnecessaryily complicated -- build graph for new_node_indices
    G = nx.DiGraph()
    for bundle in view_definition.bundles:
        G.add_edge(bundle.source, bundle.target)

    for u, node in view_definition.nodes.items():
        if not node.selection:
            continue  # no waypoints
        d_rank = +1 if node.direction == 'R' else -1
        r = d2.rank(u)

        if 0 <= r + d_rank < R and u not in has_to_elsewhere: # or u in has_to_other):
            waypoint = 'from {}'.format(u)
            assert waypoint not in d2.nodes
            d2.nodes[waypoint] = Node(direction=node.direction)

            this_rank = d2.order[d2.rank(u) + d_rank] #.append(waypoint)
            prev_rank = d2.order[d2.rank(u)]
            G.add_edge(u, waypoint)
            i, j = new_node_indices(G, this_rank, prev_rank, waypoint,
                                   side='below') # if d == 'L' else 'above')
            this_rank[i].insert(j, waypoint)

            d2.bundles.append(Bundle(u, Elsewhere, waypoints=[waypoint]))

        if 0 <= r - d_rank < R and u not in has_from_elsewhere: # or u in has_from_other):
            waypoint = 'to {}'.format(u)
            assert waypoint not in d2.nodes
            d2.nodes[waypoint] = Node(direction=node.direction)

            this_rank = d2.order[d2.rank(u) - d_rank]
            prev_rank = d2.order[d2.rank(u)]
            G.add_edge(waypoint, u)
            i, j = new_node_indices(G, this_rank, prev_rank, waypoint,
                                    side='below') # if d == 'L' else 'above')
            this_rank[i].insert(j, waypoint)

            d2.bundles.append(Bundle(Elsewhere, u, waypoints=[waypoint]))

    return d2
