import bisect
from .utils import pairwise


def flatten_bands(bands):
    L = []
    idx = []
    i = 0
    for band in bands:
        L.extend(band)
        idx.append(i)
        i += len(band)
    return L, idx


def unflatten_bands(L, idx):
    bands = []
    for i0, i1 in pairwise(idx + [len(L)]):
        bands.append(L[i0:i1])
    return bands


def band_index(idx, i):
    for iband, i0 in reversed(list(enumerate(idx))):
        if i >= i0:
            return iband
    return len(idx)


def new_node_index_flat(G, this_layer, other_layer, new_node, side='below'):
    assert side in ('above', 'below')
    new = median_value(neighbour_positions(G, other_layer, new_node))
    existing = [median_value(neighbour_positions(G, other_layer, u))
                for u in this_layer]
    index = (bisect.bisect_right(existing, new) if side == 'below' else
             bisect.bisect_left(existing, new))
    return index


def new_node_indices(G, this_bands, other_bands, new_node, side='below'):
    assert side in ('above', 'below')

    this_layer, this_idx = flatten_bands(this_bands)
    other_layer, other_idx = flatten_bands(other_bands)

    # Position of new node, and which band in other_bands it would be
    new_pos = median_value(neighbour_positions(G, other_layer, new_node))
    if new_pos == -1:
        # no connection -- default value?
        return (0, 0)
    new_band = band_index(other_idx, new_pos)

    # Position of other nodes in layer
    existing_pos = [median_value(neighbour_positions(G, other_layer, u))
                    for u in this_layer]
    existing_pos = fill_unknown(existing_pos, side)

    # New node should be in new_band, at a position depending on the existing
    # nodes in that band.
    candidates = [pos for pos in existing_pos
                  if band_index(other_idx, pos) == new_band]

    index = (bisect.bisect_right(candidates, new_pos) if side == 'below' else
             bisect.bisect_left(candidates, new_pos))

    return (new_band, index)


def median_value(positions):
    N = len(positions)
    m = N // 2
    if N == 0:
        return -1
    elif N % 2 == 1:
        return positions[m]
    elif N == 2:
        return (positions[0] + positions[1]) / 2
    else:
        left = positions[m - 1] - positions[0]
        right = positions[-1] - positions[m]
        return (positions[m - 1] * right + positions[m] * left) / (
            left + right)


def neighbour_positions(G, rank, u):
    # neighbouring positions on other rank
    positions = []
    for i, n in enumerate(rank):
        if G.has_edge(n, u) or G.has_edge(u, n):
            positions.append(i)

    return sorted(positions)


def fill_unknown(values, side):
    assert side in ('above', 'below')
    if not values:
        return []

    if side == 'above':
        y = values[::-1]
        a = y[0] if y[0] >= 0 else len(y)
    else:
        y = values
        a = y[0] if y[0] >= 0 else 0

    z = []
    for x in y:
        if x >= 0:
            a = x
        z.append(a)

    if side == 'above':
        return z[::-1]
    else:
        return z
