from collections import namedtuple


class ViewDefinition(namedtuple('ViewDefinition', 'node_groups, bundles, order, flow_partition, flow_selection, time_partition')):
    __slots__ = ()

    def __new__(cls, node_groups, bundles, order, flow_partition=None,
                flow_selection=None, time_partition=None):

        if not isinstance(bundles, dict):
            bundles = {k: v for k, v in enumerate(bundles)}

        # Check bundles
        for b in bundles.values():
            if not b.from_elsewhere:
                if b.source not in node_groups:
                    raise ValueError('Unknown node_group "{}" in bundle'.format(b.source))
                if not node_groups[b.source].selection:
                    raise ValueError('b {} - {}: source must define selection'
                                     .format(b.source, b.target))
            if not b.to_elsewhere:
                if b.target not in node_groups:
                    raise ValueError('Unknown node_group "{}" in bundle'.format(b.target))
                if not node_groups[b.target].selection:
                    raise ValueError('b {} - {}: target must define selection'
                                     .format(b.source, b.target))
            for u in b.waypoints:
                if u not in node_groups:
                    raise ValueError('Unknown waypoint "{}" in bundle'.format(u))


        # Check order
        for item in order:
            if any(isinstance(x, str) for x in item):
                # Wrap in a single band
                order = [[rank] for rank in order]
                break

        for bands in order:
            for rank in bands:
                for u in rank:
                    if u not in node_groups:
                        raise ValueError('Unknown node_group "{}" in order'.format(u))

        return super(ViewDefinition, cls).__new__(cls, node_groups, bundles, order,
                                                  flow_partition, flow_selection, time_partition)

    def __repr__(self):
        return '<ViewDef {} node_groups, {} bundles>'.format(
            len(self.node_groups), len(self.bundles))

    def copy(self):
        order = [
            [rank[:] for rank in bands]
            for bands in self.order
        ]
        return self.__class__(self.node_groups.copy(), self.bundles.copy(),
                              order, self.flow_partition, self.flow_selection, self.time_partition)

    def merge(self, node_groups={}, bundles={}):
        return self.__class__(dict(self.node_groups, **node_groups),
                              dict(self.bundles, **bundles),
                              order,
                              self.flow_partition, self.flow_selection,
                              self.time_partition)

    def rank(self, u):
        for r, bands in enumerate(self.order):
            for rank in bands:
                if u in rank:
                    return r
        raise ValueError('node_group not in order')
