import random
from collections import defaultdict

from ipysankeywidget import SankeyWidget
import networkx as nx

from .utils import pairwise
from .sankey_view import sankey_view
from .augment_view_graph import augment, elsewhere_bundles
from .view_graph import view_graph
from .graph_to_sankey import graph_to_sankey
from .view_definition import ViewDefinition, Waypoint, Elsewhere
from IPython.display import display
import graphviz


def show_sankey(view_definition, dataset, palette=None, width=700, height=500,
                align_link_types=False, measure='value'):
    G, groups = sankey_view(view_definition, dataset, measure)
    value = graph_to_sankey(G, groups, palette=palette)
    if align_link_types:
        value['alignLinkTypes'] = True
    return SankeyWidget(value=value, width=str(width), height=str(height),
                        margins={'top': 25, 'bottom': 10, 'left': 130, 'right': 130})


# def show_view_definition(view_definition, filename=None,
#                          directory=None, xlabels=None, labels=None):

#     if xlabels is None:
#         xlabels = {}
#     if labels is None:
#         labels = {}

#     g = graphviz.Digraph(graph_attr=dict(splines='true', rankdir='LR'),
#                          node_attr=dict(fontsize='12', width='0.5', height='0.3'))

#     for r, bands in enumerate(view_definition.ordering.layers):
#         subgraph = graphviz.Digraph()
#         for i, rank in enumerate(bands):
#             for j, u in enumerate(rank):
#                 node_style = 'solid' if u in view_definition.process_groups else 'dashed'
#                 attr = dict(label=u, shape='box', style=node_style)
#                 if u in xlabels:
#                     attr['xlabel'] = xlabels[u]
#                 if u in labels:
#                     attr['label'] = labels[u]
#                 subgraph.node(u, **attr)
#         subgraph.body.append('rank=same;')
#         g.subgraph(subgraph)

#     # invisible edges to get order right
#     for r, bands in enumerate(view_definition.ordering.layers):
#         for i, rank in enumerate(bands):
#             for a, b in pairwise(rank):
#                 g.edge(a, b, color='white')

#     for bundle in view_definition.bundles.values():
#         v, w = bundle.source, bundle.target
#         if w is Elsewhere:
#             pass
#         elif v is Elsewhere:
#             pass
#         else:
#             rv, jv = find_order(view_definition.ordering.layers, v)
#             rw, jw = find_order(view_definition.ordering.layers, w)
#             if rv == rw and jv > jw:
#                 g.edge(str(w), str(v), dir='back')
#             else:
#                 g.edge(str(v), str(w))

#     if filename:
#         if filename.endswith('.png'):
#             g.format = 'png'
#         elif filename.endswith('.xdot'):
#             g.format = 'xdot'
#         g.render(filename=filename, directory=directory, cleanup=True)

#     return g


