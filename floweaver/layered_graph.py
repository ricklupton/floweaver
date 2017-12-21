import networkx as nx

from .sankey_definition import Ordering


class LayeredMixin(object):
    def __init__(self):
        super().__init__()
        self.ordering = Ordering([])

    def copy(self):
        new = super().copy()
        new.ordering = self.ordering
        return new

    def remove_node(self, u):
        super().remove_node(u)
        self.ordering = self.ordering.remove(u)

    def get_node(self, u):
        """Get the ProcessGroup or Waypoint associated with `u`"""
        return self.node[u]['node']


class LayeredGraph(LayeredMixin, nx.DiGraph):
    pass


class MultiLayeredGraph(LayeredMixin, nx.MultiDiGraph):
    pass
