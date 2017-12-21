import pytest

from floweaver.sankey_definition import SankeyDefinition, Waypoint, ProcessGroup, Bundle
from floweaver.ordering import Ordering


def test_sankey_definition():
    nodes = {}
    bundles = {}
    ordering = Ordering([])
    vd = SankeyDefinition(nodes, bundles, ordering)
    assert vd.nodes is nodes
    assert vd.bundles is bundles
    assert vd.ordering is ordering


def test_sankey_definition_checks_bundles():
    nodes = {
        'a': ProcessGroup(selection=('a1')),
        'b': ProcessGroup(selection=('b1')),
        'waypoint': Waypoint(),
    }
    ordering = Ordering([])

    with pytest.raises(ValueError):
        bundles = {0: Bundle('waypoint', 'b')}
        SankeyDefinition(nodes, bundles, ordering)

    with pytest.raises(ValueError):
        bundles = {0: Bundle('b', 'waypoint')}
        SankeyDefinition(nodes, bundles, ordering)

    # should work
    bundles = {0: Bundle('a', 'b')}
    assert SankeyDefinition(nodes, bundles, ordering)

    # also accepts a list
    bundles = [Bundle('a', 'b')]
    assert SankeyDefinition(nodes, bundles, ordering).bundles \
        == {0: Bundle('a', 'b')}


def test_sankey_definition_checks_nodes_exist():
    nodes = {
        'a': ProcessGroup(selection=('a1')),
        'b': ProcessGroup(selection=('b1')),
        'waypoint': ProcessGroup(),
    }
    ordering = Ordering([])

    with pytest.raises(ValueError):
        bundles = [Bundle('does not exist', 'b')]
        SankeyDefinition(nodes, bundles, ordering)

    with pytest.raises(ValueError):
        bundles = [Bundle('a', 'b', waypoints=['does not exist'])]
        SankeyDefinition(nodes, bundles, ordering)
