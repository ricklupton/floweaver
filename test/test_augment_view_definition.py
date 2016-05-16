import pytest

from sankeyview.augment_view_definition import augment
from sankeyview.node import Node
from sankeyview.bundle import Bundle, Elsewhere
from sankeyview.grouping import Grouping
from sankeyview.view_definition import ViewDefinition


# For testing, disable checks on bundles; allows to have waypoints defining
# structure without getting too many extra to/from bundles
class UncheckedViewDefinition(ViewDefinition):
    def __new__(cls, nodes, bundles, order, flow_grouping=None):
        # bypass ViewDefinition __new__
        return super(ViewDefinition, cls).__new__(cls, nodes, bundles, order,
                                                  flow_grouping)


def test_augment_does_not_affect_min_max_rank():
    nodes = {'a': Node(selection=['a1']), }
    bundles = []
    order = [['a']]
    vd = ViewDefinition(nodes, bundles, order)
    assert augment(vd) == vd


def test_augment_does_not_affect_waypoints():
    nodes = {'waypoint': Node(), }
    bundles = []
    order = [[], ['waypoint'], []]
    vd = ViewDefinition(nodes, bundles, order)
    assert augment(vd) == vd


def test_augment_adds_elsewhere_bundles():
    nodes = {'a': Node(selection=['a1']), }
    bundles = []
    order = [[], ['a'], []]  # not at min/max rank
    vd = ViewDefinition(nodes, bundles, order)
    vd2 = augment(vd)

    assert set(vd2.nodes) == {'a', 'to a', 'from a'}
    assert vd2.order == [[['to a']], [['a']], [['from a']]]
    assert vd2.bundles == [
        Bundle('a',
               Elsewhere,
               waypoints=['from a']),
        Bundle(Elsewhere,
               'a',
               waypoints=['to a']),
    ]


def test_augment_adds_elsewhere_bundles_reversed():
    nodes = {'a': Node(selection=['a1'], direction='L'), }
    bundles = []
    order = [[], ['a'], []]  # not at min/max rank
    vd = ViewDefinition(nodes, bundles, order)
    vd2 = augment(vd)

    assert set(vd2.nodes) == {'a', 'to a', 'from a'}
    assert vd2.order == [[['from a']], [['a']], [['to a']]]
    assert vd2.bundles == [
        Bundle('a',
               Elsewhere,
               waypoints=['from a']),
        Bundle(Elsewhere,
               'a',
               waypoints=['to a']),
    ]


def test_augment_does_not_duplicate_elsewhere_bundles():
    nodes = {'a': Node(selection=('a1')), 'in': Node(), 'out': Node(), }
    bundles = [
        Bundle(Elsewhere,
               'a',
               waypoints=['in']),
        Bundle('a',
               Elsewhere,
               waypoints=['out']),
    ]
    order = [['in'], ['a'], ['out']]  # not at min/max rank
    vd = ViewDefinition(nodes, bundles, order)
    assert augment(vd) == vd


def test_augment_waypoint_alignment():
    # j -- a -- x
    #      b
    # k -- c -- y
    #
    # should insert "from b" betwen x and y
    # and "to b" between j and k
    nodes = {
        'a': Node(),
        'b': Node(selection=['b1']),
        'c': Node(),
        'x': Node(),
        'y': Node(),
        'j': Node(),
        'k': Node(),
    }
    bundles = [
        Bundle('j', 'a'),
        Bundle('k', 'c'),
        Bundle('a', 'x'),
        Bundle('c', 'y'),
    ]

    order = [[['j', 'k']], [['a', 'b', 'c']], [['x', 'y']]]
    vd = UncheckedViewDefinition(nodes, bundles, order)
    vd2 = augment(vd)

    assert set(vd2.nodes) == {'j', 'k', 'a', 'b', 'c', 'x', 'y', 'from b',
                              'to b'}
    assert vd2.order == [[['j', 'to b', 'k']], [['a', 'b', 'c']],
                         [['x', 'from b', 'y']]]
    assert vd2.bundles == vd.bundles + [
        Bundle('b',
               Elsewhere,
               waypoints=['from b']),
        Bundle(Elsewhere,
               'b',
               waypoints=['to b']),
    ]
