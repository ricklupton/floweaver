from collections import namedtuple
import sentinel

from .utils import pairwise


Elsewhere = sentinel.create('Elsewhere')


class Bundle(namedtuple('Bundle', 'source, target, waypoints, flow_selection, flow_grouping, default_grouping')):
    __slots__ = ()
    def __new__(cls, source, target, waypoints=None, flow_selection=None,
                flow_grouping=None, default_grouping=None):
        if waypoints is None:
            waypoints = ()
        waypoints = tuple(waypoints)
        return super().__new__(cls, source, target, waypoints, flow_selection,
                               flow_grouping, default_grouping)

    def __repr__(self):
        return '<Bundle {} {} via {} flow_sel={}>'.format(
            self.source, self.target, self.waypoints, self.flow_selection)

    # def __lt__(self, other):
    #     return (self.source, self.target) < (other.source, other.target)

    @property
    def to_elsewhere(self):
        return self.target is Elsewhere

    @property
    def from_elsewhere(self):
        return self.source is Elsewhere

    # def get_segments(self):
    #     nodes = [self.source] + self.waypoints + [self.target]
    #     return [BundleSegment(a, b, self) for a, b in pairwise(nodes)]

    # def _get_flows(self, dataset):
    #     self.flows = dataset.find_flows(self.source.query, self.target.query, self.flow_query)

class BundleSegment:
    def __init__(self, source, target, bundle):
        self.source = source
        self.target = target
        self.bundle = bundle

    def __eq__(self, other):
        return isinstance(other, BundleSegment) and (
            self.source == other.source and self.target == other.target and
            self.bundle == other.bundle)
