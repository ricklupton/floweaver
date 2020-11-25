import pytest

from textwrap import dedent

from floweaver.sankey_definition import SankeyDefinition, Waypoint, ProcessGroup, Bundle
from floweaver.partition import Partition
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


def test_sankey_definition_as_script():
    nodes = {
        'a': ProcessGroup(selection=['a1']),
        'b': ProcessGroup(selection=['b1']),
        'waypoint': Waypoint(),
    }
    ordering = [['a'], ['waypoint'], ['b']]
    bundles = [Bundle('a', 'b')]
    sdd = SankeyDefinition(nodes, bundles, ordering)
    code = sdd.to_code()

    assert code == dedent("""
    from floweaver import (
        ProcessGroup,
        Waypoint,
        Partition,
        Group,
        Elsewhere,
        Bundle,
        SankeyDefinition,
    )

    nodes = {
        'a': ProcessGroup(selection=['a1']),
        'b': ProcessGroup(selection=['b1']),
        'waypoint': Waypoint(),
    }

    ordering = [
        [['a']],
        [['waypoint']],
        [['b']],
    ]

    bundles = [
        Bundle(source='a', target='b'),
    ]

    sdd = SankeyDefinition(nodes, bundles, ordering)
    """)

    # Check roundtrip
    ctx = {}
    exec(code, ctx)
    assert ctx["sdd"] == sdd


def test_sankey_definition_as_script_with_partitions():
    nodes = {
        'a': ProcessGroup(selection=['a1', 'a2']),
        'b': ProcessGroup(selection=['b1']),
        'c': ProcessGroup(selection=['c1', 'c2'],
                          partition=Partition.Simple('process', ['c1', 'c2'])),
        'via': Waypoint(partition=Partition.Simple('material', ['m', 'n'])),
    }
    bundles = [
        Bundle('a', 'c', waypoints=['via']),
        Bundle('b', 'c', waypoints=['via']),
    ]
    ordering = [[['a', 'b']], [['via']], [['c']]]
    sdd = SankeyDefinition(nodes, bundles, ordering,
        flow_partition=Partition.Simple('material', ['m', 'n']))
    code = sdd.to_code()

    # Check roundtrip
    ctx = {}
    exec(code, ctx)
    assert ctx["sdd"] == sdd
