
from .ordering import new_node_indices
from .node import Node

# temporary
def get_node(G, u):
    U = G.node[u]['node']
    return U


def find_rank_band_idx(order, node):
    for r, bands in enumerate(order):
        for i, rank in enumerate(bands):
            if node in rank:
                return r, i, rank.index(node)
    raise ValueError('node not in order')


def add_dummy_nodes(G, order, v, w, bundle, node_kwargs=None):
    if node_kwargs is None:
        node_kwargs = {}

    V = get_node(G, v)
    W = get_node(G, w)
    H = G.copy()
    order = [[list(rank) for rank in bands] for bands in order]
    rv, iv, jv = find_rank_band_idx(order, v)
    rw, iw, jw = find_rank_band_idx(order, w)

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
        _add_edge(H, v, w, bundle)
        return H, order

    u = v
    for r in new_ranks:
        idr = '__{}_{}_{}'.format(v, w, r)
        # Only add and position dummy nodes the first time -- bundles can share
        # a dummy node leading to this happening more than once
        if idr not in H.node:
            _add_edge(H, u, idr, bundle)
            if r == rv:
                i, j = iv, jv + (+1 if V.direction == 'R' else -1)
            else:
                prev_rank = order[r + 1 if d == 'L' else r - 1]
                i, j = new_node_indices(H, order[r], prev_rank, idr,
                                        side='below' if d == 'L' else 'above')
            H.add_node(idr, node=Node(direction=d, **node_kwargs))
            order[r][i].insert(j, idr)
        else:
            _add_edge(H, u, idr, bundle)
        u = idr
    _add_edge(H, u, w, bundle)

    return H, order


def _add_edge(G, v, w, bundle):
    if G.has_edge(v, w):
        G[v][w]['bundles'].append(bundle)
    else:
        G.add_edge(v, w, bundles=[bundle])
