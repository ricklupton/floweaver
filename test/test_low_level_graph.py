import pytest

import networkx as nx
import pandas as pd

from sankeyview.bundle import Bundle
from sankeyview.node import Node
from sankeyview.grouping import Group, Grouping
from sankeyview.low_level_graph import low_level_graph


def test_low_level_graph():
    material_grouping = Grouping.Simple('material', ['m', 'n'])
    bundles = [
        Bundle('a', 'c', waypoints=['via'], flow_grouping=material_grouping),
        Bundle('b', 'c', waypoints=['via'], flow_grouping=material_grouping),
    ]

    # Mock flow data
    bundles[0].flows = pd.DataFrame.from_records([
        ('a1', 'c1', 'm', 3),
        ('a2', 'c1', 'n', 1),
    ], columns=('source', 'target', 'material', 'value'))

    bundles[1].flows = pd.DataFrame.from_records([
        ('b1', 'c1', 'm', 1),
        ('b1', 'c2', 'm', 2),
        ('b1', 'c2', 'n', 1),
    ], columns=('source', 'target', 'material', 'value'))

    HL = nx.DiGraph()
    HL.add_node('a', node=Node(0, 0, query=True))  # True as placeholder
    HL.add_node('b', node=Node(0, 0, query=True))
    HL.add_node('c', node=Node(2, 0, query=True, grouping=Grouping.Simple('node', ['c1', 'c2'])))
    HL.add_node('via', node=Node(1, 0, grouping=material_grouping))
    HL.add_edges_from([
        ('a', 'via', { 'bundles': [bundles[0]] }),
        ('b', 'via', { 'bundles': [bundles[1]] }),
        ('via', 'c', { 'bundles': bundles }),
    ])

    # Do grouping based on flows stored in bundles
    G, order = low_level_graph(HL)

    assert set(G.nodes()) == {'a^*', 'b^*', 'via^m', 'via^n', 'c^c1', 'c^c2'}
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

    assert order == [
        [['a^*', 'b^*']],
        [['via^m', 'via^n']],
        [['c^c1', 'c^c2']],
    ]


def test_low_level_graph_material_key():
    # Mock flow data
    flows = pd.DataFrame.from_records([
        ('a1', 'c1', 'm', 'long', 3),
        ('a1', 'c1', 'n', 'long', 1),
    ], columns=('source', 'target', 'material_type', 'shape', 'value'))

    HL = nx.DiGraph()
    HL.add_node('a', node=Node(0, 0, query=True))  # True as placeholder
    HL.add_node('c', node=Node(1, 0, query=True))
    HL.add_edge('a', 'c')

    material_grouping = Grouping.Simple('material_type', ['m', 'n'])
    shape_grouping = Grouping.Simple('shape', ['long', 'thin'])

    # Grouping based on material_type
    bundle = Bundle('a', 'c', flow_grouping=material_grouping)
    bundle.flows = flows
    HL.edge['a']['c']['bundles'] = [bundle]
    G, order = low_level_graph(HL)
    assert sorted(G.edges(keys=True, data=True)) == [
        ('a^*', 'c^*', 'm', { 'value': 3 }),
        ('a^*', 'c^*', 'n', { 'value': 1 }),
    ]

    # Grouping based on shape
    bundle = Bundle('a', 'c', flow_grouping=shape_grouping)
    bundle.flows = flows
    HL.edge['a']['c']['bundles'] = [bundle]
    G, order = low_level_graph(HL)
    assert sorted(G.edges(keys=True, data=True)) == [
        ('a^*', 'c^*', 'long', { 'value': 4 }),
    ]


