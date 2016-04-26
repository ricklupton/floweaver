import itertools
import networkx as nx
from palettable.colorbrewer import qualitative

from .utils import pairwise
from .node import Node
from .bundle import Bundle
from .grouping import Grouping
from .low_level_graph import low_level_graph


class _Elsewhere:
    def __repr__(self):
        return '<Elsewhere>'
Elsewhere = _Elsewhere()
del _Elsewhere


class SankeyView:
    def __init__(self, nodes, bundles, dividers=None):
        if dividers is None:
            dividers = []
        self.dividers = dividers

        self.high_level = nx.DiGraph()
        self.dummy_nodes = set()

        for bundle in bundles:
            if bundle.source is not Elsewhere and not nodes[bundle.source].query:
                raise ValueError('bundle {} - {}: source must define query'
                                 .format(bundle.source, bundle.target))
            if bundle.target is not Elsewhere and not nodes[bundle.target].query:
                raise ValueError('bundle {} - {}: target must define query'
                                 .format(bundle.source, bundle.target))

        for k, node in nodes.items():
            self.high_level.add_node(k, node=node)

        self.bundles = list(bundles)
        self._add_elsewhere_bundles()
        for bundle in self.bundles:
            self._add_waypoints_to_bundle(bundle)

    @property
    def nodes(self):
        return (self.high_level.node[u]['node'] for u in self.high_level.nodes())

    def build(self, dataset, flow_grouping=None):
        # XXX mutates bundle objects

        # XXX used_edges logic isn't right -- there won't ever be any unused
        # edges because the implicit Elsewhere bundles always use them up?
        used_edges = set()
        used_internal = set()
        used_nodes = set()
        for bundle in self.bundles:
            if bundle.source is Elsewhere or bundle.target is Elsewhere:
                continue  # do these afterwards
            source = self.high_level.node[bundle.source]['node']
            target = self.high_level.node[bundle.target]['node']
            bundle.flows, internal_source, internal_target = \
                dataset.find_flows(source.query, target.query, bundle.flow_query)
            assert len(used_edges.intersection(bundle.flows.index.values)) == 0, 'duplicate bundle'
            used_edges.update(bundle.flows.index.values)
            used_nodes.update(bundle.flows.source)
            used_nodes.update(bundle.flows.target)
            # Also marked internal edges as "used"
            used_internal.update(internal_source.index.values)
            used_internal.update(internal_target.index.values)

        for bundle in self.bundles:
            if bundle.source is Elsewhere and bundle.target is Elsewhere:
                raise ValueError('Cannot have flow from Elsewhere to Elsewhere')
            elif bundle.source is Elsewhere:
                target = self.high_level.node[bundle.target]['node']
                bundle.flows, _, _ = dataset.find_flows(None, target.query, bundle.flow_query, used_edges)
            elif bundle.target is Elsewhere:
                source = self.high_level.node[bundle.source]['node']
                bundle.flows, _, _ = dataset.find_flows(source.query, None, bundle.flow_query, used_edges)

        # Check set of nodes
        relevant_flows = dataset._flows[dataset._flows.source.isin(used_nodes) &
                                        dataset._flows.target.isin(used_nodes)]
        self.unused_flows = relevant_flows[~relevant_flows.index.isin(used_edges) &
                                           ~relevant_flows.index.isin(used_internal)]

        return low_level_graph(self.high_level, flow_grouping, self.dividers)

    def graph_to_sankey(self, G, order, color_key='material', palette=None):
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
            basename, part = u.split('^', 1)
            processes.append({
                'id': u,
                'title': part if part != '*' else basename,
                'style': data.get('type', 'default'),
                'direction': 'l' if data.get('reversed') else 'r',
                'visibility': 'hidden' if basename in self.dummy_nodes else 'visible',
            })

        return {'processes': processes, 'flows': flows, 'order': order}

    def _add_waypoints_to_bundle(self, bundle):
        """Make all bundles tight by adding waypoints"""
        nodes = [bundle.source] + bundle.waypoints + [bundle.target]
        for a, b in pairwise(nodes):
            if a is Elsewhere or b is Elsewhere:
                # No need to add waypoints to get to Elsewhere -- it is
                # everywhere!
                continue

            V = self.high_level.node[a]['node']
            W = self.high_level.node[b]['node']
            new_ranks = interpolate_ranks(V, W)

            new_nodes = [
                ('{}_{}_{}'.format(a, b, rank), Node(rank, y, reversed=rev,
                                                     grouping=bundle.default_grouping or Grouping.All))
                for rank, y, rev in new_ranks
            ]

            for k, node in new_nodes:
                self.high_level.add_node(k, node=node)
                self.dummy_nodes.add(k)

            segment_nodes = [a] + [k for k, node in new_nodes] + [b]
            for aa, bb in pairwise(segment_nodes):
                if self.high_level.has_edge(aa, bb):
                    self.high_level[aa][bb]['bundles'].append(bundle)
                else:
                    self.high_level.add_edge(aa, bb, bundles=[bundle])

    def _add_elsewhere_bundles(self):
        # Build dict of existing bundles to/from elsewhere
        has_to_elsewhere = set()
        has_from_elsewhere = set()
        has_to_other = set()
        has_from_other = set()
        for bundle in self.bundles:
            assert not (bundle.source is Elsewhere and bundle.target is Elsewhere)
            if bundle.target is Elsewhere:
                if bundle.source in has_to_elsewhere:
                    raise ValueError('duplicate bundles to elsewhere from {}'.format(bundle.source))
                has_to_elsewhere.add(bundle.source)
            else:
                has_to_other.add(bundle.source)
            if bundle.source is Elsewhere:
                if bundle.target in has_from_elsewhere:
                    raise ValueError('duplicate bundles from elsewhere to {}'.format(bundle.target))
                has_from_elsewhere.add(bundle.target)
            else:
                has_from_other.add(bundle.target)

        # For each node, add new bundles to/from elsewhere if not already
        # existing. Each one should have a waypoint of rank +/- 1.
        min_rank = min(node.rank for node in self.nodes)
        max_rank = max(node.rank for node in self.nodes)
        for u, data in self.high_level.nodes(data=True):
            node = data['node']
            if not node.query:
                continue  # no waypoints
            d_rank = +1 if not node.reversed else -1
            if u not in has_to_elsewhere and (min_rank < node.rank < max_rank or
                                              u in has_to_other):
                waypoint = 'from {}'.format(u)
                self.high_level.add_node(
                    waypoint,
                    node=Node(node.rank + d_rank, node.order, node.reversed))
                self.bundles.append(Bundle(u, Elsewhere, waypoints=[waypoint]))
            if u not in has_from_elsewhere and (min_rank < node.rank < max_rank or
                                                u in has_from_other):
                waypoint = 'to {}'.format(u)
                self.high_level.add_node(
                    waypoint,
                    node=Node(node.rank - d_rank, node.order, node.reversed))
                self.bundles.append(Bundle(Elsewhere, u, waypoints=[waypoint]))


