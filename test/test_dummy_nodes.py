import pytest

import networkx as nx

from sankeyview.dummy_nodes import add_dummy_nodes
from sankeyview.node import Node
from sankeyview.bundle import Bundle


def _twonodes(xrank, xdir, yrank, ydir, **kwargs):
    G = nx.DiGraph()
    G.add_node('x', node=Node(direction=xdir))
    G.add_node('y', node=Node(direction=ydir))
    order = [[[]] for i in range(max(xrank, yrank) + 1)]
    order[xrank][0].append('x')
    order[yrank][0].append('y')
    kwargs.setdefault('bundle', None)
    return add_dummy_nodes(G, order, 'x', 'y', **kwargs)


def test_dummy_nodes_simple():
    bundle = Bundle('x', 'y')
    G, order = _twonodes(0, 'R', 1, 'R', bundle=bundle)
    assert set(G.nodes()) == {'x', 'y'}
    assert set(G.edges()) == {('x', 'y')}
    assert order == [[['x']], [['y']]]
    assert G['x']['y']['bundles'] == [bundle]


def test_dummy_nodes_merge_bundles():
    G = nx.DiGraph()
    for u in 'ab': G.add_node(u, node=Node())
    order = [[['a']], [['b']]]
    bundles = [
        Bundle('x', 'b'),
        Bundle('y', 'b'),
    ]
    G, order = add_dummy_nodes(G, order, 'a', 'b', bundle=bundles[0])
    assert G['a']['b']['bundles'] == bundles[0:1]
    G, order = add_dummy_nodes(G, order, 'a', 'b', bundle=bundles[1])
    assert G['a']['b']['bundles'] == bundles[0:2]
    assert set(G.nodes()) == {'a', 'b'}
    assert set(G.edges()) == {('a', 'b')}
    assert order == [[['a']], [['b']]]


def test_dummy_nodes_sets_node_attributes():
    G, order = _twonodes(0, 'R', 2, 'R')
    assert G.node['__x_y_1']['node'].grouping == Node().grouping  # default

    G, order = _twonodes(0, 'R', 2, 'R', node_kwargs=dict(grouping='test'))
    assert G.node['__x_y_1']['node'].grouping == 'test'


def test_dummy_nodes_tracking_attributes():
    G, order = _twonodes(0, 'R', 2, 'R', attrs=dict(test='hello'))
    assert G.node['__x_y_1']['test'] == 'hello'


def test_dummy_nodes_right_RL():
    G, order = _twonodes(0, 'R', 2, 'L')
    assert set(G.nodes()) == {'x', 'y', '__x_y_1', '__x_y_2'}
    assert set(G.edges()) == {('x', '__x_y_1'), ('__x_y_1', '__x_y_2'),
                              ('__x_y_2', 'y')}
    assert order == [[['x']], [['__x_y_1']], [['__x_y_2', 'y']]]


def test_dummy_nodes_right_LR():
    G, order = _twonodes(0, 'L', 2, 'R')
    assert set(G.nodes()) == {'x', 'y', '__x_y_0', '__x_y_1'}
    assert set(G.edges()) == {('x', '__x_y_0'), ('__x_y_0', '__x_y_1'),
                              ('__x_y_1', 'y')}
    assert order == [[['__x_y_0', 'x']], [['__x_y_1']], [['y']]]


def test_dummy_nodes_right_RR():
    G, order = _twonodes(0, 'R', 2, 'R')
    assert set(G.nodes()) == {'x', 'y', '__x_y_1'}
    assert set(G.edges()) == {('x', '__x_y_1'), ('__x_y_1', 'y')}
    assert order == [[['x']], [['__x_y_1']], [['y']]]


def test_dummy_nodes_right_LL():
    G, order = _twonodes(0, 'L', 2, 'L')
    assert set(G.nodes()) == {'x', 'y', '__x_y_0', '__x_y_1', '__x_y_2'}
    assert set(G.edges()) == {('x', '__x_y_0'), ('__x_y_0', '__x_y_1'),
                              ('__x_y_1', '__x_y_2'), ('__x_y_2', 'y')}
    assert order == [[['__x_y_0', 'x']], [['__x_y_1']], [['__x_y_2', 'y']]]


def test_dummy_nodes_left_RL():
    G, order = _twonodes(2, 'R', 0, 'L')
    assert set(G.nodes()) == {'x', 'y', '__x_y_1', '__x_y_2'}
    assert set(G.edges()) == {('x', '__x_y_2'), ('__x_y_2', '__x_y_1'),
                              ('__x_y_1', 'y')}
    assert order == [[['y']], [['__x_y_1']], [['x', '__x_y_2']]]


def test_dummy_nodes_left_LR():
    G, order = _twonodes(2, 'L', 0, 'R')
    assert set(G.nodes()) == {'x', 'y', '__x_y_0', '__x_y_1'}
    assert set(G.edges()) == {('x', '__x_y_1'), ('__x_y_1', '__x_y_0'),
                              ('__x_y_0', 'y')}
    assert order == [[['y', '__x_y_0']], [['__x_y_1']], [['x']]]

    G, order = _twonodes(1, 'L', 0, 'R')
    assert set(G.nodes()) == {'x', 'y', '__x_y_0'}
    assert set(G.edges()) == {('x', '__x_y_0'), ('__x_y_0', 'y')}
    assert order == [[['y', '__x_y_0']], [['x']]]


def test_dummy_nodes_left_LL():
    G, order = _twonodes(2, 'L', 0, 'L')
    assert set(G.nodes()) == {'x', 'y', '__x_y_1'}
    assert set(G.edges()) == {('x', '__x_y_1'), ('__x_y_1', 'y')}
    assert order == [[['y']], [['__x_y_1']], [['x']]]


def test_dummy_nodes_left_RR():
    G, order = _twonodes(2, 'R', 0, 'R')
    assert set(G.nodes()) == {'x', 'y', '__x_y_0', '__x_y_1', '__x_y_2'}
    assert set(G.edges()) == {('x', '__x_y_2'), ('__x_y_2', '__x_y_1'),
                              ('__x_y_1', '__x_y_0'), ('__x_y_0', 'y')}
    assert order == [[['y', '__x_y_0']], [['__x_y_1']], [['x', '__x_y_2']]]


def test_dummy_nodes_def_position():
    G, order = _twonodes(2, 'R', 0, 'L')
    assert order == [[['y']], [['__x_y_1']], [['x', '__x_y_2']]]
    assert G.node['__x_y_2']['def_pos'] == (2, 0, 1)
    assert G.node['__x_y_1']['def_pos'] == (1, 0, 0)


def test_dummy_nodes_order_dependence():
    #
    #  a   b
    #  c   d
    #
    # bundles a-b, c-d, b-a

    G = nx.DiGraph()
    G.add_nodes_from('abcd', node=Node())
    order = [ [['a', 'c']], [['b', 'd']] ]

    # Correct order: a-b, c-d, b-a
    G1, order1 = _apply_bundles(G, order, ('ab', 'cd', 'ba'))
    assert order1 == [ [['a', '__b_a_0', 'c']], [['b', '__b_a_1', 'd']] ]

    # Incorrect order: b-a first
    G2, order2 = _apply_bundles(G, order, ('ba', 'ab', 'cd'))
    assert order2 == [ [['a', 'c', '__b_a_0']], [['b', '__b_a_1', 'd']] ]



def _apply_bundles(G, order, pairs):
    for x, y in pairs:
        G, order = add_dummy_nodes(G, order, x, y, bundle=None)
    return G, order
