import pytest

from sankeyview.view_graph import view_graph
from sankeyview.node_group import NodeGroup
from sankeyview.bundle import Bundle
from sankeyview.partition import Partition
from sankeyview.view_definition import ViewDefinition, Ordering


def test_view_graph_does_not_mutate_definition():
    node_groups = {
        'n1': NodeGroup(selection=['n1']),
        'n2': NodeGroup(selection=['n2']),
    }
    bundles = [
        Bundle('n1', 'n2'),
    ]
    order0 = [['n1'], [], ['n2']]
    vd = ViewDefinition(node_groups, bundles, order0)
    G = view_graph(vd)
    assert vd.node_groups == {
        'n1': NodeGroup(selection=['n1']),
        'n2': NodeGroup(selection=['n2']),
    }
    assert vd.bundles == {
        0: Bundle('n1', 'n2'),
    }
    assert vd.ordering == Ordering([[['n1']], [[]], [['n2']]])



def test_view_graph_adds_waypoints():
    node_groups = {
        'n1': NodeGroup(selection=['n1']),
        'w1': NodeGroup(),
        'n2': NodeGroup(selection=['n2']),
    }
    bundles = [
        Bundle('n1', 'n2', waypoints=['w1']),
    ]
    order0 = [['n1'], [], ['w1'], [], [], ['n2']]
    G, implicit_waypoints = view_graph(ViewDefinition(node_groups, bundles, order0))

    assert sorted(nodes_ignoring_elsewhere(G, data=True)) == [
        ('__n1_w1_1', {'node_group': NodeGroup(title='')}),
        ('__w1_n2_3', {'node_group': NodeGroup(title='')}),
        ('__w1_n2_4', {'node_group': NodeGroup(title='')}),
        ('n1', {'node_group': NodeGroup(selection=['n1'])}),
        ('n2', {'node_group': NodeGroup(selection=['n2'])}),
        ('w1', {'node_group': NodeGroup()}),
    ]
    assert sorted(edges_ignoring_elsewhere(G, data=True)) == [
        ('__n1_w1_1', 'w1', {'bundles': [0]}),
        ('__w1_n2_3', '__w1_n2_4', {'bundles': [0]}),
        ('__w1_n2_4', 'n2', {'bundles': [0]}),
        ('n1', '__n1_w1_1', {'bundles': [0]}),
        ('w1', '__w1_n2_3', {'bundles': [0]}),
    ]
    assert G.ordering == Ordering([
        [['n1']], [['__n1_w1_1']], [['w1']],
        [['__w1_n2_3']], [['__w1_n2_4']], [['n2']]
    ])

    assert implicit_waypoints == {
        '__n1_w1_1': {'position': (1, 0, 0), 'bundle': 0, 'index': 0},
        '__w1_n2_3': {'position': (3, 0, 0), 'bundle': 0, 'index': 1},
        '__w1_n2_4': {'position': (4, 0, 0), 'bundle': 0, 'index': 1},
    }


def test_view_graph_adds_waypoints_partition():
    node_groups = {
        'n1': NodeGroup(selection=['n1']),
        'n2': NodeGroup(selection=['n2']),
    }
    g = Partition.Simple('test', ['x'])
    bundles = [
        Bundle('n1', 'n2', default_partition=g),
    ]
    order0 = [['n1'], [], ['n2']]
    G, _ = view_graph(ViewDefinition(node_groups, bundles, order0))

    assert sorted(nodes_ignoring_elsewhere(G, data=True)) == [
        ('__n1_n2_1', {'node_group': NodeGroup(title='', partition=g)}),
        ('n1', {'node_group': NodeGroup(selection=['n1'])}),
        ('n2', {'node_group': NodeGroup(selection=['n2'])}),
    ]


def test_view_graph_merges_bundles_between_same_nodes():
    node_groups = {
        'n1': NodeGroup(selection=['n1']),
        'n2': NodeGroup(selection=['n2']),
        'n3': NodeGroup(selection=['n3']),
        'via': NodeGroup(),
    }
    order0 = [['n1', 'n2'], ['via'], ['n3']]
    bundles = [
        Bundle('n1', 'n3', waypoints=['via']),
        Bundle('n2', 'n3', waypoints=['via']),
    ]
    G, _ = view_graph(ViewDefinition(node_groups, bundles, order0))

    assert G.node['n3'] == {'node_group': node_groups['n3']}
    assert sorted(edges_ignoring_elsewhere(G, data=True)) == [
        ('n1', 'via', { 'bundles': [0] }),
        ('n2', 'via', { 'bundles': [1] }),
        ('via', 'n3', { 'bundles': [0, 1] }),
    ]