def interpolate_ranks(V, W):
    r = V.rank
    yv = V.order
    yw = W.order
    new_ranks = []

    if r + 1 <= W.rank:
        # add more to get forwards
        if V.reversed:
            yv = yw if yw != yv else yw - 1  # move up starting position
            new_ranks.append((r, False))  # turn around
        while r + 1 < W.rank:
            r += 1
            new_ranks.append((r, False))
        r += 1
        if W.reversed:
            yw = yv if yv != yw else yw - 1
            new_ranks.append((r, False))  # turn around

        if V.reversed and W.reversed:
            yv = yw = min(V.order, W.order) - 1

    elif r > W.rank:
        # add more to get backwards
        if not V.reversed:
            yv = yw if yw != yv else yw + 1  # move down starting position
            new_ranks.append((r, True))
        while r > W.rank + 1:
            r -= 1
            new_ranks.append((r, True))
        r -= 1
        if not W.reversed:
            yw = yv if yv != yw else yv + 1
            new_ranks.append((r, True))

        if not V.reversed and not W.reversed:
            yv = yw = max(V.order, W.order) + 1

    # Linearly interpolate order between yv and yw
    def y(r):
        return yv + (yw - yv) / (W.rank - V.rank) * (r - V.rank)
    new_ranks = [(r, y(r), d) for r, d in new_ranks]

    return new_ranks