def test_low_level_graph_bundle_flow_groupings_must_be_equal():
    material_grouping_mn = Grouping.Simple('material', ['m', 'n'])
    material_grouping_XY = Grouping.Simple('material', ['X', 'Y'])
    bundles = [
        Bundle('a', 'c', waypoints=['via'], flow_grouping=material_grouping_mn),
        Bundle('b', 'c', waypoints=['via'], flow_grouping=material_grouping_XY),
    ]

    # Mock flow data
    bundles[0].flows = pd.DataFrame.from_records([
    ], columns=('source', 'target', 'material', 'value'))

    bundles[1].flows = pd.DataFrame.from_records([
    ], columns=('source', 'target', 'material', 'value'))

    HL = nx.DiGraph()
    HL.add_node('a', node=Node(0, 0, query=True))  # True as placeholder
    HL.add_node('b', node=Node(0, 0, query=True))
    HL.add_node('c', node=Node(2, 0, query=True))
    HL.add_node('via', node=Node(1, 0, grouping=material_grouping_mn))
    HL.add_edges_from([
        ('a', 'via', { 'bundles': [bundles[0]] }),
        ('b', 'via', { 'bundles': [bundles[1]] }),
        ('via', 'c', { 'bundles': bundles }),
    ])

    # Do grouping based on flows stored in bundles
    with pytest.raises(ValueError):
        G, order = low_level_graph(HL)


def test_low_level_graph_unused_nodes():
    bundles = [Bundle('a', 'b')]

    # Mock flow data: b2 not used
    bundles[0].flows = pd.DataFrame.from_records([
        ('a1', 'b1', 'm', 3),
        ('a2', 'b1', 'n', 1),
    ], columns=('source', 'target', 'material', 'value'))

    HL = nx.DiGraph()
    HL.add_node('a', node=Node(0, 0, query=True, grouping=Grouping.Simple('node', ['a1', 'a2'])))  # True as placeholder
    HL.add_node('b', node=Node(1, 0, query=True, grouping=Grouping.Simple('node', ['b1', 'b2'])))
    HL.add_edges_from([
        ('a', 'b', { 'bundles': bundles }),
    ])

    # Do grouping based on flows stored in bundles
    G, order = low_level_graph(HL)

    assert set(G.nodes()) == {'a^a1', 'a^a2', 'b^b1'}
    assert sorted(G.edges(keys=True, data=True)) == [
        ('a^a1', 'b^b1', '*', { 'value': 3 }),
        ('a^a2', 'b^b1', '*', { 'value': 1 }),
    ]

    assert order == [
        [['a^a1', 'a^a2']],
        [['b^b1']],
    ]


def test_low_level_graph_with_extra_or_not_enough_groups():
    bundles = [Bundle('a', 'b')]

    # Mock flow data
    bundles[0].flows = pd.DataFrame.from_records([
        ('a1', 'b1', 'm', 3),
        ('a2', 'b1', 'm', 1),
    ], columns=('source', 'target', 'material', 'value'))

    # Group 'a3' not used. Node 'a2' isn't in any group.
    node_a = Node(0, 0, grouping=Grouping.Simple('node', ['a1', 'a3']))
    node_b = Node(1, 0, grouping=Grouping.Simple('node', ['b1']))
    HL = nx.DiGraph()
    HL.add_node('a', node=node_a)
    HL.add_node('b', node=node_b)
    HL.add_edges_from([
        ('a', 'b', { 'bundles': bundles }),
    ])

    # Do grouping based on flows stored in bundles
    G, order = low_level_graph(HL)

    assert set(G.nodes()) == {'a^a1', 'a^_', 'b^b1'}
    assert sorted(G.edges(keys=True, data=True)) == [
        ('a^_',  'b^b1', '*', { 'value': 1 }),
        ('a^a1', 'b^b1', '*', { 'value': 3 }),
    ]

    assert order == [
        [['a^a1', 'a^_']],
        [['b^b1']],
    ]


def test_low_level_graph_dividers():
    bundles = [
        Bundle('a', 'b'),
    ]

    # Mock flow data
    bundles[0].flows = pd.DataFrame.from_records([
        ('a1', 'b1', 'm', 3),
    ], columns=('source', 'target', 'material', 'value'))

    HL = nx.DiGraph()
    HL.add_node('a', node=Node(0, 0, query=True))  # True as placeholder
    HL.add_node('b', node=Node(1, 2, query=True))
    HL.add_edges_from([
        ('a', 'b', { 'bundles': bundles }),
    ])

    dividers = [1]  # split at depth == 1

    # Do grouping based on flows stored in bundles
    G, order = low_level_graph(HL, dividers=dividers)

    assert order == [
        # rank 1
        [ [ 'a^*' ], [] ],
        # rank 2
        [ [], [ 'b^*' ] ],
    ]
