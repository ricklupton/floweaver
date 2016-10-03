import pytest

from sankeyview.view_definition import ViewDefinition, Waypoint, ProcessGroup, Bundle, Elsewhere
from sankeyview.ordering import Ordering


def test_view_definition():
    nodes = {}
    bundles = {}
    ordering = Ordering([])
    vd = ViewDefinition(nodes, bundles, ordering)
    assert vd.nodes is nodes
    assert vd.bundles is bundles
    assert vd.ordering is ordering


def test_view_definition_checks_bundles():
    nodes = {
        'a': ProcessGroup(selection=('a1')),
        'b': ProcessGroup(selection=('b1')),
        'waypoint': Waypoint(),
    }
    ordering = Ordering([])

    with pytest.raises(ValueError):
        bundles = {
            0: Bundle('waypoint', 'b')
        }
        ViewDefinition(nodes, bundles, ordering)

    with pytest.raises(ValueError):
        bundles = {
            0: Bundle('b', 'waypoint')
        }
        ViewDefinition(nodes, bundles, ordering)

    # should work
    bundles = {
        0: Bundle('a', 'b')
    }
    assert ViewDefinition(nodes, bundles, ordering)

    # also accepts a list
    bundles = [Bundle('a', 'b')]
    assert ViewDefinition(nodes, bundles, ordering).bundles \
        == {0: Bundle('a', 'b')}


def test_view_definition_checks_process_groups_exist():
    nodes = {
        'a': ProcessGroup(selection=('a1')),
        'b': ProcessGroup(selection=('b1')),
        'waypoint': ProcessGroup(),
    }
    ordering = Ordering([])

    with pytest.raises(ValueError):
        bundles = [
            Bundle('does not exist', 'b')
        ]
        ViewDefinition(nodes, bundles, ordering)

    with pytest.raises(ValueError):
        bundles = [
            Bundle('a', 'b', waypoints=['does not exist'])
        ]
        ViewDefinition(nodes, bundles, ordering)
