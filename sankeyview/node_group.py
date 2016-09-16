from collections import namedtuple
from .partition import Partition


class NodeGroup(namedtuple('NodeGroup', 'direction, selection, partition, title')):
    __slots__ = ()
    def __new__(cls, direction='R', selection=None, partition=None, title=None):
        if direction not in 'LR':
            raise ValueError('direction must be L or R')
        if partition is None:
            partition = Partition.All

        return super().__new__(cls, direction, selection, partition, title)

    def __repr__(self):
        return '<NodeGroup {} {}selection={} partition={}>'.format(
            self.direction, '"{}" '.format(self.title) if self.title else '',
            self.selection, self.partition)

    # def __eq__(self, other):
    #     return isinstance(other, NodeGroup) and (
    #         self.rank == other.rank and self.order == other.order and
    #         self.reversed == other.reversed and self.query == other.query and
    #         self.partition == other.partition)
