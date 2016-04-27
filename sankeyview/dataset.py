import pandas as pd
import networkx as nx

import itertools

from .grouping import Grouping


def leaves_below(tree, node):
    return set(sum(
        ([vv for vv in v if tree.out_degree(vv) == 0]
         for k, v in nx.dfs_successors(tree, node).items()), []))


def leaves_matching_query(trees, query):
    """query is of the form {
        "tree_name": ["node name in tree", "another name in  tree"],
        "another tree name": [...],
    }
    or a list of these dictionaries.

    The result is the set of leaves which are at the intersection of the tree
    queries. If a list, the union of each of the items.

    """
    if query is None:
        return []
    if not isinstance(query, list):
        query = [query]
    matches = set()
    for q in query:
        matches.update(leaves_matching_query_single(trees, q))
    return matches


def leaves_matching_query_single(trees, query):
    """query is of the form {
        "tree_name": ["node name in tree", "another name in  tree"],
        "another tree name": [...],
    }

    The result is the set of leaves which are at the intersection of the tree
    queries.

    """
    matches = None
    for tree_name, node_list in query.items():
        if not isinstance(node_list, (list, tuple)):
            node_list = [node_list]

        try:
            leaves = set()
            for node in node_list:
                leaves.update(leaves_below(trees[tree_name], node) or {node})

            if matches is None:
                matches = leaves
            else:
                matches = matches.intersection(leaves)
        except KeyError as err:
            raise KeyError('Cannot find node "{}" in tree "{}"'.format(
                err, tree_name))

    return matches


class Resolver:
    def __init__(self, df, column):
        self.df = df
        self.column = column

    def __iter__(self):
        # XXX hack to avoid __getitem__ being called with integer indices, but
        # to have non-zero len.
        return iter(['keys'])

    def __getitem__(self, k):
        if k == 'id':
            col = self.column
        else:
            col = '{}.{}'.format(self.column, k)
        return self.df[col]


def eval_selection(df, column, sel):
    if isinstance(sel, list):
        return df[column].isin(sel)
    elif isinstance(sel, str):
        resolver = Resolver(df, column)
        return df.eval(sel, local_dict={}, global_dict={}, resolvers=(resolver,))
    else:
        raise TypeError('Unknown selection type: %s' % type(sel))


class Dataset:
    def __init__(self, processes, flows, trees=None):
        self._processes = processes
        self._flows = flows

        self._table = flows \
            .join(processes.add_prefix('source.'), on='source') \
            .join(processes.add_prefix('target.'), on='target')
        # self._trees = trees

    def find_flows(self, source_query, target_query, flow_query=None, ignore_edges=None):
        """Filter flows according to source_query, target_query, and flow_query.
        """
        flows = self._table

        # n1 = leaves_matching_query(self._trees, q1)
        # n2 = leaves_matching_query(self._trees, q2)
        n1 = source_query
        n2 = target_query

        if source_query is None and target_query is None:
            raise ValueError('source_query and target_query cannot both be None')
        if source_query is None:
            qs = ~flows.index.isin(ignore_edges or [])
        else:
            qs = eval_selection(flows, 'source', source_query)
        if target_query is None:
            qt = ~flows.index.isin(ignore_edges or [])
        else:
            qt = eval_selection(flows, 'target', target_query)

        f = flows[qs & qt]
        if source_query is None:
            internal_source = None
        else:
            internal_source = flows[qs & eval_selection(flows, 'target', source_query)]
        if target_query is None:
            internal_target = None
        else:
            internal_target = flows[qt & eval_selection(flows, 'source', target_query)]

        if flow_query:
            raise NotImplementedError()

        return f, internal_source, internal_target

    def grouping(self, dimension, processes=None):
        """Grouping of all values of `dimension` within `processes`"""
        if processes:
            q = self._table.source.isin(processes) | self._table.target.isin(processes)
            values = self._table.loc[q, dimension].unique()
        else:
            values = self._table[dimension].unique()
        return Grouping.Simple(dimension, values)

    def save(self, filename):
        with pd.HDFStore(filename) as store:
            store['processes'] = self._processes
            store['flows'] = self._flows

    @classmethod
    def from_hdf(cls, filename):
        with pd.HDFStore(filename) as store:
            return cls(store['processes'], store['flows'])

    @classmethod
    def from_csv(cls, flows_filename, processes_filename):
        flows = pd.read_csv(flows_filename)
        processes = pd.read_csv(processes_filename).set_index('id')
        return cls(processes, flows)
