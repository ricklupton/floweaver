import pytest

from floweaver.view_graph import view_graph
from floweaver.partition import Partition
from floweaver.sankey_definition import SankeyDefinition, Ordering, ProcessGroup, Waypoint, Bundle


def test_view_graph_does_not_mutate_definition():
    nodes = {
        'n1': ProcessGroup(selection=['n1']),
        'n2': ProcessGroup(selection=['n2']),
    }
    bundles = [Bundle('n1', 'n2'), ]
    order0 = [['n1'], [], ['n2']]
    vd = SankeyDefinition(nodes, bundles, order0)
    G = view_graph(vd)
    assert vd.nodes == {
        'n1': ProcessGroup(selection=['n1']),
        'n2': ProcessGroup(selection=['n2']),
    }
    assert vd.bundles == {0: Bundle('n1', 'n2'), }
    assert vd.ordering == Ordering([[['n1']], [[]], [['n2']]])


def test_view_graph_adds_waypoints():
    nodes = {
        'n1': ProcessGroup(selection=['n1']),
        'n2': ProcessGroup(selection=['n2']),
        'w1': Waypoint(),
    }
    bundles = [Bundle('n1', 'n2', waypoints=['w1']), ]
    order0 = [['n1'], [], ['w1'], [], [], ['n2']]
    G = view_graph(SankeyDefinition(nodes, bundles, order0))

    assert sorted(nodes_ignoring_elsewhere(G, data=True)) == [
        ('__n1_w1_1', {'node': Waypoint(title='')}),
        ('__w1_n2_3', {'node': Waypoint(title='')}),
        ('__w1_n2_4', {'node': Waypoint(title='')}),
        ('n1', {'node': ProcessGroup(selection=['n1'])}),
        ('n2', {'node': ProcessGroup(selection=['n2'])}),
        ('w1', {'node': Waypoint()}),
    ]
    assert sorted(edges_ignoring_elsewhere(G, data=True)) == [
        ('__n1_w1_1', 'w1', {'bundles': [0]}),
        ('__w1_n2_3', '__w1_n2_4', {'bundles': [0]}),
        ('__w1_n2_4', 'n2', {'bundles': [0]}),
        ('n1', '__n1_w1_1', {'bundles': [0]}),
        ('w1', '__w1_n2_3', {'bundles': [0]}),
    ]
    assert G.ordering == Ordering([
        [['n1']], [['__n1_w1_1']], [['w1']], [['__w1_n2_3']], [['__w1_n2_4']],
        [['n2']]
    ])


def test_view_graph_adds_waypoints_partition():
    nodes = {
        'n1': ProcessGroup(selection=['n1']),
        'n2': ProcessGroup(selection=['n2']),
    }
    g = Partition.Simple('test', ['x'])
    bundles = [Bundle('n1', 'n2', default_partition=g), ]
    order0 = [['n1'], [], ['n2']]
    G = view_graph(SankeyDefinition(nodes, bundles, order0))

    assert sorted(nodes_ignoring_elsewhere(G, data=True)) == [
        ('__n1_n2_1', {'node': Waypoint(title='', partition=g)}),
        ('n1', {'node': ProcessGroup(selection=['n1'])}),
        ('n2', {'node': ProcessGroup(selection=['n2'])}),
    ]


def test_view_graph_merges_bundles_between_same_nodes():
    nodes = {
        'n1': ProcessGroup(selection=['n1']),
        'n2': ProcessGroup(selection=['n2']),
        'n3': ProcessGroup(selection=['n3']),
        'via': Waypoint(),
    }
    order0 = [['n1', 'n2'], ['via'], ['n3']]
    bundles = [
        Bundle('n1', 'n3', waypoints=['via']),
        Bundle('n2', 'n3', waypoints=['via']),
    ]
    G = view_graph(SankeyDefinition(nodes, bundles, order0))

    assert G.nodes['n3'] == {'node': nodes['n3']}
    assert sorted(edges_ignoring_elsewhere(G, data=True)) == [
        ('n1', 'via', {'bundles': [0]}),
        ('n2', 'via', {'bundles': [1]}),
        ('via', 'n3', {'bundles': [0, 1]}),
    ]


