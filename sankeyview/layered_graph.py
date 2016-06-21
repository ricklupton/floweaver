import networkx as nx


class LayeredGraph(nx.DiGraph):
    def __init__(self):
        super().__init__()
        self.order = []

    def copy(self):
        new = super().copy()
        new.order = [[list(rank) for rank in bands] for bands in self.order]
        return new


class MultiLayeredGraph(nx.MultiDiGraph):
    def __init__(self):
        super().__init__()
        self.order = []

    def copy(self):
        new = super().copy()
        new.order = [[list(rank) for rank in bands] for bands in self.order]
        return new