def show_view_graph(view_definition, include_elsewhere=False, filename=None,
                    directory=None, xlabels=None, labels=None,
                    include_coords=False):

    if xlabels is None:
        xlabels = {}
    if labels is None:
        labels = {}

    GV, implicit_waypoints = view_graph(view_definition)

    if include_elsewhere:
        new_waypoints, new_bundles = elsewhere_bundles(view_definition)
        GV = augment(GV, new_waypoints, new_bundles)

    g = graphviz.Digraph(#engine='neato',
                         graph_attr=dict(splines='true', rankdir='LR'),
                         node_attr=dict(fontsize='12', width='0.5', height='0.3'))

    # band_heights = defaultdict(int)
    # for bands in oV:
    #     for i, rank in enumerate(bands):
    #         band_heights[i] = max(band_heights[i], len(rank))

    for r, bands in enumerate(GV.ordering.layers):
        # j0 = 0
        subgraph = graphviz.Digraph()
        for i, rank in enumerate(bands):
            for j, u in enumerate(rank):
                node = GV.node[u]['node']
                if '_' in u:
                    attr = dict(label='', shape='point', width='0.1')
                elif isinstance(node, Waypoint):
                    if u.startswith('from ') or u.startswith('to '):
                        attr = dict(label=u, shape='plaintext')
                    else:
                        attr = dict(label=u, shape='box', style='dashed')
                else:
                    attr = dict(label=u, shape='box')
                if u in xlabels:
                    attr['xlabel'] = xlabels[u]
                if u in labels:
                    attr['label'] = labels[u]
                if include_coords:
                    attr['label'] += '\n({}, {}, {})'.format(r, i, j)
                # pos = (r * 1.2, -0.6 * (j0 + j))
                subgraph.node(u, **attr) #pos='{},{}!'.format(*pos), pin='True', **attr)
            # j0 += band_heights[i]
        subgraph.body.append('rank=same;')
        g.subgraph(subgraph)

    # invisible edges to get order right
    for r, bands in enumerate(GV.ordering.layers):
        for i, rank in enumerate(bands):
            for a, b in pairwise(rank):
                g.edge(a, b, color='white')

    for v, w in GV.edges():
        rv, jv = find_order(GV.ordering.layers, v)
        rw, jw = find_order(GV.ordering.layers, w)
        if rv == rw and jv > jw:
            g.edge(w, v, dir='back')
        else:
            g.edge(v, w)

    # r0 = -0.5
    # r1 = len(oV) + 0.5
    # j = 0.5
    # for i in range(1, len(band_heights)):
    #     attr = dict(pin='True', shape='none', label='')
    #     g.node('__{}a'.format(j), pos='{},{}!'.format(r0*1.2, -0.6*j), **attr)
    #     g.node('__{}b'.format(j), pos='{},{}!'.format(r1*1.2, -0.6*j), **attr)
    #     g.edge('__{}a'.format(j), '__{}b'.format(j), arrowhead='none', style='dotted')
    #     j += band_heights[i]

    if filename:
        g.format = 'png'
        g.render(filename=filename, directory=directory, cleanup=True)

    return g


def find_order(order, process_group):
    for r, bands in enumerate(order):
        j = 0
        for i, rank in enumerate(bands):
            for u in rank:
                if u == process_group:
                    return (r, j)
                j += 1
    raise ValueError('process_group "{}" not found'.format(process_group))


def show_view_graph_pos(view_definition, include_elsewhere=False, filename=None,
                        directory=None, xlabels=None, labels=None,
                        include_coords=False):
    if xlabels is None:
        xlabels = {}
    if labels is None:
        labels = {}

    if include_elsewhere:
        view_definition = augment(view_definition)

    GV, oV = view_graph(view_definition)

    g = graphviz.Digraph(engine='neato',
                         graph_attr=dict(splines='true'),
                         node_attr=dict(fontsize='12', width='0.5', height='0.3'))

    band_heights = defaultdict(int)
    for bands in oV:
        for i, rank in enumerate(bands):
            band_heights[i] = max(band_heights[i], len(rank))

    for r, bands in enumerate(oV):
        j0 = 0
        for i, rank in enumerate(bands):
            for j, u in enumerate(rank):
                process_group = GV.node[u]['node']
                if '_' in u:
                    attr = dict(label='', shape='point', width='0.1')
                elif not process_group.selection:  # waypoint
                    if u.startswith('from ') or u.startswith('to '):
                        attr = dict(label=u, shape='plaintext')
                    else:
                        attr = dict(label=u, shape='box', style='dashed')
                else:
                    attr = dict(label=u, shape='box')
                if u in xlabels:
                    attr['xlabel'] = xlabels[u]
                if u in labels:
                    attr['label'] = labels[u]
                if include_coords:
                    attr['label'] += '\n({}, {}, {})'.format(r, i, j)
                pos = (r * 1.2, -0.6 * (j0 + j))
                g.process_group(u, pos='{},{}!'.format(*pos), pin='True', **attr)
            j0 += band_heights[i]

    for v, w in GV.edges():
        g.edge(v, w)

    r0 = -0.5
    r1 = len(oV) + 0.5
    j = 0.5
    for i in range(1, len(band_heights)):
        attr = dict(pin='True', shape='none', label='')
        g.node('__{}a'.format(j), pos='{},{}!'.format(r0*1.2, -0.6*j), **attr)
        g.node('__{}b'.format(j), pos='{},{}!'.format(r1*1.2, -0.6*j), **attr)
        g.edge('__{}a'.format(j), '__{}b'.format(j), arrowhead='none', style='dotted')
        j += band_heights[i]

    if filename:
        g.format = 'png'
        g.render(filename=filename, directory=directory, cleanup=True)

    return g