def test_view_graph_bundle_flow_partitions_must_be_equal():
    material_partition_mn = Partition.Simple('material', ['m', 'n'])
    material_partition_XY = Partition.Simple('material', ['X', 'Y'])
    nodes = {
        'a': ProcessGroup(selection=['a1']),
        'b': ProcessGroup(selection=['b1']),
        'c': ProcessGroup(selection=['c1']),
        'via': Waypoint(),
    }
    order = [['a', 'b'], ['via'], ['c']]
    bundles = [
        Bundle('a',
               'c',
               waypoints=['via'],
               flow_partition=material_partition_mn),
        Bundle('b',
               'c',
               waypoints=['via'],
               flow_partition=material_partition_XY),
    ]

    # Do partition based on flows stored in bundles
    with pytest.raises(ValueError):
        G = view_graph(SankeyDefinition(nodes, bundles, order))

    bundles[1] = Bundle('b',
                        'c',
                        waypoints=['via'],
                        flow_partition=material_partition_mn)
    assert view_graph(SankeyDefinition(nodes, bundles, order))


def test_view_graph_does_short_bundles_last():
    """Return loops are inserted immediately below the source node, so work from
    the outside in."""
    #
    #  ,a -- b -- c-,
    #  |      `----`|
    #   `-----------'
    #
    nodes = {
        'a': ProcessGroup(selection=('a', )),
        'b': ProcessGroup(selection=('b', )),
        'c': ProcessGroup(selection=('c', )),
    }
    order = [[['a']], [['b']], [['c']]]
    bundles = [
        Bundle('a', 'b'),
        Bundle('b', 'c'),
        Bundle('c', 'b'),
        Bundle('c', 'a'),
    ]
    G = view_graph(SankeyDefinition(nodes, bundles, order))

    assert G.ordering == Ordering([
        [['a', '__c_a_0']],
        [['b', '__c_b_1', '__c_a_1']],
        [['c', '__c_b_2', '__c_a_2']],
    ])

    # order of bundles doesn't affect it
    G2 = view_graph(SankeyDefinition(nodes, bundles[::-1], order))
    assert G.ordering == G2.ordering


def test_view_graph_does_non_dummy_bundles_first():
    """It's important to do bundles that don't require adding dummy nodes first, so
    when it comes to return loops, they are better placed."""
    nodes = {
        'a': ProcessGroup(selection=('a', )),
        'b': ProcessGroup(selection=('b', )),
        'c': ProcessGroup(selection=('c', )),
        'd': ProcessGroup(selection=('d', )),
    }
    order = [[['a', 'c']], [['b', 'd']]]
    bundles = [
        Bundle('a', 'b'),
        Bundle('c', 'd'),
        Bundle('b', 'a'),
    ]
    G = view_graph(SankeyDefinition(nodes, bundles, order))

    assert G.ordering == Ordering([
        [['a', '__b_a_0', 'c']],
        [['b', '__b_a_1', 'd']],
    ])

    # order of bundles doesn't affect it
    G2 = view_graph(SankeyDefinition(nodes, bundles[::-1], order))
    assert G2.ordering == G.ordering


def edges_ignoring_elsewhere(G, data=False):
    if data:
        return [(a, b, data) for a, b, data in G.edges(data=True)
                if not (a.startswith('from') or b.startswith('from') or
                        a.startswith('to') or b.startswith('to'))]
    else:
        return [(a, b) for a, b in G.edges(data=False)
                if not (a.startswith('from') or b.startswith('from') or
                        a.startswith('to') or b.startswith('to'))]


def nodes_ignoring_elsewhere(G, data=False):
    if data:
        return [(u, data) for u, data in G.nodes(data=True)
                if not (u.startswith('from') or u.startswith('to'))]
    else:
        return [u for u in G.nodes(data=False)
                if not (u.startswith('from') or u.startswith('to'))]
