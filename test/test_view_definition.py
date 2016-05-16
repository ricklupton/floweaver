import pytest

from sankeyview.view_definition import ViewDefinition
from sankeyview.bundle import Bundle, Elsewhere
from sankeyview.node import Node


def test_view_definition():
    nodes = {}
    bundles = []
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
        bundles = [
            Bundle('waypoint', 'b')
        ]
        ViewDefinition(nodes, bundles, order)

    with pytest.raises(ValueError):
        bundles = [
            Bundle('b', 'waypoint')
        ]
        ViewDefinition(nodes, bundles, order)

    # should work
    bundles = [
        Bundle('a', 'b')
    ]
    assert ViewDefinition(nodes, bundles, order)


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
