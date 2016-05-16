from collections import namedtuple


class ViewDefinition(namedtuple('ViewDefinition', 'nodes, bundles, order, flow_grouping')):
    __slots__ = ()

    def __new__(cls, nodes, bundles, order, flow_grouping=None):
        # Check bundles
        for b in bundles:
            if not b.from_elsewhere:
                if b.source not in nodes:
                    raise ValueError('Unknown node "{}" in bundle'.format(b.source))
                if not nodes[b.source].selection:
                    raise ValueError('b {} - {}: source must define selection'
                                     .format(b.source, b.target))
            if not b.to_elsewhere:
                if b.target not in nodes:
                    raise ValueError('Unknown node "{}" in bundle'.format(b.target))
                if not nodes[b.target].selection:
                    raise ValueError('b {} - {}: target must define selection'
                                     .format(b.source, b.target))
            for u in b.waypoints:
                if u not in nodes:
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
                    if u not in nodes:
                        raise ValueError('Unknown node "{}" in order'.format(u))

        return super(ViewDefinition, cls).__new__(cls, nodes, bundles, order,
                                                  flow_grouping)

    def __repr__(self):
        return '<ViewDef {} nodes, {} bundles>'.format(
            len(self.nodes), len(self.bundles))

    def copy(self):
        order = [
            [rank[:] for rank in bands]
            for bands in self.order
        ]
        return self.__class__(self.nodes.copy(), self.bundles[:],
                              order, self.flow_grouping)

    def rank(self, u):
        for r, bands in enumerate(self.order):
            for rank in bands:
                if u in rank:
                    return r
        raise ValueError('node not in order')
