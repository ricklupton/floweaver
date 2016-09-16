import pytest

import networkx as nx

from sankeyview.layered_graph import LayeredGraph
from sankeyview.dummy_nodes import add_dummy_nodes
from sankeyview.node_group import NodeGroup
from sankeyview.bundle import Bundle


def _twonodes(xrank, xdir, yrank, ydir, implicit=None, **kwargs):
    G = LayeredGraph()
    G.add_node('x', node_group=NodeGroup(direction=xdir))
    G.add_node('y', node_group=NodeGroup(direction=ydir))
    G.order = [[[]] for i in range(max(xrank, yrank) + 1)]
    G.order[xrank][0].append('x')
    G.order[yrank][0].append('y')
    kwargs.setdefault('bundle_key', None)
    return add_dummy_nodes(G, 'x', 'y', implicit_waypoints=implicit, **kwargs)


def test_dummy_nodes_simple():
    G = _twonodes(0, 'R', 1, 'R', bundle_key=27)
    assert set(G.nodes()) == {'x', 'y'}
    assert set(G.edges()) == {('x', 'y')}
    assert G.order == [[['x']], [['y']]]
    assert G['x']['y']['bundles'] == [27]


def test_dummy_nodes_merge_bundles():
    G = LayeredGraph()
    for u in 'ab': G.add_node(u, node_group=NodeGroup())
    G.order = [[['a']], [['b']]]

    G = add_dummy_nodes(G, 'a', 'b', bundle_key=1)
    assert G['a']['b']['bundles'] == [1]

    G = add_dummy_nodes(G, 'a', 'b', bundle_key=2)
    assert G['a']['b']['bundles'] == [1, 2]

    assert set(G.nodes()) == {'a', 'b'}
    assert set(G.edges()) == {('a', 'b')}
    assert G.order == [[['a']], [['b']]]


def test_dummy_nodes_sets_node_attributes():
    G = _twonodes(0, 'R', 2, 'R')
    assert G.node['__x_y_1']['node_group'].partition == NodeGroup().partition  # default

    G = _twonodes(0, 'R', 2, 'R', node_kwargs=dict(partition='test'))
    assert G.node['__x_y_1']['node_group'].partition == 'test'


def test_dummy_nodes_right_RL():
    G = _twonodes(0, 'R', 2, 'L')
    assert set(G.nodes()) == {'x', 'y', '__x_y_1', '__x_y_2'}
    assert set(G.edges()) == {('x', '__x_y_1'), ('__x_y_1', '__x_y_2'),
                              ('__x_y_2', 'y')}
    assert G.order == [[['x']], [['__x_y_1']], [['__x_y_2', 'y']]]


def test_dummy_nodes_right_LR():
    G = _twonodes(0, 'L', 2, 'R')
    assert set(G.nodes()) == {'x', 'y', '__x_y_0', '__x_y_1'}
    assert set(G.edges()) == {('x', '__x_y_0'), ('__x_y_0', '__x_y_1'),
                              ('__x_y_1', 'y')}
    assert G.order == [[['__x_y_0', 'x']], [['__x_y_1']], [['y']]]


def test_dummy_nodes_right_RR():
    G = _twonodes(0, 'R', 2, 'R')
    assert set(G.nodes()) == {'x', 'y', '__x_y_1'}
    assert set(G.edges()) == {('x', '__x_y_1'), ('__x_y_1', 'y')}
    assert G.order == [[['x']], [['__x_y_1']], [['y']]]


def test_dummy_nodes_right_LL():
    G = _twonodes(0, 'L', 2, 'L')
    assert set(G.nodes()) == {'x', 'y', '__x_y_0', '__x_y_1', '__x_y_2'}
    assert set(G.edges()) == {('x', '__x_y_0'), ('__x_y_0', '__x_y_1'),
                              ('__x_y_1', '__x_y_2'), ('__x_y_2', 'y')}
    assert G.order == [[['__x_y_0', 'x']], [['__x_y_1']], [['__x_y_2', 'y']]]


def test_dummy_nodes_left_RL():
    G = _twonodes(2, 'R', 0, 'L')
    assert set(G.nodes()) == {'x', 'y', '__x_y_1', '__x_y_2'}
    assert set(G.edges()) == {('x', '__x_y_2'), ('__x_y_2', '__x_y_1'),
                              ('__x_y_1', 'y')}
    assert G.order == [[['y']], [['__x_y_1']], [['x', '__x_y_2']]]


def test_dummy_nodes_left_LR():
    G = _twonodes(2, 'L', 0, 'R')
    assert set(G.nodes()) == {'x', 'y', '__x_y_0', '__x_y_1'}
    assert set(G.edges()) == {('x', '__x_y_1'), ('__x_y_1', '__x_y_0'),
                              ('__x_y_0', 'y')}
    assert G.order == [[['y', '__x_y_0']], [['__x_y_1']], [['x']]]

    G = _twonodes(1, 'L', 0, 'R')
    assert set(G.nodes()) == {'x', 'y', '__x_y_0'}
    assert set(G.edges()) == {('x', '__x_y_0'), ('__x_y_0', 'y')}
    assert G.order == [[['y', '__x_y_0']], [['x']]]


def test_dummy_nodes_left_LL():
    G = _twonodes(2, 'L', 0, 'L')
    assert set(G.nodes()) == {'x', 'y', '__x_y_1'}
    assert set(G.edges()) == {('x', '__x_y_1'), ('__x_y_1', 'y')}
    assert G.order == [[['y']], [['__x_y_1']], [['x']]]


def test_dummy_nodes_left_RR():
    G = _twonodes(2, 'R', 0, 'R')
    assert set(G.nodes()) == {'x', 'y', '__x_y_0', '__x_y_1', '__x_y_2'}
    assert set(G.edges()) == {('x', '__x_y_2'), ('__x_y_2', '__x_y_1'),
                              ('__x_y_1', '__x_y_0'), ('__x_y_0', 'y')}
    assert G.order == [[['y', '__x_y_0']], [['__x_y_1']], [['x', '__x_y_2']]]


def test_dummy_nodes_implicit_position():
    implicit = {}
    G = _twonodes(2, 'R', 0, 'L', implicit)
    assert G.order == [[['y']], [['__x_y_1']], [['x', '__x_y_2']]]
    assert implicit['__x_y_2']['position'] == (2, 0, 1)
    assert implicit['__x_y_1']['position'] == (1, 0, 0)


def test_dummy_nodes_order_dependence():
    #
    #  a   b
    #  c   d
    #
    # bundles a-b, c-d, b-a

    G = nx.DiGraph()
    G.add_nodes_from('abcd', node_group=NodeGroup())
    G.order = [ [['a', 'c']], [['b', 'd']] ]

    # Correct G.order: a-b, c-d, b-a
    G1 = _apply_bundles(G, ('ab', 'cd', 'ba'))
    assert G1.order == [ [['a', '__b_a_0', 'c']], [['b', '__b_a_1', 'd']] ]

    # Incorrect G.order: b-a first
    G2 = _apply_bundles(G, ('ba', 'ab', 'cd'))
    assert G2.order == [ [['a', 'c', '__b_a_0']], [['b', '__b_a_1', 'd']] ]



def _apply_bundles(G, pairs):
    for x, y in pairs:
        G = add_dummy_nodes(G, x, y, bundle_key=None)
    return G
