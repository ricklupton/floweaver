from collections import namedtuple
from .grouping import Grouping


class Node(namedtuple('Node', 'direction, selection, grouping, title')):
    __slots__ = ()
    def __new__(cls, direction='R', selection=None, grouping=None, title=None):
        if direction not in 'LR':
            raise ValueError('direction must be L or R')
        if grouping is None:
            grouping = Grouping.All

        return super().__new__(cls, direction, selection, grouping, title)

    def __repr__(self):
        return '<Node {} {}selection={} grouping={}>'.format(
            self.direction, '"{}" '.format(self.title) if self.title else '',
            self.selection, self.grouping)

    # def __eq__(self, other):
    #     return isinstance(other, Node) and (
    #         self.rank == other.rank and self.order == other.order and
    #         self.reversed == other.reversed and self.query == other.query and
    #         self.grouping == other.grouping)
