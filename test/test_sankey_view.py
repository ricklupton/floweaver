import pytest

import pandas as pd

from sankeyview.sankey_view import SankeyView, interpolate_ranks, Elsewhere
from sankeyview.node import Node
from sankeyview.bundle import Bundle
from sankeyview.grouping import Grouping
from sankeyview.dataset import Dataset


def test_interpolate_ranks_y():
    # forwards to forwards
    V = Node(0, 0, query={'query': '1'})
    W = Node(2, 2, query={'query': '2'})
    assert interpolate_ranks(V, W) == [(1, 1, False)]

    # forwards to forwards, requiring return loop: loop placed below lower-most
    # of the two nodes.
    V = Node(1, 0, query={'query': '1'})
    W = Node(0, 2, query={'query': '2'})
    assert interpolate_ranks(V, W) == [(1, 3, True), (0, 3, True)]
    V = Node(1, 2, query={'query': '1'})
    W = Node(0, 0, query={'query': '2'})
    assert interpolate_ranks(V, W) == [(1, 3, True), (0, 3, True)]

    # forwards to backwards: return loop is aligned with backwards node
    V = Node(2, 0, query={'query': '1'})
    W = Node(0, 2, query={'query': '2'}, reversed=True)
    assert interpolate_ranks(V, W) == [(2, 2, True), (1, 2, True)]

    # forwards to backwards: return loop is aligned with forwards node if to
    # the left
    V = Node(0, 0, query={'query': '1'})
    W = Node(2, 2, query={'query': '2'}, reversed=True)
    assert interpolate_ranks(V, W) == [(1, 0, False), (2, 0, False)]

    # forwards to backwards: if nodes at at same level, move start of loop down
    V = Node(2, 2, query={'query': '1'})
    W = Node(0, 2, query={'query': '2'}, reversed=True)
    assert interpolate_ranks(V, W) == [(2, 3, True), (1, 2.5, True)]
    V = Node(0, 2, query={'query': '1'})
    W = Node(2, 2, query={'query': '2'}, reversed=True)
    assert interpolate_ranks(V, W) == [(1, 1.5, False), (2, 1, False)]

    # backwards to forwards: return loop is aligned with backwards node
    V = Node(2, 2, query={'query': '1'}, reversed=True)
    W = Node(0, 1, query={'query': '2'})
    assert interpolate_ranks(V, W) == [(1, 2, True), (0, 2, True)]

    # backwards to forwards: if nodes at at same level, move end of loop down
    V = Node(2, 2, query={'query': '1'}, reversed=True)
    W = Node(0, 2, query={'query': '2'})
    assert interpolate_ranks(V, W) == [(1, 2.5, True), (0, 3, True)]
    V = Node(0, 2, query={'query': '1'}, reversed=True)
    W = Node(2, 2, query={'query': '2'})
    assert interpolate_ranks(V, W) == [(0, 1, False), (1, 1.5, False)]

    # backwards to forwards: return loop is aligned with forwards node if to
    # the right
    V = Node(0, 2, query={'query': '1'}, reversed=True)
    W = Node(2, 0, query={'query': '2'})
    assert interpolate_ranks(V, W) == [(0, 0, False), (1, 0, False)]

    # backwards to backwards: linearly interpolates
    V = Node(2, 2, query={'query': '1'}, reversed=True)
    W = Node(0, 0, query={'query': '2'}, reversed=True)
    assert interpolate_ranks(V, W) == [(1, 1, True)]

    # backwards to backwards, requiring return loop: loop placed above
    # upper-most of the two nodes.
    V = Node(0, 1, query={'query': '1'}, reversed=True)
    W = Node(1, 2, query={'query': '2'}, reversed=True)
    assert interpolate_ranks(V, W) == [(0, 0, False), (1, 0, False)]
    V = Node(0, 2, query={'query': '1'}, reversed=True)
    W = Node(1, 1, query={'query': '2'}, reversed=True)
    assert interpolate_ranks(V, W) == [(0, 0, False), (1, 0, False)]


def test_sankey_view_adds_waypoints_forwards():
    nodes = {
        'n1': Node(0, 0, query={'query': '1'}),
        'n2': Node(2, 0, query={'query': '2'}),
    }
    v = SankeyView(nodes, [Bundle('n1', 'n2')])

    assert set(nodes_ignoring_elsewhere(v)) == {'n1', 'n2', 'n1_n2_1'}
    assert set(edges_ignoring_elsewhere(v)) == {
        ('n1', 'n1_n2_1'),
        ('n1_n2_1', 'n2'),
    }

    waypoint = Node(1, 0)
    assert v.high_level.node['n1_n2_1']['node'] == waypoint


