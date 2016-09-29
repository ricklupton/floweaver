import pytest

from sankeyview.view_definition import ViewDefinition, Waypoint, ProcessGroup
from sankeyview.ordering import Ordering
from sankeyview.bundle import Bundle, Elsewhere


def test_view_definition():
    process_groups = {}
    waypoints = {}
    bundles = {}
    ordering = Ordering([])
    vd = ViewDefinition(process_groups, waypoints, bundles, ordering)
    assert vd.process_groups is process_groups
    assert vd.waypoints is waypoints
    assert vd.bundles is bundles
    assert vd.ordering is ordering


def test_view_definition_checks_bundles():
    process_groups = {
        'a': ProcessGroup(selection=('a1')),
        'b': ProcessGroup(selection=('b1')),
    }
    waypoints = {
        'waypoint': Waypoint(),
    }
    ordering = Ordering([])

    with pytest.raises(ValueError):
        bundles = {
            0: Bundle('waypoint', 'b')
        }
        ViewDefinition(process_groups, waypoints, bundles, ordering)

    with pytest.raises(ValueError):
        bundles = {
            0: Bundle('b', 'waypoint')
        }
        ViewDefinition(process_groups, waypoints, bundles, ordering)

    # should work
    bundles = {
        0: Bundle('a', 'b')
    }
    assert ViewDefinition(process_groups, waypoints, bundles, ordering)

    # also accepts a list
    bundles = [Bundle('a', 'b')]
    assert ViewDefinition(process_groups, waypoints, bundles, ordering).bundles \
        == {0: Bundle('a', 'b')}


def test_view_definition_checks_process_groups_exist():
    process_groups = {
        'a': ProcessGroup(selection=('a1')),
        'b': ProcessGroup(selection=('b1')),
    }
    waypoints = {
        'waypoint': ProcessGroup(),
    }
    ordering = Ordering([])

    with pytest.raises(ValueError):
        bundles = [
            Bundle('does not exist', 'b')
        ]
        ViewDefinition(process_groups, waypoints, bundles, ordering)

    with pytest.raises(ValueError):
        bundles = [
            Bundle('a', 'b', waypoints=['does not exist'])
        ]
        ViewDefinition(process_groups, waypoints, bundles, ordering)



def test_view_definition_normalises_order():
    process_groups = {'a': ProcessGroup(), 'b': ProcessGroup(), 'c': ProcessGroup()}

    # two levels (no bands) --> normalised 3-level
    vd = ViewDefinition(process_groups, {}, [], [ ['a', 'b'], ['c'] ])
    assert vd.ordering == Ordering([ [['a', 'b']], [['c']] ])

    # three levels --> unaltered
    vd = ViewDefinition(process_groups, {}, [], [ [['a', 'b']], [['c']] ])
    assert vd.ordering == Ordering([ [['a', 'b']], [['c']] ])


# def test_view_definition_merge():
#     vd1 = ViewDefinition({'a': ProcessGroup(selection=True), 'b': ProcessGroup(selection=True)},
#                          {'0': Bundle('a', 'b')},
#                          [['a'], ['b']])

#     vd2 = vd1.merge(nodes={'c': ProcessGroup(selection=True, title='C')},
#                     bundles={'1': Bundle('a', 'c')})

#     assert vd2.nodes == {'a': ProcessGroup(selection=True),
#                          'b': ProcessGroup(selection=True),
#                          'c': ProcessGroup(selection=True, title='C')}

#     assert vd2.bundles == {'0': Bundle('a', 'b'),
#                            '1': Bundle('a', 'c')}

