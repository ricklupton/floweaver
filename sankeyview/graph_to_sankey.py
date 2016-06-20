import itertools
from collections import defaultdict
from palettable.colorbrewer import qualitative


def graph_to_sankey(G, order, groups=None, palette=None):
    """Convert to display format, set colours, titles etc."""
    if groups is None:
        groups = []

    if palette is None:
        palette = qualitative.Pastel1_8.hex_colors
        # palette = qualitative.Set3_11

    if not isinstance(palette, dict):
        materials = sorted(set([m for v, w, (m, t) in G.edges(keys=True)]))
        palette = {m: v for m, v in zip(materials, itertools.cycle(palette))}

    links = []
    nodes = []

    for v, w, (m, t), data in G.edges(keys=True, data=True):
        links.append({
            'source': v,
            'target': w,
            'type': m,
            'time': t,
            'value': float(data['value']),
            'color': palette[m],
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
            'bundle': data.get('bundle'),
            'def_pos': data.get('def_pos'),
        })

    return {'nodes': nodes, 'links': links, 'order': order, 'groups': groups}

