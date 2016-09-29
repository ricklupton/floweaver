import pytest

from sankeyview.view_definition import ViewDefinition
from sankeyview.ordering import Ordering
from sankeyview.bundle import Bundle, Elsewhere
from sankeyview.node_group import NodeGroup


def test_view_definition():
    node_groups = {}
    bundles = {}
    ordering = Ordering([])
    vd = ViewDefinition(node_groups, bundles, ordering)
    assert vd.node_groups is node_groups
    assert vd.bundles is bundles
    assert vd.ordering is ordering


def test_view_definition_checks_bundles():
    node_groups = {
        'a': NodeGroup(selection=('a1')),
        'b': NodeGroup(selection=('b1')),
        'waypoint': NodeGroup(),
    }
    ordering = Ordering([])

    with pytest.raises(ValueError):
        bundles = {
            0: Bundle('waypoint', 'b')
        }
        ViewDefinition(node_groups, bundles, ordering)

    with pytest.raises(ValueError):
        bundles = {
            0: Bundle('b', 'waypoint')
        }
        ViewDefinition(node_groups, bundles, ordering)

    # should work
    bundles = {
        0: Bundle('a', 'b')
    }
    assert ViewDefinition(node_groups, bundles, ordering)

    # also accepts a list
    bundles = [Bundle('a', 'b')]
    assert ViewDefinition(node_groups, bundles, ordering).bundles == {0: Bundle('a', 'b')}


def test_view_definition_checks_node_groups_exist():
    node_groups = {
        'a': NodeGroup(selection=('a1')),
        'b': NodeGroup(selection=('b1')),
        'waypoint': NodeGroup(),
    }
    ordering = Ordering([])

    with pytest.raises(ValueError):
        bundles = [
            Bundle('does not exist', 'b')
        ]
        ViewDefinition(node_groups, bundles, ordering)

    with pytest.raises(ValueError):
        bundles = [
            Bundle('a', 'b', waypoints=['does not exist'])
        ]
        ViewDefinition(node_groups, bundles, ordering)



def test_view_definition_normalises_order():
    node_groups = {'a': NodeGroup(), 'b': NodeGroup(), 'c': NodeGroup()}

    # two levels (no bands) --> normalised 3-level
    vd = ViewDefinition(node_groups, [], [ ['a', 'b'], ['c'] ])
    assert vd.ordering == Ordering([ [['a', 'b']], [['c']] ])

    # three levels --> unaltered
    vd = ViewDefinition(node_groups, [], [ [['a', 'b']], [['c']] ])
    assert vd.ordering == Ordering([ [['a', 'b']], [['c']] ])


# def test_view_definition_merge():
#     vd1 = ViewDefinition({'a': NodeGroup(selection=True), 'b': NodeGroup(selection=True)},
#                          {'0': Bundle('a', 'b')},
#                          [['a'], ['b']])

#     vd2 = vd1.merge(nodes={'c': NodeGroup(selection=True, title='C')},
#                     bundles={'1': Bundle('a', 'c')})

#     assert vd2.nodes == {'a': NodeGroup(selection=True),
#                          'b': NodeGroup(selection=True),
#                          'c': NodeGroup(selection=True, title='C')}

#     assert vd2.bundles == {'0': Bundle('a', 'b'),
#                            '1': Bundle('a', 'c')}

