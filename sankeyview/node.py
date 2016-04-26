from collections import namedtuple
from .grouping import Grouping


class Node(namedtuple('Node', 'rank, order, reversed, query, grouping')):
    __slots__ = ()
    def __new__(cls, rank, order, reversed=False, query=None, grouping=None):
        if grouping is None:
            grouping = Grouping.All

        return super().__new__(cls, rank, order, reversed, query, grouping)

    def __repr__(self):
        return '<Node ({}, {}){} query={} grouping={}>'.format(
            self.rank, self.order, ' rev' if self.reversed else '', self.query,
            self.grouping)

    # def __eq__(self, other):
    #     return isinstance(other, Node) and (
    #         self.rank == other.rank and self.order == other.order and
    #         self.reversed == other.reversed and self.query == other.query and
    #         self.grouping == other.grouping)