def test_sankey_view_adds_waypoints_forwards_default_grouping():
    nodes = {
        'n1': Node(0, 0, query={'query': '1'}),
        'n2': Node(2, 0, query={'query': '2'}),
    }
    g = Grouping.Simple('test', ['x'])
    v = SankeyView(nodes, [Bundle('n1', 'n2', default_grouping=g)])

    assert set(nodes_ignoring_elsewhere(v)) == {'n1', 'n2', 'n1_n2_1'}
    assert set(edges_ignoring_elsewhere(v)) == {
        ('n1', 'n1_n2_1'),
        ('n1_n2_1', 'n2'),
    }

    waypoint = Node(1, 0, grouping=g)
    assert v.high_level.node['n1_n2_1']['node'] == waypoint


def test_sankey_view_adds_waypoints_forwards_to_backwards():
    nodes = {
        'n1': Node(1, 0, query={'query': '1'}),
        'n2': Node(0, 0, query={'query': '2'}, reversed=True),
    }
    v = SankeyView(nodes, [Bundle('n1', 'n2')])

    assert set(nodes_ignoring_elsewhere(v)) == {'n1', 'n2', 'n1_n2_1'}
    assert set(edges_ignoring_elsewhere(v)) == {
        ('n1', 'n1_n2_1'),
        ('n1_n2_1', 'n2'),
    }

    waypoint = Node(1, 1, reversed=True)
    assert v.high_level.node['n1_n2_1']['node'] == waypoint


def test_sankey_view_adds_waypoints_backwards_to_forwards():
    nodes = {
        'n1': Node(1, 1, query={'query': '1'}, reversed=True),
        'n2': Node(0, 0, query={'query': '2'}),
    }
    v = SankeyView(nodes, [Bundle('n1', 'n2')])

    assert set(nodes_ignoring_elsewhere(v)) == {'n1', 'n2', 'n1_n2_0'}
    assert set(edges_ignoring_elsewhere(v)) == {
        ('n1', 'n1_n2_0'),
        ('n1_n2_0', 'n2'),
    }

    waypoint = Node(0, 1, reversed=True)
    assert v.high_level.node['n1_n2_0']['node'] == waypoint


def test_sankey_view_adds_waypoints_backwards_to_backwards():
    # no gap to fill
    nodes = {
        'n1': Node(1, 0, query={'query': '1'}, reversed=True),
        'n2': Node(0, 0, query={'query': '2'}, reversed=True),
    }
    v = SankeyView(nodes, [Bundle('n1', 'n2')])

    assert set(nodes_ignoring_elsewhere(v)) == {'n1', 'n2'}
    assert set(edges_ignoring_elsewhere(v)) == {('n1', 'n2')}

    # with a gap to fill
    nodes = {
        'n1': Node(2, 0, query={'query': '1'}, reversed=True),
        'n2': Node(0, 0, query={'query': '2'}, reversed=True),
    }
    v = SankeyView(nodes, [Bundle('n1', 'n2')])

    assert set(nodes_ignoring_elsewhere(v)) == {'n1', 'n2', 'n1_n2_1'}
    assert set(edges_ignoring_elsewhere(v)) == {
        ('n1', 'n1_n2_1'),
        ('n1_n2_1', 'n2'),
    }

    waypoint = Node(1, 0, reversed=True)
    assert v.high_level.node['n1_n2_1']['node'] == waypoint


def test_sankey_view_merges_bundles_between_same_nodes():
    nodes = {
        'n1': Node(0, 0, query={'query': '1'}),
        'n2': Node(0, 0, query={'query': '2'}),
        'n3': Node(2, 0, query={'query': '3'}),
        'via': Node(1, 0),
    }
    bundles = [
        Bundle('n1', 'n3', waypoints=['via']),
        Bundle('n2', 'n3', waypoints=['via']),
    ]
    v = SankeyView(nodes, bundles)

    assert sorted(edges_ignoring_elsewhere(v, data=True)) == [
        ('n1', 'via', { 'bundles': [bundles[0]] }),
        ('n2', 'via', { 'bundles': [bundles[1]] }),
        ('via', 'n3', { 'bundles': bundles }),
    ]


def test_sankey_view_unused_flows():
    """Unused flows are between *used* nodes
    """
    nodes = {
        'a': Node(0, 0, query=['a']),
        'b': Node(1, 0, query=['b']),
        'c': Node(2, 0, query=['c']),
    }
    bundles = [
        Bundle('a', 'b'),
        Bundle('b', 'c'),
    ]
    v = SankeyView(nodes, bundles)

    # Dataset
    flows = pd.DataFrame.from_records([
        ('a', 'b', 'm', 3),
        ('b', 'c', 'm', 3),
        ('a', 'c', 'm', 1),  # UNUSED
    ], columns=('source', 'target', 'material', 'value'))
    processes = pd.DataFrame({
        'id': list(flows.source.unique()) + list(flows.target.unique())}).set_index('id')
    dataset = Dataset(processes, flows)

    v.build(dataset)

    assert len(v.unused_flows) == 1
    assert v.unused_flows.iloc[0].equals(flows.iloc[2])


