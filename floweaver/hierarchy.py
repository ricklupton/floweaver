import networkx as nx


class Hierarchy:
    def __init__(self, tree, column):
        self.tree = tree
        self.column = column

    def _leaves_below(self, node):
        leaves = sum(([vv for vv in v if self.tree.out_degree(vv) == 0]
                      for k, v in nx.dfs_successors(self.tree, node).items()),
                     [])
        return sorted(leaves) or [node]

    def __call__(self, *nodes):
        """Return process IDs below the given nodes in the tree"""
        s = set()
        for node in nodes:
            if self.tree.in_degree(node) == 0:
                return None  # all
            s.update(self._leaves_below(node))

        if len(s) == 1:
            query = '{} == "{}"'.format(self.column, s.pop())
        else:
            query = '{} in {}'.format(self.column, repr(sorted(s)))
        return query
