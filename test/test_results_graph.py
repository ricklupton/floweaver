import pytest

import pandas as pd
import networkx as nx

from sankeyview.results_graph import results_graph
from sankeyview.node import Node
from sankeyview.bundle import Bundle, Elsewhere
from sankeyview.grouping import Grouping
from sankeyview.dataset import Dataset


def test_results_graph():
    material_grouping = Grouping.Simple('material', ['m', 'n'])
    c_grouping = Grouping.Simple('node', ['c1', 'c2'])

    bundles = [
        Bundle('a', 'c', waypoints=['via'], flow_grouping=material_grouping),
        Bundle('b', 'c', waypoints=['via'], flow_grouping=material_grouping),
    ]

    view_graph = nx.DiGraph()
    view_graph.add_node('a', node=Node(selection=True, title='Node a'))  # True as placeholder
    view_graph.add_node('b', node=Node(selection=True))
    view_graph.add_node('c', node=Node(selection=True, grouping=c_grouping))
    view_graph.add_node('via', node=Node(grouping=material_grouping))
    view_graph.add_edges_from([
        ('a', 'via', { 'bundles': [bundles[0]] }),
        ('b', 'via', { 'bundles': [bundles[1]] }),
        ('via', 'c', { 'bundles': bundles }),
    ])
    view_graph_order = [
        [ ['a', 'b'] ], [ ['via'] ], [ ['c'] ]
    ]

    # Mock flow data
    bundle_flows = {
        bundles[0]: pd.DataFrame.from_records([
            ('a1', 'c1', 'm', 3),
            ('a2', 'c1', 'n', 1),
        ], columns=('source', 'target', 'material', 'value')),

        bundles[1]: pd.DataFrame.from_records([
            ('b1', 'c1', 'm', 1),
            ('b1', 'c2', 'm', 2),
            ('b1', 'c2', 'n', 1),
        ], columns=('source', 'target', 'material', 'value'))
    }

    # Do grouping based on flows stored in bundles
    Gr, order, groups, bundles = results_graph(view_graph, view_graph_order, bundle_flows)

    assert sorted(Gr.nodes(data=True)) == [
        ('a^*',   { 'direction': 'R', 'type': 'process', 'bundle': None, 'def_pos': None, 'title': 'Node a' }),
        ('b^*',   { 'direction': 'R', 'type': 'process', 'bundle': None, 'def_pos': None, 'title': 'b' }),
        ('c^c1',  { 'direction': 'R', 'type': 'process', 'bundle': None, 'def_pos': None, 'title': 'c1' }),
        ('c^c2',  { 'direction': 'R', 'type': 'process', 'bundle': None, 'def_pos': None, 'title': 'c2' }),
        ('via^m', { 'direction': 'R', 'type': 'group',   'bundle': None, 'def_pos': None, 'title': 'm' }),
        ('via^n', { 'direction': 'R', 'type': 'group',   'bundle': None, 'def_pos': None, 'title': 'n' }),
    ]
    assert sorted(Gr.edges(keys=True, data=True)) == [
        ('a^*',   'via^m', ('m', '*'), { 'value': 3 }),
        ('a^*',   'via^n', ('n', '*'), { 'value': 1 }),
        ('b^*',   'via^m', ('m', '*'), { 'value': 3 }),
        ('b^*',   'via^n', ('n', '*'), { 'value': 1 }),
        ('via^m', 'c^c1',  ('m', '*'), { 'value': 4 }),
        ('via^m', 'c^c2',  ('m', '*'), { 'value': 2 }),
        ('via^n', 'c^c1',  ('n', '*'), { 'value': 1 }),
        ('via^n', 'c^c2',  ('n', '*'), { 'value': 1 }),
    ]

    assert order == [
        [['a^*', 'b^*']],
        [['via^m', 'via^n']],
        [['c^c1', 'c^c2']],
    ]

    assert groups == [
        {'id': 'a',   'title': 'Node a', 'type': 'process', 'bundle': None, 'def_pos': None, 'processes': ['a^*']},
        {'id': 'b',   'title': '',       'type': 'process', 'bundle': None, 'def_pos': None, 'processes': ['b^*']},
        {'id': 'via', 'title': '',       'type': 'group',   'bundle': None, 'def_pos': None, 'processes': ['via^m', 'via^n']},
        {'id': 'c',   'title': '',       'type': 'process', 'bundle': None, 'def_pos': None, 'processes': ['c^c1', 'c^c2']},
    ]

    # assert bundles == []


