import networkx as nx
import pandas as pd

from sankeyview.dataset import Dataset
from sankeyview.grouping import Grouping, Group, Hierarchy


def test_group():
    g1 = Group('g1', ('dim1', ('v1', 'v2')))
    g2 = Group('g2', ('dim2', ('x',)))
    g3 = Group('g3', ('dim2', ('y',)))
    assert g1.label == 'g1'
    assert g2.label == 'g2'
    assert g3.label == 'g3'

    G = Grouping(g1, g2)
    assert G.labels == ['g1', 'g2']

    G1 = Grouping(g1)
    G2 = Grouping(g2, g3)

    Gsum = G1 + G2
    assert Gsum.groups == (g1, g2, g3)

    Gprod = G1 * G2
    assert Gprod.groups == (
        Group('g1/g2', ('dim1', ('v1', 'v2')), ('dim2', ('x',))),
        Group('g1/g3', ('dim1', ('v1', 'v2')), ('dim2', ('y',))),
    )


def test_all_grouping():
    G = Grouping.All
    assert G.groups == (Group('*'),)


def test_simple_grouping():
    G = Grouping.Simple('dim1', ['x', 'y'])
    assert G.labels == ['x', 'y']
    assert G.groups == (
        Group('x', ('dim1', ('x',))),
        Group('y', ('dim1', ('y',))),
    )


def test_hierarchy():
    tree = nx.DiGraph()
    tree.add_edges_from([
        ('*', 'stage1'),
        ('*', 'stage2'),
        ('stage1', 'a'),
        ('stage1', 'b'),
        ('stage2', 'c'),
        ('stage2', 'd'),
    ])

    processes = pd.DataFrame.from_records([
        ('a1', 'a'),
        ('a2', 'a'),
        ('b1', 'b'),
        ('c1', 'c'),
        ('d1', 'd'),
    ], columns=('id', 'function')).set_index('id')

    flows = pd.DataFrame.from_records([
    ], columns=('source', 'target', 'material', 'value'))

    dataset = Dataset(processes, flows)

    h = Hierarchy('node.function', tree, dataset)

    assert h.selection('c') == ['c1']
    assert h.selection('c', 'assumed to be a node id') == ['c1', 'assumed to be a node id']
    assert h.selection('stage1') == ['a1', 'a2', 'b1']

    assert h.grouping('stage1', 'stage2') == Grouping(
        Group('stage1', ('node.function', ['a', 'b'])),
        Group('stage2', ('node.function', ['c', 'd'])),
    )
    assert h.grouping('a', 'b1') == Grouping(
        Group('a', ('node.function', ['a'])),
        Group('b1', ('node', ['b1'])),
    )
