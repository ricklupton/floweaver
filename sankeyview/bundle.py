from .utils import pairwise


class Bundle:
    def __init__(self, source, target, flow_query=None, waypoints=None, flow_grouping=None,
                 default_grouping=None):
        if waypoints is None:
            waypoints = []

        self.source = source
        self.target = target
        self.flow_query = flow_query
        self.waypoints = waypoints
        self.flow_grouping = flow_grouping
        self.default_grouping = default_grouping
        self.flows = None

    def __repr__(self):
        return '<Bundle {} {} via {} flow_query={}>'.format(
            self.source, self.target, self.waypoints, self.flow_query)

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def get_segments(self):
        nodes = [self.source] + self.waypoints + [self.target]
        return [BundleSegment(a, b, self) for a, b in pairwise(nodes)]

    def _get_flows(self, dataset):
        self.flows = dataset.find_flows(self.source.query, self.target.query, self.flow_query)

class BundleSegment:
    def __init__(self, source, target, bundle):
        self.source = source
        self.target = target
        self.bundle = bundle

    def __eq__(self, other):
        return isinstance(other, BundleSegment) and (
            self.source == other.source and self.target == other.target and
            self.bundle == other.bundle)