def test_view_graph_bundle_flow_partitions_must_be_equal():
    material_partition_mn = Partition.Simple('material', ['m', 'n'])
    material_partition_XY = Partition.Simple('material', ['X', 'Y'])
    node_groups = {
        'a': NodeGroup(selection=['a1']),
        'b': NodeGroup(selection=['b1']),
        'c': NodeGroup(selection=['c1']),
        'via': NodeGroup(),
    }
    order = [ ['a', 'b'], ['via'], ['c'] ]
    bundles = [
        Bundle('a', 'c', waypoints=['via'], flow_partition=material_partition_mn),
        Bundle('b', 'c', waypoints=['via'], flow_partition=material_partition_XY),
    ]

    # Do partition based on flows stored in bundles
    with pytest.raises(ValueError):
        G, _ = view_graph(ViewDefinition(node_groups, bundles, order))

    bundles[1] = Bundle('b', 'c', waypoints=['via'], flow_partition=material_partition_mn)
    assert view_graph(ViewDefinition(node_groups, bundles, order))


def test_view_graph_does_short_bundles_last():
    """Return loops are inserted immediately below the source node, so work from
    the outside in."""
    #
    #  ,a -- b -- c-,
    #  |      `----`|
    #   `-----------'
    #
    node_groups = {
        'a': NodeGroup(selection=('a',)),
        'b': NodeGroup(selection=('b',)),
        'c': NodeGroup(selection=('c',)),
    }
    order = [[['a']], [['b']], [['c']]]
    bundles = [
        Bundle('a', 'b'),
        Bundle('b', 'c'),
        Bundle('c', 'b'),
        Bundle('c', 'a'),
    ]
    G, _ = view_graph(ViewDefinition(node_groups, bundles, order))

    assert G.ordering == Ordering([
        [['a', '__c_a_0']],
        [['b', '__c_b_1', '__c_a_1']],
        [['c', '__c_b_2', '__c_a_2']],
    ])

    # order of bundles doesn't affect it
    G2, _ = view_graph(ViewDefinition(node_groups, bundles[::-1], order))
    assert G.ordering == G2.ordering


def test_view_graph_does_non_dummy_bundles_first():
    """It's important to do bundles that don't require adding dummy nodes first, so
    when it comes to return loops, they are better placed."""
    node_groups = {
        'a': NodeGroup(selection=('a',)),
        'b': NodeGroup(selection=('b',)),
        'c': NodeGroup(selection=('c',)),
        'd': NodeGroup(selection=('d',)),
    }
    order = [ [['a', 'c']], [['b', 'd']] ]
    bundles = [
        Bundle('a', 'b'),
        Bundle('c', 'd'),
        Bundle('b', 'a'),
    ]
    G, _ = view_graph(ViewDefinition(node_groups, bundles, order))

    assert G.ordering == Ordering([
        [['a', '__b_a_0', 'c']],
        [['b', '__b_a_1', 'd']],
    ])

    # order of bundles doesn't affect it
    G2, _ = view_graph(ViewDefinition(node_groups, bundles[::-1], order))
    assert G2.ordering == G.ordering


# def test_sankey_view_adds_bundles_to_from_elsewhere():
#     nodes = {
#         # this is a real node -- should add 'to elsewhere' bundle
#         # should not add 'from elsewhere' bundle as it would be the only one
#         'a': NodeGroup(0, 0, query=('a1')),
#         'b': NodeGroup(1, 0, query=('b1')),

#         # this is a waypoint -- should not have from/to via nodes
#         'via': NodeGroup(0, 0),
#     }
#     bundles = [Bundle('a', 'b')]
#     v = SankeyView(nodes, bundles)

#     from_a = NodeGroup(1, 0)
#     to_b = NodeGroup(0, 0)
#     assert set(v.nodes) == {nodes['a'], nodes['b'], nodes['via'], from_a, to_b}
#     assert sorted(v.bundles) == [
#         Bundle('a', 'b'),
#         Bundle('a', Elsewhere, waypoints=['from a']),
#         Bundle(Elsewhere, 'b', waypoints=['to b']),
#     ]


# def test_sankey_view_allows_only_one_bundle_to_or_from_elsewhere():
#     nodes = {
#         'a': NodeGroup(0, 0, query=('a1', 'a2')),
#     }
#     bundles = [
#         Bundle(Elsewhere, 'a'),
#         Bundle(Elsewhere, 'a'),
#     ]
#     with pytest.raises(ValueError):
#         SankeyView(nodes, bundles)

#     bundles = [
#         Bundle('a', Elsewhere),
#         Bundle('a', Elsewhere),
#     ]
#     with pytest.raises(ValueError):
#         SankeyView(nodes, bundles)

#     bundles = [
#         Bundle('a', Elsewhere),
#     ]
#     SankeyView(nodes, bundles)


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
