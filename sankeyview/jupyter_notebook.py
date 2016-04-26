import random
from ipysankeywidget import SankeyWidget
import networkx as nx
import matplotlib.pyplot as plt
from .sankey_view import SankeyView
from IPython.display import display


def show_sankey(nodes, bundles, dataset, flow_grouping=None, dividers=None, palette=None,
                width=700, height=500, show_unused=False, align_materials=False,
                **opts):
    v = SankeyView(nodes, bundles, dividers)
    G, order = v.build(dataset, flow_grouping)
    if show_unused:
        display(v.unused_flows)
    value = v.graph_to_sankey(G, order, palette=palette)
    if align_materials:
        value['alignMaterials'] = True
    return SankeyWidget(value=value, width=width, height=height,
                        margins={'top': 10, 'bottom': 10, 'left': 90, 'right': 120})


def show_high_level_graph(nodes, bundles):
    v = SankeyView(nodes, bundles)
    g = v.high_level.copy()
    for n in g.nodes():
        if n.startswith('to ') or n.startswith('from '):
            g.remove_node(n)
    pos = {k: (data['node'].rank + random.random()*0.2, data['node'].order) for k, data in g.nodes(data=True)}
    nodes = g.nodes()
    labels = {k: '' if '_' in k else k for k in nodes}
    node_colors = ['y' if '_' in k else 'r' for k in nodes ]
    fig, ax = plt.subplots(figsize=(8, 4))

    min_rank = min(x for (x, y) in pos.values())
    max_rank = max(x for (x, y) in pos.values())
    min_ypos = min(y for (x, y) in pos.values())
    max_ypos = max(y for (x, y) in pos.values())
    ax.set_xlim(min_rank - 0.5, max_rank + 0.5)
    ax.set_ylim(max_ypos + 0.5, min_ypos - 0.5)
    ax.set_xticks(range(int(min_rank), int(max_rank) + 1))
    ax.set_yticks(range(int(min_ypos), int(max_ypos) + 1))
    ax.set_xlabel('Rank')
    ax.set_ylabel('Vertical position')
    nx.draw_networkx(g, pos, nodelist=nodes, alpha=0.5, node_color=node_colors, labels=labels, ax=ax)


import graphviz
def high_level_graphviz(nodes, bundles, dividers=None, include_elsewhere=False, filename=None,
                        directory=None, xlabels=None, labels=None, include_coords=False):
    if dividers is None:
        dividers = []
    if xlabels is None:
        xlabels = {}
    if labels is None:
        labels = {}

    g = graphviz.Digraph(engine='neato',
                         graph_attr=dict(splines='true'),
                         node_attr=dict(fontsize='12', width='0.5', height='0.3'))
    v = SankeyView(nodes, bundles)
    nn = [(k, data['node']) for k, data in v.high_level.nodes(data=True)
          if include_elsewhere or not (k.startswith('from ') or k.startswith('to '))]
    for k, node in nn:
        if '_' in k:
            attr = dict(label='', shape='point', width='0.1')
        elif not node.query:  # waypoint
            if k.startswith('from ') or k.startswith('to '):
                attr = dict(label=k, shape='plaintext')
            else:
                attr = dict(label=k, shape='box', style='dashed')
        else:
            attr = dict(label=k, shape='box')
        if k in xlabels:
            attr['xlabel'] = xlabels[k]
        if k in labels:
            attr['label'] = labels[k]
        if include_coords:
            attr['label'] += '\n({}, {})'.format(node.rank, node.order)
        g.node(k, pos='{},{}!'.format(node.rank*1.2, -0.6*node.order), pin='True', **attr)
    for v, w, data in v.high_level.edges(data=True):
        if not include_elsewhere and (v.startswith('from ') or v.startswith('to ')):
            continue
        if not include_elsewhere and (w.startswith('from ') or w.startswith('to ')):
            continue
        g.edge(v, w)

    min_rank = min(node.rank for k, node in nn) - 1
    max_rank = max(node.rank for k, node in nn) + 1
    for i, d in enumerate(dividers):
        attr = dict(pin='True', shape='none', label='')
        g.node('__{}a'.format(i), pos='{},{}!'.format(min_rank*1.5, -0.6*d), **attr)
        g.node('__{}b'.format(i), pos='{},{}!'.format(max_rank*1.5, -0.6*d), **attr)
        g.edge('__{}a'.format(i), '__{}b'.format(i), arrowhead='none', style='dotted')

    if filename:
        g.format = 'png'
        g.render(filename=filename, directory=directory, cleanup=True)

    return g
