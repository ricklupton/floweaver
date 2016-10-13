import itertools
from palettable.colorbrewer import qualitative, sequential
import numpy as np


# From matplotlib.colours
def rgb2hex(rgb):
    'Given an rgb or rgba sequence of 0-1 floats, return the hex string'
    return '#%02x%02x%02x' % tuple([int(np.round(val * 255)) for val in rgb[:3]])


def graph_to_sankey(G,
                    groups=None,
                    palette=None,
                    sample=None,
                    hue=None,
                    hue_range=None,
                    hue_norm=False):
    """Convert to display format, set colours, titles etc."""
    if groups is None:
        groups = []

    def get_data(data, key):
        if key == 'value':
            return data[key]
        else:
            return data['measures'][key]

    if sample is None:
        get_value = lambda data, key: float(get_data(data, key))
    elif sample == 'mean':
        get_value = lambda data, key: get_data(data, key).mean()
    else:
        get_value = lambda data, key: get_data(data, key)[sample]

    if hue is None:
        # qualitative colours based on material
        if palette is None:
            palette = qualitative.Pastel1_8.hex_colors
            # palette = qualitative.Set3_11

        if not isinstance(palette, dict):
            materials = sorted(set([m for v, w, (m, t) in G.edges(keys=True)]))
            palette = {m: v
                       for m, v in zip(materials, itertools.cycle(palette))}
        get_color = lambda m, data: palette[m]

    else:
        if palette is None:
            palette = sequential.Reds_9.mpl_colormap
        if hue_norm:
            get_hue = lambda data: get_value(data, hue) / get_value(data, 'value')
        elif callable(hue):
            get_hue = hue
        else:
            get_hue = lambda data: get_value(data, hue)
        values = np.array([get_hue(data) for _, _, data in G.edges(data=True)])
        if hue_range is None:
            vmin, vmax = values.min(), values.max()
        else:
            vmin, vmax = hue_range
        get_color = lambda m, data: rgb2hex(palette((get_hue(data) - vmin) / (vmax - vmin)))

    links = []
    nodes = []

    for v, w, (m, t), data in G.edges(keys=True, data=True):
        links.append({
            'source': v,
            'target': w,
            'type': m,
            'time': t,
            'value': get_value(data, 'value'),
            'bundles': [str(x) for x in data.get('bundles', [])],
            'color': get_color(m, data),
            'title': str(m),
            'opacity': 1.0,
        })

    for u, data in G.nodes(data=True):
        nodes.append({
            'id': u,
            'title': str(data.get('title', u)),
            'style': data.get('type', 'default'),
            'direction': 'l' if data.get('direction', 'R') == 'L' else 'r',
            'visibility': 'hidden' if data.get('title') == '' else 'visible',
        })

    return {
        'nodes': nodes,
        'links': links,
        'order': G.ordering.layers,
        'groups': groups,
    }
