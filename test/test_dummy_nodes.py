from floweaver.layered_graph import LayeredGraph, Ordering
from floweaver.dummy_nodes import add_dummy_nodes
from floweaver.sankey_definition import ProcessGroup
from floweaver.partition import Partition


def _twonodes(xrank, xdir, yrank, ydir, **kwargs):
    G = LayeredGraph()
    G.add_node('x', node=ProcessGroup(direction=xdir))
    G.add_node('y', node=ProcessGroup(direction=ydir))
    layers = [[[]] for i in range(max(xrank, yrank) + 1)]
    layers[xrank][0].append('x')
    layers[yrank][0].append('y')
    G.ordering = Ordering(layers)
    kwargs.setdefault('bundle_key', None)
    return add_dummy_nodes(G, 'x', 'y', **kwargs)


def test_dummy_nodes_simple():
    G = _twonodes(0, 'R', 1, 'R', bundle_key=27)
    assert set(G.nodes()) == {'x', 'y'}
    assert set(G.edges()) == {('x', 'y')}
    assert G.ordering == Ordering([[['x']], [['y']]])
    assert G['x']['y']['bundles'] == [27]


def test_dummy_nodes_merge_bundles():
    G = LayeredGraph()
    G.add_node('a', node=ProcessGroup())
    G.add_node('b', node=ProcessGroup())
    G.ordering = Ordering([[['a']], [['b']]])

    G = add_dummy_nodes(G, 'a', 'b', bundle_key=1)
    assert G['a']['b']['bundles'] == [1]

    G = add_dummy_nodes(G, 'a', 'b', bundle_key=2)
    assert G['a']['b']['bundles'] == [1, 2]

    assert set(G.nodes()) == {'a', 'b'}
    assert set(G.edges()) == {('a', 'b')}
    assert G.ordering == Ordering([[['a']], [['b']]])


def test_dummy_nodes_sets_node_attributes():
    G = _twonodes(0, 'R', 2, 'R')
    assert G.nodes['__x_y_1']['node'].partition == None

    G = _twonodes(0, 'R', 2, 'R', node_kwargs=dict(partition=Partition()))
    assert G.nodes['__x_y_1']['node'].partition == Partition()


def test_dummy_nodes_right_RL():
    G = _twonodes(0, 'R', 2, 'L')
    assert set(G.nodes()) == {'x', 'y', '__x_y_1', '__x_y_2'}
    assert set(G.edges()) == {('x', '__x_y_1'), ('__x_y_1', '__x_y_2'),
                              ('__x_y_2', 'y')}
    assert G.ordering == Ordering([[['x']], [['__x_y_1']], [['__x_y_2', 'y']]])


def test_dummy_nodes_right_LR():
    G = _twonodes(0, 'L', 2, 'R')
    assert set(G.nodes()) == {'x', 'y', '__x_y_0', '__x_y_1'}
    assert set(G.edges()) == {('x', '__x_y_0'), ('__x_y_0', '__x_y_1'),
                              ('__x_y_1', 'y')}
    assert G.ordering == Ordering([[['__x_y_0', 'x']], [['__x_y_1']], [['y']]])


def test_dummy_nodes_right_RR():
    G = _twonodes(0, 'R', 2, 'R')
    assert set(G.nodes()) == {'x', 'y', '__x_y_1'}
    assert set(G.edges()) == {('x', '__x_y_1'), ('__x_y_1', 'y')}
    assert G.ordering == Ordering([[['x']], [['__x_y_1']], [['y']]])


def test_dummy_nodes_right_LL():
    G = _twonodes(0, 'L', 2, 'L')
    assert set(G.nodes()) == {'x', 'y', '__x_y_0', '__x_y_1', '__x_y_2'}
    assert set(G.edges()) == {('x', '__x_y_0'), ('__x_y_0', '__x_y_1'),
                              ('__x_y_1', '__x_y_2'), ('__x_y_2', 'y')}
    assert G.ordering == Ordering(
        [[['__x_y_0', 'x']], [['__x_y_1']], [['__x_y_2', 'y']]])


def test_dummy_nodes_left_RL():
    G = _twonodes(2, 'R', 0, 'L')
    assert set(G.nodes()) == {'x', 'y', '__x_y_1', '__x_y_2'}
    assert set(G.edges()) == {('x', '__x_y_2'), ('__x_y_2', '__x_y_1'),
                              ('__x_y_1', 'y')}
    assert G.ordering == Ordering([[['y']], [['__x_y_1']], [['x', '__x_y_2']]])


def test_dummy_nodes_left_LR():
    G = _twonodes(2, 'L', 0, 'R')
    assert set(G.nodes()) == {'x', 'y', '__x_y_0', '__x_y_1'}
    assert set(G.edges()) == {('x', '__x_y_1'), ('__x_y_1', '__x_y_0'),
                              ('__x_y_0', 'y')}
    assert G.ordering == Ordering([[['y', '__x_y_0']], [['__x_y_1']], [['x']]])

    G = _twonodes(1, 'L', 0, 'R')
    assert set(G.nodes()) == {'x', 'y', '__x_y_0'}
    assert set(G.edges()) == {('x', '__x_y_0'), ('__x_y_0', 'y')}
    assert G.ordering == Ordering([[['y', '__x_y_0']], [['x']]])


def test_dummy_nodes_left_LL():
    G = _twonodes(2, 'L', 0, 'L')
    assert set(G.nodes()) == {'x', 'y', '__x_y_1'}
    assert set(G.edges()) == {('x', '__x_y_1'), ('__x_y_1', 'y')}
    assert G.ordering == Ordering([[['y']], [['__x_y_1']], [['x']]])


def test_dummy_nodes_left_RR():
    G = _twonodes(2, 'R', 0, 'R')
    assert set(G.nodes()) == {'x', 'y', '__x_y_0', '__x_y_1', '__x_y_2'}
    assert set(G.edges()) == {('x', '__x_y_2'), ('__x_y_2', '__x_y_1'),
                              ('__x_y_1', '__x_y_0'), ('__x_y_0', 'y')}
    assert G.ordering == Ordering(
        [[['y', '__x_y_0']], [['__x_y_1']], [['x', '__x_y_2']]])


def test_dummy_nodes_order_dependence():
    #
    #  a   b
    #  c   d
    #
    # bundles a-b, c-d, b-a

    G = LayeredGraph()
    G.add_nodes_from('abcd', node=ProcessGroup())
    G.ordering = Ordering([[['a', 'c']], [['b', 'd']]])

    # Correct G.order: a-b, c-d, b-a
    G1 = _apply_bundles(G, ('ab', 'cd', 'ba'))
    assert G1.ordering == Ordering(
        [[['a', '__b_a_0', 'c']], [['b', '__b_a_1', 'd']]])

    # Incorrect G.order: b-a first
    G2 = _apply_bundles(G, ('ba', 'ab', 'cd'))
    assert G2.ordering == Ordering(
        [[['a', 'c', '__b_a_0']], [['b', '__b_a_1', 'd']]])


def _apply_bundles(G, pairs):
    for x, y in pairs:
        G = add_dummy_nodes(G, x, y, bundle_key=None)
    return G
