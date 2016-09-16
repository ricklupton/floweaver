import pytest

from sankeyview.view_definition import ViewDefinition
from sankeyview.bundle import Bundle, Elsewhere
from sankeyview.node_group import NodeGroup


def test_view_definition():
    node_groups = {}
    bundles = {}
    order = []
    vd = ViewDefinition(node_groups, bundles, order)
    assert vd.node_groups is node_groups
    assert vd.bundles is bundles
    assert vd.order is order


def test_view_definition_checks_bundles():
    node_groups = {
        'a': NodeGroup(selection=('a1')),
        'b': NodeGroup(selection=('b1')),
        'waypoint': NodeGroup(),
    }
    order = []

    with pytest.raises(ValueError):
        bundles = {
            0: Bundle('waypoint', 'b')
        }
        ViewDefinition(node_groups, bundles, order)

    with pytest.raises(ValueError):
        bundles = {
            0: Bundle('b', 'waypoint')
        }
        ViewDefinition(node_groups, bundles, order)

    # should work
    bundles = {
        0: Bundle('a', 'b')
    }
    assert ViewDefinition(node_groups, bundles, order)

    # also accepts a list
    bundles = [Bundle('a', 'b')]
    assert ViewDefinition(node_groups, bundles, order).bundles == {0: Bundle('a', 'b')}


def test_view_definition_checks_node_groups_exist():
    node_groups = {
        'a': NodeGroup(selection=('a1')),
        'b': NodeGroup(selection=('b1')),
        'waypoint': NodeGroup(),
    }
    order = []

    with pytest.raises(ValueError):
        bundles = [
            Bundle('does not exist', 'b')
        ]
        ViewDefinition(node_groups, bundles, order)

    with pytest.raises(ValueError):
        bundles = [
            Bundle('a', 'b', waypoints=['does not exist'])
        ]
        ViewDefinition(node_groups, bundles, order)



def test_view_definition_normalises_order():
    node_groups = {'a': NodeGroup(), 'b': NodeGroup(), 'c': NodeGroup()}

    # two levels (no bands) --> normalised 3-level
    vd = ViewDefinition(node_groups, [], [ ['a', 'b'], ['c'] ])
    assert vd.order == [ [['a', 'b']], [['c']] ]

    # three levels --> unaltered
    vd = ViewDefinition(node_groups, [], [ [['a', 'b']], [['c']] ])
    assert vd.order == [ [['a', 'b']], [['c']] ]


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
