import pytest

from sankeyview.augment_view_graph import augment, elsewhere_bundles
from sankeyview.node_group import NodeGroup
from sankeyview.bundle import Bundle, Elsewhere
from sankeyview.partition import Partition
from sankeyview.view_definition import ViewDefinition
from sankeyview.view_graph import view_graph


# For testing, disable checks on bundles; allows to have waypoints defining
# structure without getting too many extra to/from bundles
class UncheckedViewDefinition(ViewDefinition):
    def __new__(cls, node_groups, bundles, order, flow_partition=None,
                flow_selection=None, time_partition=None):
        # bypass ViewDefinition __new__
        return super(ViewDefinition, cls).__new__(
            cls, node_groups, bundles, order, flow_partition, flow_selection, time_partition)


def test_elsewhere_bundles_are_added_when_no_bundles_defined():
    # make it easier to get started
    node_groups = {'a': NodeGroup(selection=['a1']), }
    bundles = {}
    order = [['a']]
    vd = ViewDefinition(node_groups, bundles, order)
    new_node_groups, new_bundles = elsewhere_bundles(vd)
    assert len(new_bundles) == 2


def test_elsewhere_bundles_not_added_at_min_max_rank_if_at_least_one_bundle_is_defined():
    node_groups = {'a': NodeGroup(selection=['a1'])}
    bundles = {0: Bundle('a', Elsewhere)}
    order = [['a']]
    vd = ViewDefinition(node_groups, bundles, order)
    new_node_groups, new_bundles = elsewhere_bundles(vd)
    assert len(new_node_groups) == 0
    assert len(new_bundles) == 0


def test_elsewhere_bundles_not_added_to_waypoints():
    node_groups = {'waypoint': NodeGroup(), }
    bundles = {}
    order = [[], ['waypoint'], []]
    vd = ViewDefinition(node_groups, bundles, order)
    new_node_groups, new_bundles = elsewhere_bundles(vd)
    assert new_node_groups == {}
    assert new_bundles == {}


def test_elsewhere_bundles():
    node_groups = {'a': NodeGroup(selection=['a1']), }
    bundles = {}
    order = [[], ['a'], []]  # not at min/max rank
    vd = ViewDefinition(node_groups, bundles, order)
    new_node_groups, new_bundles = elsewhere_bundles(vd)
    assert set(new_node_groups.keys()) == {'__a>', '__>a'}
    assert set(new_bundles.values()) == {
        Bundle('a',
               Elsewhere,
               waypoints=['__a>']),
        Bundle(Elsewhere,
               'a',
               waypoints=['__>a']),
    }

    # assert set(vd2.nodes) == {'a', 'to a', 'from a'}
    # assert vd2.order == [[['to a']], [['a']], [['from a']]]
    # assert vd2.bundles == [
    # ]


def test_elsewhere_bundles_does_not_duplicate():
    node_groups = {'a': NodeGroup(selection=('a1')), 'in': NodeGroup(), 'out': NodeGroup(), }
    bundles = {
        0: Bundle(Elsewhere,
                  'a',
                  waypoints=['in']),
        1: Bundle('a',
                  Elsewhere,
                  waypoints=['out']),
    }
    order = [['in'], ['a'], ['out']]  # not at min/max rank
    vd = ViewDefinition(node_groups, bundles, order)
    new_node_groups, new_bundles = elsewhere_bundles(vd)
    assert new_bundles == {}


def test_augment_waypoint_alignment():
    # j -- a -- x
    #      b
    # k -- c -- y
    #
    # should insert "from b" betwen x and y
    # and "to b" between j and k
    node_groups = {
        'a': NodeGroup(),
        'b': NodeGroup(selection=['b1']),
        'c': NodeGroup(),
        'x': NodeGroup(),
        'y': NodeGroup(),
        'j': NodeGroup(),
        'k': NodeGroup(),
    }
    bundles = {
        0: Bundle('j', 'a'),
        1: Bundle('k', 'c'),
        2: Bundle('a', 'x'),
        3: Bundle('c', 'y'),
    }

    order = [[['j', 'k']], [['a', 'b', 'c']], [['x', 'y']]]
    vd = UncheckedViewDefinition(node_groups, bundles, order)

    G, _ = view_graph(vd)
    new_node_groups = {
        'from b': NodeGroup(),
        'to b': NodeGroup(),
    }
    new_bundles = {
        'b>': Bundle('b',
                     Elsewhere,
                     waypoints=['from b']),
        '>b': Bundle(Elsewhere,
                     'b',
                     waypoints=['to b']),
    }

    G2 = augment(G, new_node_groups, new_bundles)

    assert set(G2.nodes()).difference(G.nodes()) == {'from b', 'to b'}
    assert G2.order == [
        [['j', 'to b', 'k']],
        [['a', 'b', 'c']],
        [['x', 'from b', 'y']]
    ]


# def test_augment_adds_elsewhere_bundles_reversed():
#     node_groups = {'a': NodeGroup(selection=['a1'], direction='L'), }
#     bundles = []
#     order = [[], ['a'], []]  # not at min/max rank
#     vd = ViewDefinition(node_groups, bundles, order)
#     vd2 = augment(vd)

#     assert set(vd2.node_groups) == {'a', 'to a', 'from a'}
#     assert vd2.order == [[['from a']], [['a']], [['to a']]]
#     assert vd2.bundles == [
#         Bundle('a',
#                Elsewhere,
#                waypoints=['from a']),
#         Bundle(Elsewhere,
#                'a',
#                waypoints=['to a']),
#     ]

