import bisect
from .utils import pairwise
import attr


def _convert_layers(layers):
    """Wrap nodes in a single band, if none are specified."""
    for item in layers:
        if any(isinstance(x, str) for x in item):
            return tuple((tuple(layer_nodes), ) for layer_nodes in layers)

    return tuple(tuple(tuple(band_nodes) for band_nodes in layer_bands)
                 for layer_bands in layers)


@attr.s(slots=True, frozen=True, repr=False)
class Ordering(object):
    layers = attr.ib(convert=_convert_layers)

    def __repr__(self):
        def format_layer(layer):
            return '; '.join(', '.join(band) for band in layer)

        return 'Ordering( {} )'.format(' | '.join(format_layer(layer)
                                                  for layer in self.layers))

    def insert(self, i, j, k, value):
        def __insert(band):
            return band[:k] + (value, ) + band[k:]

        def _insert(layer):
            return [__insert(band) if j == jj else band
                    for jj, band in enumerate(layer)]

        layers = [_insert(layer) if i == ii else layer
                  for ii, layer in enumerate(self.layers)]
        return Ordering(layers)

    def remove(self, value):
        def __remove(band):
            return tuple(x for x in band if x != value)

        def _remove(layer):
            return tuple(__remove(band) for band in layer)

        layers = tuple(_remove(layer) for layer in self.layers)

        # remove unused ranks from layers
        layers = tuple(layer for layer in layers if any(rank
                                                        for rank in layer))

        return Ordering(layers)

    def indices(self, value):
        for r, bands in enumerate(self.layers):
            for i, rank in enumerate(bands):
                if value in rank:
                    return r, i, rank.index(value)
        raise ValueError('node "{}" not in ordering'.format(value))


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


def new_node_indices(G,
                     this_bands,
                     other_bands,
                     new_process_group,
                     side='below'):
    assert side in ('above', 'below')

    this_layer, this_idx = flatten_bands(this_bands)
    other_layer, other_idx = flatten_bands(other_bands)

    # Position of new node, and which band in other_bands it would be
    new_pos = median_value(neighbour_positions(G, other_layer,
                                               new_process_group))
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

    index = (bisect.bisect_right(candidates, new_pos)
             if side == 'below' else bisect.bisect_left(candidates, new_pos))

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
