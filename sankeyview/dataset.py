import pandas as pd
import networkx as nx

from .partition import Partition


def leaves_below(tree, node):
    return set(sum(([vv for vv in v if tree.out_degree(vv) == 0]
                    for k, v in nx.dfs_successors(tree, node).items()), []))


class Resolver:
    def __init__(self, df, column):
        self.df = df
        self.column = column

    def __iter__(self):
        # XXX hack to avoid __getitem__ being called with integer indices, but
        # to have non-zero len.
        return iter(['keys'])

    def __getitem__(self, k):
        if not self.column:
            col = k
        elif k == 'id':
            col = self.column
        else:
            col = '{}.{}'.format(self.column, k)
        return self.df[col]


def eval_selection(df, column, sel):
    if isinstance(sel, (list, tuple)):
        return df[column].isin(sel)
    elif isinstance(sel, str):
        resolver = Resolver(df, column)
        return df.eval(sel,
                       local_dict={},
                       global_dict={},
                       resolvers=(resolver, ))
    else:
        raise TypeError('Unknown selection type: %s' % type(sel))


class Dataset:
    def __init__(self, processes, flows):
        self._processes = processes
        self._flows = flows

        self._table = flows \
            .join(processes.add_prefix('source.'), on='source') \
            .join(processes.add_prefix('target.'), on='target')

    def partition(self, dimension, processes=None):
        """Partition of all values of `dimension` within `processes`"""
        if processes:
            q = (self._table.source.isin(processes) |
                 self._table.target.isin(processes))
            values = self._table.loc[q, dimension].unique()
        else:
            values = self._table[dimension].unique()
        return Partition.Simple(dimension, values)

    def apply_view(self, process_groups, bundles, flow_selection=None):
        return _apply_view(self, process_groups, bundles, flow_selection)

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


def find_flows(flows,
               source_query,
               target_query,
               flow_query=None,
               ignore_edges=None):
    """Filter flows according to source_query, target_query, and flow_query.
    """
    if flow_query is not None:
        flows = flows[eval_selection(flows, '', flow_query)]

    if source_query is None and target_query is None:
        raise ValueError('source_query and target_query cannot both be None')

    elif source_query is None and target_query is not None:
        qt = eval_selection(flows, 'target', target_query)
        qs = (~eval_selection(flows, 'source', target_query) &
              ~flows.index.isin(ignore_edges or []))

    elif source_query is not None and target_query is None:
        qs = eval_selection(flows, 'source', source_query)
        qt = (~eval_selection(flows, 'target', source_query) &
              ~flows.index.isin(ignore_edges or []))

    else:
        qs = eval_selection(flows, 'source', source_query)
        qt = eval_selection(flows, 'target', target_query)

    f = flows[qs & qt]
    if source_query is None:
        internal_source = None
    else:
        internal_source = flows[qs & eval_selection(flows, 'target',
                                                    source_query)]
    if target_query is None:
        internal_target = None
    else:
        internal_target = flows[qt & eval_selection(flows, 'source',
                                                    target_query)]

    return f, internal_source, internal_target


def _apply_view(dataset, process_groups, bundles, flow_selection):
    # What we want to warn about is flows between process_groups in the view_graph; they
    # are "used", since they appear in Elsewhere bundles, but the connection
    # isn't visible.

    used_edges = set()
    used_internal = set()
    used_process_groups = set()
    bundle_flows = {}

    table = dataset._table
    if flow_selection:
        table = table[eval_selection(table, '', flow_selection)]

    for k, bundle in bundles.items():
        if bundle.from_elsewhere or bundle.to_elsewhere:
            continue  # do these afterwards

        source = process_groups[bundle.source]
        target = process_groups[bundle.target]
        flows, internal_source, internal_target = \
            find_flows(table, source.selection, target.selection, bundle.flow_selection)
        assert len(used_edges.intersection(
            flows.index.values)) == 0, 'duplicate bundle'
        bundle_flows[k] = flows
        used_edges.update(flows.index.values)
        used_process_groups.update(flows.source)
        used_process_groups.update(flows.target)
        # Also marked internal edges as "used"
        used_internal.update(internal_source.index.values)
        used_internal.update(internal_target.index.values)

    for k, bundle in bundles.items():
        if bundle.from_elsewhere and bundle.to_elsewhere:
            raise ValueError('Cannot have flow from Elsewhere to Elsewhere')

        elif bundle.from_elsewhere:
            target = process_groups[bundle.target]
            flows, _, _ = find_flows(table, None, target.selection,
                                     bundle.flow_selection, used_edges)
            used_process_groups.add(bundle.target)

        elif bundle.to_elsewhere:
            source = process_groups[bundle.source]
            flows, _, _ = find_flows(table, source.selection, None,
                                     bundle.flow_selection, used_edges)
            used_process_groups.add(bundle.source)

        else:
            continue

        bundle_flows[k] = flows

    # XXX shouldn't this check processes in selections, not process groups?
    # Check set of process_groups
    relevant_flows = dataset._flows[dataset._flows.source.isin(
        used_process_groups) & dataset._flows.target.isin(used_process_groups)]
    unused_flows = relevant_flows[~relevant_flows.index.isin(used_edges) &
                                  ~relevant_flows.index.isin(used_internal)]

    return bundle_flows, unused_flows
