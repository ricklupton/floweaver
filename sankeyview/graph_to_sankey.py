import itertools
from palettable.colorbrewer import qualitative


def graph_to_sankey(G, order, color_key='material', palette=None):
    """Convert to display format, set colours, titles etc."""
    if palette is None:
        palette = qualitative.Pastel1_8.hex_colors
        # palette = qualitative.Set3_11

    if not isinstance(palette, dict):
        materials = sorted(set([k for v, w, k in G.edges(keys=True)]))
        palette = {k: v for k, v in zip(materials, itertools.cycle(palette))}

    flows = []
    processes = []

    for v, w, k, data in G.edges(keys=True, data=True):
        flows.append({
            'source': v,
            'target': w,
            'material': k,
            'value': float(data['value']),
            'color': palette[k],
            'title': k,
            'opacity': 0.8,
        })

    for u, data in G.nodes(data=True):
        # basename, part = u.split('^', 1)
        processes.append({
            'id': u,
            'title': data.get('title', u),
            'style': data.get('type', 'default'),
            'direction': 'l' if data.get('direction', 'R') == 'L' else 'r',
            'visibility': 'hidden' if data.get('title') == '' else 'visible',
        })

    return {'processes': processes, 'flows': flows, 'order': order}