def test_results_graph_time_grouping():
    time_grouping = Grouping.Simple('time', [1, 2])
    bundles = [
        Bundle('a', 'b'),
    ]

    view_graph = nx.DiGraph()
    view_graph.add_node('a', node=Node(selection=True))  # True as placeholder
    view_graph.add_node('b', node=Node(selection=True))
    view_graph.add_edges_from([
        ('a', 'b', { 'bundles': bundles }),
    ])
    view_graph_order = [ [['a']], [['b']] ]

    # Mock flow data
    bundle_flows = {
        bundles[0]: pd.DataFrame.from_records([
            ('a1', 'b1', 'm', 1, 3),
            ('a2', 'b1', 'n', 1, 1),
            ('a2', 'b2', 'n', 1, 2),
            ('a1', 'b1', 'm', 2, 1),
            ('a1', 'b1', 'n', 2, 3),
        ], columns=('source', 'target', 'material', 'time', 'value')),
    }

    # Do grouping based on flows stored in bundles
    Gr, order, groups, bundles = results_graph(view_graph, view_graph_order,
                                               bundle_flows, time_grouping=time_grouping)
    assert sorted(Gr.edges(keys=True, data=True)) == [
        ('a^*', 'b^*', ('*', '1'), { 'value': 6 }),
        ('a^*', 'b^*', ('*', '2'), { 'value': 4 }),
    ]

    # Now add a material grouping too
    material_grouping = Grouping.Simple('material', ['m', 'n'])
    Gr, order, groups, bundles = results_graph(view_graph, view_graph_order,
                                               bundle_flows, material_grouping,
                                               time_grouping)
    assert sorted(Gr.edges(keys=True, data=True)) == [
        ('a^*', 'b^*', ('m', '1'), { 'value': 3 }),
        ('a^*', 'b^*', ('m', '2'), { 'value': 1 }),
        ('a^*', 'b^*', ('n', '1'), { 'value': 3 }),
        ('a^*', 'b^*', ('n', '2'), { 'value': 3 }),
    ]


def test_results_graph_material_key():
    # Mock flow data
    flows = pd.DataFrame.from_records([
        ('a1', 'c1', 'm', 'long', 3),
        ('a1', 'c1', 'n', 'long', 1),
    ], columns=('source', 'target', 'material_type', 'shape', 'value'))

    view_graph = nx.DiGraph()
    view_graph.add_node('a', node=Node(selection=True))  # True as placeholder
    view_graph.add_node('c', node=Node(selection=True))
    view_graph.add_edge('a', 'c')
    view_graph_order = [
        [['a']], [['c']]
    ]

    material_grouping = Grouping.Simple('material_type', ['m', 'n'])
    shape_grouping = Grouping.Simple('shape', ['long', 'thin'])

    # Grouping based on material_type
    bundle = Bundle('a', 'c', flow_grouping=material_grouping)
    bundle_flows = { bundle: flows }
    view_graph.edge['a']['c']['bundles'] = [bundle]
    Gr, order, groups, bundles = results_graph(view_graph, view_graph_order, bundle_flows)
    assert sorted(Gr.edges(keys=True, data=True)) == [
        ('a^*', 'c^*', ('m', '*'), { 'value': 3 }),
        ('a^*', 'c^*', ('n', '*'), { 'value': 1 }),
    ]

    # Grouping based on shape
    bundle = Bundle('a', 'c', flow_grouping=shape_grouping)
    bundle_flows = { bundle: flows }
    view_graph.edge['a']['c']['bundles'] = [bundle]
    Gr, order, groups, bundles = results_graph(view_graph, view_graph_order, bundle_flows)
    assert sorted(Gr.edges(keys=True, data=True)) == [
        ('a^*', 'c^*', ('long', '*'), { 'value': 4 }),
    ]


def test_results_graph_bundle_flow_groupings_must_be_equal():
    material_grouping_mn = Grouping.Simple('material', ['m', 'n'])
    material_grouping_XY = Grouping.Simple('material', ['X', 'Y'])
    bundles = [
        Bundle('a', 'c', waypoints=['via'], flow_grouping=material_grouping_mn),
        Bundle('b', 'c', waypoints=['via'], flow_grouping=material_grouping_XY),
    ]

    # Mock flow data
    bundle_flows = {
        bundles[0]: pd.DataFrame.from_records([
        ], columns=('source', 'target', 'material', 'value')),

        bundles[1]: pd.DataFrame.from_records([
        ], columns=('source', 'target', 'material', 'value'))
    }

    view_graph = nx.DiGraph()
    view_graph.add_node('a', node=Node(selection=True))  # True as placeholder
    view_graph.add_node('b', node=Node(selection=True))
    view_graph.add_node('c', node=Node(selection=True))
    view_graph.add_node('via', node=Node(grouping=material_grouping_mn))
    view_graph.add_edges_from([
        ('a', 'via', { 'bundles': [bundles[0]] }),
        ('b', 'via', { 'bundles': [bundles[1]] }),
        ('via', 'c', { 'bundles': bundles }),
    ])
    view_graph_order = [
        [['a', 'b']], [['via']], [['c']]
    ]

    # Do grouping based on flows stored in bundles
    with pytest.raises(ValueError):
        Gr, order, order = results_graph(view_graph, view_graph_order, bundle_flows)


