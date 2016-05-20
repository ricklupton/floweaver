import pytest

from sankeyview.view_graph import view_graph
from sankeyview.node import Node
from sankeyview.bundle import Bundle
from sankeyview.grouping import Grouping
from sankeyview.view_definition import ViewDefinition


def test_view_graph_does_not_mutate_definition():
    nodes = {
        'n1': Node(selection=['n1']),
        'n2': Node(selection=['n2']),
    }
    bundles = [
        Bundle('n1', 'n2'),
    ]
    order0 = [['n1'], [], ['n2']]
    vd = ViewDefinition(nodes, bundles, order0)
    G, order = view_graph(vd)
    assert vd.nodes == {
        'n1': Node(selection=['n1']),
        'n2': Node(selection=['n2']),
    }
    assert vd.bundles == [
        Bundle('n1', 'n2'),
    ]
    assert vd.order == [[['n1']], [[]], [['n2']]]



def test_view_graph_adds_waypoints():
    nodes = {
        'n1': Node(selection=['n1']),
        'n2': Node(selection=['n2']),
    }
    bundles = [
        Bundle('n1', 'n2'),
    ]
    order0 = [['n1'], [], ['n2']]
    G, order = view_graph(ViewDefinition(nodes, bundles, order0))

    assert sorted(nodes_ignoring_elsewhere(G, data=True)) == [
        ('__n1_n2_1', {'node': Node(title='')}),
        ('n1', {'node': Node(selection=['n1'])}),
        ('n2', {'node': Node(selection=['n2'])}),
    ]
    assert sorted(edges_ignoring_elsewhere(G, data=True)) == [
        ('__n1_n2_1', 'n2', {'bundles': bundles}),
        ('n1', '__n1_n2_1', {'bundles': bundles}),
    ]
    assert order == [[['n1']], [['__n1_n2_1']], [['n2']]]


def test_view_graph_adds_waypoints_grouping():
    nodes = {
        'n1': Node(selection=['n1']),
        'n2': Node(selection=['n2']),
    }
    g = Grouping.Simple('test', ['x'])
    bundles = [
        Bundle('n1', 'n2', default_grouping=g),
    ]
    order0 = [['n1'], [], ['n2']]
    G, order = view_graph(ViewDefinition(nodes, bundles, order0))

    assert sorted(nodes_ignoring_elsewhere(G, data=True)) == [
        ('__n1_n2_1', {'node': Node(title='', grouping=g)}),
        ('n1', {'node': Node(selection=['n1'])}),
        ('n2', {'node': Node(selection=['n2'])}),
    ]


def test_view_graph_merges_bundles_between_same_nodes():
    nodes = {
        'n1': Node(selection=['n1']),
        'n2': Node(selection=['n2']),
        'n3': Node(selection=['n3']),
        'via': Node(),
    }
    order0 = [['n1', 'n2'], ['via'], ['n3']]
    bundles = [
        Bundle('n1', 'n3', waypoints=['via']),
        Bundle('n2', 'n3', waypoints=['via']),
    ]
    G, order = view_graph(ViewDefinition(nodes, bundles, order0))

    assert sorted(edges_ignoring_elsewhere(G, data=True)) == [
        ('n1', 'via', { 'bundles': [bundles[0]] }),
        ('n2', 'via', { 'bundles': [bundles[1]] }),
        ('via', 'n3', { 'bundles': bundles }),
    ]


def test_view_graph_does_short_bundles_last():
    """Return loops are inserted immediately below the source node, so work from
    the outside in."""
    #
    #  ,a -- b -- c-,
    #  |      `----`|
    #   `-----------'
    #
    nodes = {
        'a': Node(selection=('a',)),
        'b': Node(selection=('b',)),
        'c': Node(selection=('c',)),
    }
    order = [[['a']], [['b']], [['c']]]
    bundles = [
        Bundle('a', 'b'),
        Bundle('b', 'c'),
        Bundle('c', 'b'),
        Bundle('c', 'a'),
    ]
    # import pdb
    # pdb.set_trace()
    GV, oV = view_graph(ViewDefinition(nodes, bundles, order))

    assert oV == [
        [['a', '__c_a_0']],
        [['b', '__c_b_1', '__c_a_1']],
        [['c', '__c_b_2', '__c_a_2']],
    ]

    # order of bundles doesn't affect it
    GV2, oV2 = view_graph(ViewDefinition(nodes, bundles[::-1], order))
    assert oV == oV2


def test_view_graph_does_non_dummy_bundles_first():
    """It's important to do bundles that don't require adding dummy nodes first, so
    when it comes to return loops, they are better placed."""
    nodes = {
        'a': Node(selection=('a',)),
        'b': Node(selection=('b',)),
        'c': Node(selection=('c',)),
        'd': Node(selection=('d',)),
    }
    order = [ [['a', 'c']], [['b', 'd']] ]
    bundles = [
        Bundle('a', 'b'),
        Bundle('c', 'd'),
        Bundle('b', 'a'),
    ]
    GV, oV = view_graph(ViewDefinition(nodes, bundles, order))

    assert oV == [
        [['a', '__b_a_0', 'c']],
        [['b', '__b_a_1', 'd']],
    ]

    # order of bundles doesn't affect it
    GV2, oV2 = view_graph(ViewDefinition(nodes, bundles[::-1], order))
    assert oV == oV2


# def test_sankey_view_adds_bundles_to_from_elsewhere():
#     nodes = {
#         # this is a real node -- should add 'to elsewhere' bundle
#         # should not add 'from elsewhere' bundle as it would be the only one
#         'a': Node(0, 0, query=('a1')),
#         'b': Node(1, 0, query=('b1')),

#         # this is a waypoint -- should not have from/to via nodes
#         'via': Node(0, 0),
#     }
#     bundles = [Bundle('a', 'b')]
#     v = SankeyView(nodes, bundles)

#     from_a = Node(1, 0)
#     to_b = Node(0, 0)
#     assert set(v.nodes) == {nodes['a'], nodes['b'], nodes['via'], from_a, to_b}
#     assert sorted(v.bundles) == [
#         Bundle('a', 'b'),
#         Bundle('a', Elsewhere, waypoints=['from a']),
#         Bundle(Elsewhere, 'b', waypoints=['to b']),
#     ]


# def test_sankey_view_allows_only_one_bundle_to_or_from_elsewhere():
#     nodes = {
#         'a': Node(0, 0, query=('a1', 'a2')),
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
