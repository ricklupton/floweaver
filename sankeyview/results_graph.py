import pandas as pd

from .layered_graph import MultiLayeredGraph, Ordering
from .partition import Partition, Group
from .sankey_definition import ProcessGroup


def results_graph(view_graph,
                  bundle_flows,
                  flow_partition=None,
                  time_partition=None,
                  measure='value',
                  agg_measures=None):

    G = MultiLayeredGraph()
    groups = []

    # Add nodes to graph and to order
    layers = []
    for r, bands in enumerate(view_graph.ordering.layers):
        o = [[] for band in bands]
        for i, rank in enumerate(bands):
            for u in rank:
                node = view_graph.get_node(u)
                group_nodes = []
                for x, xtitle in nodes_from_partition(u, node.partition):
                    o[i].append(x)
                    group_nodes.append(x)
                    if node.partition == None:
                        title = u if node.title is None else node.title
                    else:
                        title = xtitle
                    G.add_node(x, {
                        'type': ('process' if isinstance(node, ProcessGroup)
                                 else 'group'),
                        'direction': node.direction,
                        'title': title,
                    })
                groups.append({
                    'id': u,
                    'type': ('process'
                             if isinstance(node, ProcessGroup) else 'group'),
                    'title': node.title or '',
                    'nodes': group_nodes
                })
        layers.append(o)

    G.ordering = Ordering(layers)

    # Add edges to graph
    for v, w, data in view_graph.edges(data=True):
        flows = pd.concat([bundle_flows[bundle] for bundle in data['bundles']],
                          ignore_index=True)
        gv = view_graph.get_node(v).partition
        gw = view_graph.get_node(w).partition
        gf = data.get('flow_partition') or flow_partition or None
        gt = time_partition or None
        edges = group_flows(flows, v, gv, w, gw, gf, gt, measure, agg_measures)
        for _, _, _, d in edges:
            d['bundles'] = data['bundles']
        G.add_edges_from(edges)

    # remove unused nodes
    unused = [u for u, deg in G.degree_iter() if deg == 0]
    for u in unused:
        G.remove_node(u)

    # remove unused nodes from groups
    groups = [
        dict(g, nodes=[x for x in g['nodes'] if x not in unused])
        for g in groups
    ]
    groups = [g for g in groups if len(g['nodes']) > 0]

    return G, groups


def nodes_from_partition(u, partition):
    if partition is None:
        return [('{}^*'.format(u), '*')]
    else:
        # _ -> other
        return [('{}^{}'.format(u, value), value)
                for value in partition.labels + ['_']]


def group_flows(flows,
                v,
                partition1,
                w,
                partition2,
                flow_partition,
                time_partition,
                measure,
                agg_measures=None):

    if agg_measures is None:
        agg_measures = {}
    agg_all_measures = dict(agg_measures)
    agg_all_measures[measure] = 'sum'

    e = flows.copy()
    set_partition_keys(e, partition1, 'k1', v + '^', process_side='source')
    set_partition_keys(e, partition2, 'k2', w + '^', process_side='target')
    set_partition_keys(e, flow_partition, 'k3', '')
    set_partition_keys(e, time_partition, 'k4', '')
    grouped = e.groupby(['k1', 'k2', 'k3', 'k4'])

    if 'sample' in flows:

        def data(group):
            agg = group.groupby('sample').agg(agg_all_measures)
            d = {'value': agg[measure].values}
            if agg_measures:
                d['measures'] = {k: agg[k].values for k in agg_measures}
            return d

    else:

        def data(group):
            agg = group.groupby(lambda x: '').agg(agg_all_measures)
            d = {'value': agg[measure].iloc[0]}
            if agg_measures:
                d['measures'] = {k: agg[k].iloc[0] for k in agg_measures}
            return d

    return [
        (source, target, (material, time), data(group))
        for (source, target, material, time), group in grouped
    ]


def set_partition_keys(df, partition, key_column, prefix, process_side=None):
    if partition is None:
        partition = Partition([Group('*', [])])
    df[key_column] = prefix + '_'  # other
    seen = (df.index != df.index)  # False
    for group in partition.groups:
        q = (df.index == df.index)  # True
        for dim, values in group.query:
            if dim.startswith('process') and process_side:
                dim = process_side + dim[7:]
            q = q & df[dim].isin(values)
        if any(q & seen):
            dup = df[q & seen]
            raise ValueError('Duplicate values in group {} ({}): {}'
                             .format(group, process_side, ', '.join(
                                 ['{}-{}'.format(e.source, e.target)
                                  for _, e in dup.iterrows()])))
        df.loc[q, key_column] = prefix + str(group.label)
        seen = seen | q