def test_results_graph_unused_nodes():
    bundles = [Bundle('a', 'b')]

    # Mock flow data: b2 not used
    bundle_flows = {
        bundles[0]: pd.DataFrame.from_records([
            ('a1', 'b1', 'm', 3),
            ('a2', 'b1', 'n', 1),
        ], columns=('source', 'target', 'material', 'value'))
    }

    view_graph = nx.DiGraph()
    view_graph.add_node('a', node=Node(selection=True, grouping=Grouping.Simple('node', ['a1', 'a2'])))  # True as placeholder
    view_graph.add_node('b', node=Node(selection=True, grouping=Grouping.Simple('node', ['b1', 'b2'])))
    view_graph.add_edges_from([
        ('a', 'b', { 'bundles': bundles }),
    ])
    view_graph_order = [
        [['a']], [['b']]
    ]

    # Do grouping based on flows stored in bundles
    Gr, order, groups, bundles = results_graph(view_graph, view_graph_order, bundle_flows)

    assert set(Gr.nodes()) == {'a^a1', 'a^a2', 'b^b1'}
    assert sorted(Gr.edges(keys=True, data=True)) == [
        ('a^a1', 'b^b1', ('*', '*'), { 'value': 3 }),
        ('a^a2', 'b^b1', ('*', '*'), { 'value': 1 }),
    ]

    assert order == [
        [['a^a1', 'a^a2']],
        [['b^b1']],
    ]


def test_results_graph_with_extra_or_not_enough_groups():
    bundles = [Bundle('a', 'b')]

    # Mock flow data
    bundle_flows = {
        bundles[0]: pd.DataFrame.from_records([
            ('a1', 'b1', 'm', 3),
            ('a2', 'b1', 'm', 1),
        ], columns=('source', 'target', 'material', 'value'))
    }

    # Group 'a3' not used. Node 'a2' isn't in any group.
    node_a = Node(grouping=Grouping.Simple('node', ['a1', 'a3']))
    node_b = Node(grouping=Grouping.Simple('node', ['b1']))
    view_graph = nx.DiGraph()
    view_graph.add_node('a', node=node_a)
    view_graph.add_node('b', node=node_b)
    view_graph.add_edges_from([
        ('a', 'b', { 'bundles': bundles }),
    ])
    view_graph_order = [
        [['a']], [['b']]
    ]

    # Do grouping based on flows stored in bundles
    Gr, order, groups, bundles = results_graph(view_graph, view_graph_order, bundle_flows)

    assert set(Gr.nodes()) == {'a^a1', 'a^_', 'b^b1'}
    assert sorted(Gr.edges(keys=True, data=True)) == [
        ('a^_',  'b^b1', ('*', '*'), { 'value': 1 }),
        ('a^a1', 'b^b1', ('*', '*'), { 'value': 3 }),
    ]

    assert order == [
        [['a^a1', 'a^_']],
        [['b^b1']],
    ]


def test_results_graph_bands():
    bundles = [
        Bundle('a', 'b'),
    ]

    # Mock flow data
    bundle_flows = {
        bundles[0]: pd.DataFrame.from_records([
            ('a1', 'b1', 'm', 3),
        ], columns=('source', 'target', 'material', 'value'))
    }

    view_graph = nx.DiGraph()
    view_graph.add_node('a', node=Node(selection=True))  # True as placeholder
    view_graph.add_node('b', node=Node(selection=True))
    view_graph.add_edges_from([
        ('a', 'b', { 'bundles': bundles }),
    ])

    view_graph_order = [
        [ ['a'], [   ] ],
        [ [   ], ['b'] ],
    ]

    # Do grouping based on flows stored in bundles
    Gr, order, groups, bundles = results_graph(view_graph, view_graph_order, bundle_flows)

    assert order == [
        # rank 1
        [ [ 'a^*' ], [] ],
        # rank 2
        [ [], [ 'b^*' ] ],
    ]
