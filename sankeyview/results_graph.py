from itertools import groupby
import networkx as nx
import pandas as pd


from .grouping import Grouping


def results_graph(view_graph, view_order, bundle_flows, flow_grouping=None):

    G = nx.MultiDiGraph()
    order = []

    for r, bands in enumerate(view_order):
        o = [[] for band in bands]
        for i, rank in enumerate(bands):
            for u in rank:
                node = view_graph.node[u]['node']
                for x, xtitle in nodes_from_grouping(u, node.grouping):
                    o[i].append(x)
                    if node.grouping == Grouping.All:
                        title = u if node.title is None else node.title
                    else:
                        title = xtitle
                    G.add_node(x, {
                        'type': 'process' if node.selection else 'group',
                        'direction': node.direction,
                        'title': title,
                    })
        order.append(o)

    for v, w, data in view_graph.edges(data=True):
        flows = pd.concat([bundle_flows[bundle] for bundle in data['bundles']],
                           ignore_index=True)
        gv = view_graph.node[v]['node'].grouping
        gw = view_graph.node[w]['node'].grouping
        gf = flow_grouping
        for b in data['bundles']:
            if gf is None:
                gf = b.flow_grouping
            if b.flow_grouping is not None and b.flow_grouping != gf:
                raise ValueError('Bundle {} flow grouping {} != {}'.format(b, b.flow_grouping, gf))
        if gf is None:
            gf = Grouping.All
        G.add_edges_from(group_flows(flows, v, gv, w, gw, gf))

    # remove unused nodes
    unused = [u for u, deg in G.degree_iter() if deg == 0]
    for u in unused:
        G.remove_node(u)
    # remove unused nodes
    order = [
        [
            [x for x in rank if x not in unused]
            for rank in bands
        ]
        for bands in order
    ]
    # remove unused ranks
    order = [
        bands
        for bands in order
        if any(rank for rank in bands)
    ]

    return G, order


def nodes_from_grouping(u, grouping):
    # _ -> other
    return [('{}^{}'.format(u, value), value) for value in grouping.labels + ['_']]


def group_flows(flows, v, grouping1, w, grouping2, flow_grouping):
    e = flows.copy()

    set_grouping_keys(e, grouping1, 'k1', v + '^', node_side='source')
    set_grouping_keys(e, grouping2, 'k2', w + '^', node_side='target')
    set_grouping_keys(e, flow_grouping, 'k3', '')

    #grouped = e[(e.k1 != '') | (e.k2 != '')] \
    grouped = e \
        .groupby(['k1', 'k2', 'k3'], as_index=False)

    agg = grouped.agg({'value': 'sum'})
    return [(row['k1'], row['k2'], row['k3'], { 'value': row['value'] })
            for i, row in agg.iterrows()]


def set_grouping_keys(df, grouping, key_column, prefix, node_side=None):
    df[key_column] = prefix + '_'  # other
    seen = (df.index != df.index)  # False
    for group in grouping.groups:
        q = (df.index == df.index)  # True
        for dim, values in group.query:
            if dim.startswith('node') and node_side:
                dim = node_side + dim[4:]
            q = q & df[dim].isin(values)
        if any(q & seen):
            dup = df[q & seen]
            raise ValueError(
                'Duplicate values in group {} ({}): {}'
                .format(group, node_side,
                        ', '.join(['{}-{}'.format(e.source, e.target) for _, e in dup.iterrows()])))
        df.loc[q, key_column] = prefix + str(group.label)
        seen = seen | q


def band_index(dividers, depth):
    for i, d in enumerate(dividers):
        if d > depth:
            return i
    return len(dividers)


# def leaves_below(tree, node):
#     return set(sum(
#         ([vv for vv in v if tree.out_degree(vv) == 0]
#          for k, v in nx.dfs_successors(tree, node).items()), []))


# def leaves_matching_query(trees, query):
#     """query is of the form {
#         "tree_name": ["node name in tree", "another name in  tree"],
#         "another tree name": [...],
#     }
#     or a list of these dictionaries.

#     The result is the set of leaves which are at the intersection of the tree
#     queries. If a list, the union of each of the items.

#     """
#     if query is None:
#         return []
#     if not isinstance(query, list):
#         query = [query]
#     matches = set()
#     for q in query:
#         matches.update(leaves_matching_query_single(trees, q))
#     return matches


# def leaves_matching_query_single(trees, query):
#     """query is of the form {
#         "tree_name": ["node name in tree", "another name in  tree"],
#         "another tree name": [...],
#     }

#     The result is the set of leaves which are at the intersection of the tree
#     queries.

#     """
#     matches = None
#     for tree_name, node_list in query.items():
#         if not isinstance(node_list, (list, tuple)):
#             node_list = [node_list]

#         try:
#             leaves = set()
#             for node in node_list:
#                 leaves.update(leaves_below(trees[tree_name], node) or {node})

#             if matches is None:
#                 matches = leaves
#             else:
#                 matches = matches.intersection(leaves)
#         except KeyError as err:
#             raise KeyError('Cannot find node "{}" in tree "{}"'.format(
#                 err, tree_name))

#     return matches


# def find_edges_between_slices(trees, edges, q1, q2):
#     """Filter edges according to q1 and q2

#     Returns three sets of edges: from q1 to elsewhere, from
#     q1 to q2, and from elsewhere to q2.

#     """

#     n1 = leaves_matching_query(trees, q1)
#     n2 = leaves_matching_query(trees, q2)

#     qs = (edges['source'].isin(n1) & ~edges['target'].isin(n1))
#     qt = (edges['target'].isin(n2) & ~edges['source'].isin(n2))

#     continuing = edges[qs & qt]
#     to_elsewhere = edges[qs & ~qt]
#     from_elsewhere = edges[qt & ~qs]

#     return to_elsewhere, continuing, from_elsewhere

# def grouping_key_func(grouping):
#     N = len(grouping)
#     table = defaultdict(lambda: [None] * N)
#     for i, (tree_name, node_list) in enumerate(grouping.items()):
#         for key_node in node_list:
#             for leaf in leaves_below(trees[tree_name], key_node):
#                 table[leaf][i] = key_node
#     def key(node):
#         print(node)
#         return tuple(table[node])
#     return key


# def set_grouping_keys(trees, df, grouping, column, key_column):
#     if grouping is None:
#         df[key_column] = 'XXX'
#         return

#     df[key_column] = ''
#     for i, (tree_name, node_list) in enumerate(grouping.items()):
#         seen_leaves = set()
#         for key_node in node_list:
#             try:
#                 leaves = leaves_below(trees[tree_name], key_node) or [key_node]
#             except KeyError:
#                 raise KeyError('Cannot find node "{}" in tree "{}"'.format(
#                     key_node, tree_name))
#             for leaf in leaves:
#                 if leaf in seen_leaves:
#                     raise ValueError(
#                         'Leaf "{}" found again while searching for "{}" in tree "{}"'
#                         .format(leaf, key_node, tree_name))
#                 if i == 0:
#                     df.loc[df[column] == leaf, key_column] = key_node
#                 else:
#                     df.loc[df[column] == leaf, key_column] += '/' + key_node
#                 seen_leaves.add(leaf)
