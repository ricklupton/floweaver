from collections import namedtuple
import networkx as nx


class Grouping(namedtuple('Grouping', 'groups')):
    __slots__ = ()

    def __new__(cls, *groups):
        return super().__new__(cls, groups)

    @property
    def labels(self):
        return [g.label for g in self.groups]

    @classmethod
    def Simple(cls, dimension, values):
        groups = [Group(v, (dimension, (v,))) for v in values]
        return Grouping(*groups)

    def __add__(self, other):
        return Grouping(*(self.groups + other.groups))

    def __mul__(self, other):
        """Cartesian product"""
        groups = [Group('{}/{}'.format(g1.label, g2.label), *(g1.query + g2.query))
                  for g1 in self.groups
                  for g2 in other.groups]
        return Grouping(*groups)

    def __copy__(self):
        return self

    def __deepcopy__(self, memo):
        return self


class Group(namedtuple('Group', 'label, query')):
    __slots__ = ()

    def __new__(cls, label, *query):
        return super().__new__(cls, label, query)


Grouping.All = Grouping(Group('*'))


class Hierarchy:
    def __init__(self, dimension, tree, dataset):
        self.dimension = dimension
        self.tree = tree
        self.dataset = dataset

    def _leaves_below(self, node):
        leaves = sum(([vv for vv in v if self.tree.out_degree(vv) == 0]
                      for k, v in nx.dfs_successors(self.tree, node).items()), [])
        return sorted(leaves) or [node]

    def selection(self, *nodes):
        """Return process IDs below the given nodes in the tree"""
        s = []
        assert self.dimension.startswith('node.')
        dim = self.dimension[5:]
        for node in nodes:
            if node in self.tree:
                leaves = self._leaves_below(node)
                ids = self.dataset._processes[
                    self.dataset._processes[dim].isin(leaves)].index
                if len(ids) == 0:
                    raise ValueError('No processes found for {}={} -> {}'
                                     .format(dim, node, leaves))
            else:
                # assume it's a node id
                ids = [node]
            s.extend(ids)
        return s

    def grouping(self, *nodes):
        groups = []
        for node in nodes:
            if node in self.tree:
                groups.append(Group(node, (self.dimension, self._leaves_below(node))))
            else:
                groups.append(Group(node, ('node', [node])))
        return Grouping(*groups)