def test_sankey_view_low_level_graph():
    nodes = {
        'a': Node(0, 0, query=['a1', 'a2']),
        'b': Node(0, 0, query=['b1']),
        'c': Node(2, 0, query=['c1', 'c2'], grouping=Grouping.Simple('node', ['c1', 'c2'])),
        'via': Node(1, 0, grouping=Grouping.Simple('material', ['m', 'n'])),
    }
    bundles = [
        Bundle('a', 'c', waypoints=['via']),
        Bundle('b', 'c', waypoints=['via']),
    ]
    v = SankeyView(nodes, bundles)

    # Dataset
    flows = pd.DataFrame.from_records([
        ('a1', 'c1', 'm', 3),
        ('a2', 'c1', 'n', 1),
        ('b1', 'c1', 'm', 1),
        ('b1', 'c2', 'm', 2),
        ('b1', 'c2', 'n', 1),
    ], columns=('source', 'target', 'material', 'value'))
    processes = pd.DataFrame({
        'id': list(flows.source.unique()) + list(flows.target.unique())}).set_index('id')
    dataset = Dataset(processes, flows)

    G, order = v.build(dataset)

    assert set(G.nodes()) == {'a^*', 'b^*', 'via^m', 'via^n', 'c^c1', 'c^c2'}
    assert sorted(G.edges(keys=True, data=True)) == [
        ('a^*', 'via^m', '*', { 'value': 3 }),
        ('a^*', 'via^n', '*', { 'value': 1 }),
        ('b^*', 'via^m', '*', { 'value': 3 }),
        ('b^*', 'via^n', '*', { 'value': 1 }),
        ('via^m', 'c^c1', '*', { 'value': 4 }),
        ('via^m', 'c^c2', '*', { 'value': 2 }),
        ('via^n', 'c^c1', '*', { 'value': 1 }),
        ('via^n', 'c^c2', '*', { 'value': 1 }),
    ]

    assert order == [
        [ ['a^*', 'b^*'] ],
        [ ['via^m', 'via^n'] ],
        [ ['c^c1', 'c^c2'] ],
    ]

    # Can also set flow_grouping for all bundles at once
    G, order = v.build(dataset, flow_grouping=Grouping.Simple('material', ['m', 'n']))
    assert sorted(G.edges(keys=True, data=True)) == [
        ('a^*', 'via^m', 'm', { 'value': 3 }),
        ('a^*', 'via^n', 'n', { 'value': 1 }),
        ('b^*', 'via^m', 'm', { 'value': 3 }),
        ('b^*', 'via^n', 'n', { 'value': 1 }),
        ('via^m', 'c^c1', 'm', { 'value': 4 }),
        ('via^m', 'c^c2', 'm', { 'value': 2 }),
        ('via^n', 'c^c1', 'n', { 'value': 1 }),
        ('via^n', 'c^c2', 'n', { 'value': 1 }),
    ]


def test_sankey_view_adds_bundles_to_from_elsewhere():
    nodes = {
        # this is a real node -- should add 'to elsewhere' bundle
        # should not add 'from elsewhere' bundle as it would be the only one
        'a': Node(0, 0, query=('a1')),
        'b': Node(1, 0, query=('b1')),

        # this is a waypoint -- should not have from/to via nodes
        'via': Node(0, 0),
    }
    bundles = [Bundle('a', 'b')]
    v = SankeyView(nodes, bundles)

    from_a = Node(1, 0)
    to_b = Node(0, 0)
    assert set(v.nodes) == {nodes['a'], nodes['b'], nodes['via'], from_a, to_b}
    assert v.bundles == [
        Bundle('a', 'b'),
        Bundle('a', Elsewhere, waypoints=['from a']),
        Bundle(Elsewhere, 'b', waypoints=['to b']),
    ]


def test_sankey_view_allows_only_one_bundle_to_or_from_elsewhere():
    nodes = {
        'a': Node(0, 0, query=('a1', 'a2')),
    }
    bundles = [
        Bundle(Elsewhere, 'a'),
        Bundle(Elsewhere, 'a'),
    ]
    with pytest.raises(ValueError):
        SankeyView(nodes, bundles)

    bundles = [
        Bundle('a', Elsewhere),
        Bundle('a', Elsewhere),
    ]
    with pytest.raises(ValueError):
        SankeyView(nodes, bundles)

    bundles = [
        Bundle('a', Elsewhere),
    ]
    SankeyView(nodes, bundles)


def edges_ignoring_elsewhere(v, data=False):
    if data:
        return [(a, b, data) for a, b, data in v.high_level.edges(data=True)
                if not (a.startswith('from') or b.startswith('from') or
                        a.startswith('to') or b.startswith('to'))]
    else:
        return [(a, b) for a, b in v.high_level.edges(data=False)
                if not (a.startswith('from') or b.startswith('from') or
                        a.startswith('to') or b.startswith('to'))]


def nodes_ignoring_elsewhere(v):
    return [u for u in v.high_level.nodes(data=False)
            if not (u.startswith('from') or u.startswith('to'))]
