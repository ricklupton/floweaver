from .ordering import new_node_indices
from .sankey_definition import Waypoint


def add_dummy_nodes(G, v, w, bundle_key, bundle_index=0, node_kwargs=None):

    if node_kwargs is None:
        node_kwargs = {}

    V = G.get_node(v)
    W = G.get_node(w)
    H = G.copy()
    rv, iv, jv = H.ordering.indices(v)
    rw, iw, jw = H.ordering.indices(w)

    if rw > rv:
        p = rv if V.direction == 'L' else rv + 1
        q = rw if W.direction == 'L' else rw - 1
        new_ranks = list(range(p, q + 1))
        d = 'R'
    elif rv > rw:
        p = rv if V.direction == 'R' else rv - 1
        q = rw if W.direction == 'R' else rw + 1
        new_ranks = list(range(p, q - 1, -1))
        d = 'L'
    else:
        new_ranks = []

    if not new_ranks:
        _add_edge(H, v, w, bundle_key)
        return H

    u = v
    for r in new_ranks:
        idr = '__{}_{}_{}'.format(v, w, r)
        # Only add and position dummy nodes the first time -- bundles can share
        # a dummy node leading to this happening more than once
        if idr not in H.node:
            _add_edge(H, u, idr, bundle_key)
            if r == rv:
                i, j = iv, jv + (+1 if V.direction == 'R' else -1)
            else:
                prev_rank = H.ordering.layers[r + 1 if d == 'L' else r - 1]
                i, j = new_node_indices(H,
                                        H.ordering.layers[r],
                                        prev_rank,
                                        idr,
                                        side='below' if d == 'L' else 'above')
            H.ordering = H.ordering.insert(r, i, j, idr)
            H.add_node(idr, node=Waypoint(direction=d, **node_kwargs))
        else:
            _add_edge(H, u, idr, bundle_key)
        u = idr
    _add_edge(H, u, w, bundle_key)

    return H


def _add_edge(G, v, w, bundle_key):
    if G.has_edge(v, w):
        G[v][w]['bundles'].append(bundle_key)
    else:
        G.add_edge(v, w, bundles=[bundle_key])
