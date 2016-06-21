import pytest

from sankeyview.view_definition import ViewDefinition
from sankeyview.bundle import Bundle, Elsewhere
from sankeyview.node import Node


def test_view_definition():
    nodes = {}
    bundles = {}
    order = []
    vd = ViewDefinition(nodes, bundles, order)
    assert vd.nodes is nodes
    assert vd.bundles is bundles
    assert vd.order is order


def test_view_definition_checks_bundles():
    nodes = {
        'a': Node(selection=('a1')),
        'b': Node(selection=('b1')),
        'waypoint': Node(),
    }
    order = []

    with pytest.raises(ValueError):
        bundles = {
            0: Bundle('waypoint', 'b')
        }
        ViewDefinition(nodes, bundles, order)

    with pytest.raises(ValueError):
        bundles = {
            0: Bundle('b', 'waypoint')
        }
        ViewDefinition(nodes, bundles, order)

    # should work
    bundles = {
        0: Bundle('a', 'b')
    }
    assert ViewDefinition(nodes, bundles, order)

    # also accepts a list
    bundles = [Bundle('a', 'b')]
    assert ViewDefinition(nodes, bundles, order).bundles == {0: Bundle('a', 'b')}


def test_view_definition_checks_nodes_exist():
    nodes = {
        'a': Node(selection=('a1')),
        'b': Node(selection=('b1')),
        'waypoint': Node(),
    }
    order = []

    with pytest.raises(ValueError):
        bundles = [
            Bundle('does not exist', 'b')
        ]
        ViewDefinition(nodes, bundles, order)

    with pytest.raises(ValueError):
        bundles = [
            Bundle('a', 'b', waypoints=['does not exist'])
        ]
        ViewDefinition(nodes, bundles, order)



def test_view_definition_normalises_order():
    nodes = {'a': Node(), 'b': Node(), 'c': Node()}

    # two levels (no bands) --> normalised 3-level
    vd = ViewDefinition(nodes, [], [ ['a', 'b'], ['c'] ])
    assert vd.order == [ [['a', 'b']], [['c']] ]

    # three levels --> unaltered
    vd = ViewDefinition(nodes, [], [ [['a', 'b']], [['c']] ])
    assert vd.order == [ [['a', 'b']], [['c']] ]


# def test_view_definition_merge():
#     vd1 = ViewDefinition({'a': Node(selection=True), 'b': Node(selection=True)},
#                          {'0': Bundle('a', 'b')},
#                          [['a'], ['b']])

#     vd2 = vd1.merge(nodes={'c': Node(selection=True, title='C')},
#                     bundles={'1': Bundle('a', 'c')})

#     assert vd2.nodes == {'a': Node(selection=True),
#                          'b': Node(selection=True),
#                          'c': Node(selection=True, title='C')}

#     assert vd2.bundles == {'0': Bundle('a', 'b'),
#                            '1': Bundle('a', 'c')}
