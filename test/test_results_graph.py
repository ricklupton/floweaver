import numpy as np
import pandas as pd

from floweaver.layered_graph import LayeredGraph, Ordering
from floweaver.results_graph import results_graph
from floweaver.sankey_definition import ProcessGroup, Waypoint, Bundle
from floweaver.partition import Partition


def test_results_graph_overall():
    material_partition = Partition.Simple('material', ['m', 'n'])
    c_partition = Partition.Simple('process', ['c1', 'c2'])

    view_graph = LayeredGraph()
    view_graph.add_node('a', node=ProcessGroup(title='Node a'))
    view_graph.add_node('b', node=ProcessGroup())
    view_graph.add_node('c', node=ProcessGroup(partition=c_partition))
    view_graph.add_node('via', node=Waypoint(partition=material_partition))
    view_graph.add_edges_from([
        ('a', 'via', {'bundles': [0],
                      'flow_partition': material_partition}),
        ('b', 'via', {'bundles': [1],
                      'flow_partition': material_partition}),
        ('via', 'c', {'bundles': [0, 1],
                      'flow_partition': material_partition}),
    ])
    view_graph.ordering = Ordering([[['a', 'b']], [['via']], [['c']]])

    # Mock flow data
    bundle_flows = {
        0: pd.DataFrame.from_records(
            [
                ('a1', 'c1', 'm', 3),
                ('a2', 'c1', 'n', 1),
            ],
            index=(0, 1),
            columns=('source', 'target', 'material', 'value')),
        1: pd.DataFrame.from_records(
            [
                ('b1', 'c1', 'm', 1),
                ('b1', 'c2', 'm', 2),
                ('b1', 'c2', 'n', 1),
            ],
            index=(2, 3, 4),
            columns=('source', 'target', 'material', 'value'))
    }

    # Do partition based on flows stored in bundles
    Gr, groups = results_graph(view_graph, bundle_flows)

    assert sorted(Gr.nodes(data=True)) == [
        ('a^*', {'direction': 'R',
                 'type': 'process',
                 'title': 'Node a'}),
        ('b^*', {'direction': 'R',
                 'type': 'process',
                 'title': 'b'}),
        ('c^c1', {'direction': 'R',
                  'type': 'process',
                  'title': 'c1'}),
        ('c^c2', {'direction': 'R',
                  'type': 'process',
                  'title': 'c2'}),
        ('via^m', {'direction': 'R',
                   'type': 'group',
                   'title': 'm'}),
        ('via^n', {'direction': 'R',
                   'type': 'group',
                   'title': 'n'}),
    ]
    assert sorted(Gr.edges(keys=True, data=True)) == [
        ('a^*', 'via^m',  ('m', '*'), {'measures': {'value': 3}, 'original_flows': [0], 'bundles': [0]}),
        ('a^*', 'via^n',  ('n', '*'), {'measures': {'value': 1}, 'original_flows': [1], 'bundles': [0]}),
        ('b^*', 'via^m',  ('m', '*'), {'measures': {'value': 3}, 'original_flows': [2, 3], 'bundles': [1]}),
        ('b^*', 'via^n',  ('n', '*'), {'measures': {'value': 1}, 'original_flows': [4], 'bundles': [1]}),
        ('via^m', 'c^c1', ('m', '*'), {'measures': {'value': 4}, 'original_flows': [0, 2], 'bundles': [0, 1]}),
        ('via^m', 'c^c2', ('m', '*'), {'measures': {'value': 2}, 'original_flows': [3], 'bundles': [0, 1]}),
        ('via^n', 'c^c1', ('n', '*'), {'measures': {'value': 1}, 'original_flows': [1], 'bundles': [0, 1]}),
        ('via^n', 'c^c2', ('n', '*'), {'measures': {'value': 1}, 'original_flows': [4], 'bundles': [0, 1]}),
    ]

    assert Gr.ordering == Ordering([
        [['a^*', 'b^*']],
        [['via^m', 'via^n']],
        [['c^c1', 'c^c2']],
    ])

    # Only includes groups where the title is not the same as the single node
    # title
    assert groups == [
        {'id': 'via',
         'title': '',
         'type': 'group',
         'nodes': ['via^m', 'via^n']},
        {'id': 'c',
         'title': '',
         'type': 'process',
         'nodes': ['c^c1', 'c^c2']},
    ]


def test_results_graph_time_partition():
    time_partition = Partition.Simple('time', [1, 2])

    view_graph = LayeredGraph()
    view_graph.add_node('a', node=ProcessGroup())
    view_graph.add_node('b', node=ProcessGroup())
    view_graph.add_edges_from([('a', 'b', {'bundles': [0]}), ])
    view_graph.ordering = Ordering([[['a']], [['b']]])

    # Mock flow data
    bundle_flows = {
        0: pd.DataFrame.from_records(
            [
                ('a1', 'b1', 'm', 1, 3),
                ('a2', 'b1', 'n', 1, 1),
                ('a2', 'b2', 'n', 1, 2),
                ('a1', 'b1', 'm', 2, 1),
                ('a1', 'b1', 'n', 2, 3),
            ],
            columns=('source', 'target', 'material', 'time', 'value')),
    }

    # Do partition based on flows stored in bundles
    Gr, groups = results_graph(view_graph,
                               bundle_flows,
                               time_partition=time_partition)
    assert sorted(Gr.edges(keys=True, data=True)) == [
        ('a^*', 'b^*', ('*', '1'), {'measures': {'value': 6}, 'original_flows': [0, 1, 2], 'bundles': [0]}),
        ('a^*', 'b^*', ('*', '2'), {'measures': {'value': 4}, 'original_flows': [3, 4], 'bundles': [0]}),
    ]

    # Now add a material partition too
    material_partition = Partition.Simple('material', ['m', 'n'])
    Gr, groups = results_graph(view_graph, bundle_flows, material_partition,
                               time_partition)
    assert sorted(Gr.edges(keys=True, data=True)) == [
        ('a^*', 'b^*', ('m', '1'), {'measures': {'value': 3}, 'original_flows': [0], 'bundles': [0]}),
        ('a^*', 'b^*', ('m', '2'), {'measures': {'value': 1}, 'original_flows': [3], 'bundles': [0]}),
        ('a^*', 'b^*', ('n', '1'), {'measures': {'value': 3}, 'original_flows': [1, 2], 'bundles': [0]}),
        ('a^*', 'b^*', ('n', '2'), {'measures': {'value': 3}, 'original_flows': [4], 'bundles': [0]}),
    ]


def test_results_graph_material_key():
    # Mock flow data
    flows = pd.DataFrame.from_records(
        [
            ('a1', 'c1', 'm', 'long', 3),
            ('a1', 'c1', 'n', 'long', 1),
        ],
        columns=('source', 'target', 'material_type', 'shape', 'value'))

    view_graph = LayeredGraph()
    view_graph.add_node('a', node=ProcessGroup())
    view_graph.add_node('c', node=ProcessGroup())
    view_graph.add_edge('a', 'c', bundles=[0])
    view_graph.ordering = Ordering([[['a']], [['c']]])
    bundle_flows = {0: flows}

    material_partition = Partition.Simple('material_type', ['m', 'n'])
    shape_partition = Partition.Simple('shape', ['long', 'thin'])

    # Partition based on material_type
    view_graph.edges['a', 'c']['flow_partition'] = material_partition
    Gr, groups = results_graph(view_graph, bundle_flows)
    assert sorted(Gr.edges(keys=True, data=True)) == [
        ('a^*', 'c^*', ('m', '*'), {'measures': {'value': 3}, 'original_flows': [0], 'bundles': [0]}),
        ('a^*', 'c^*', ('n', '*'), {'measures': {'value': 1}, 'original_flows': [1], 'bundles': [0]}),
    ]

    # Partition based on shape
    view_graph.edges['a', 'c']['flow_partition'] = shape_partition
    Gr, groups = results_graph(view_graph, bundle_flows)
    assert sorted(Gr.edges(keys=True, data=True)) == [
        ('a^*', 'c^*', ('long', '*'), {'measures': {'value': 4}, 'original_flows': [0, 1], 'bundles': [0]}),
    ]


def test_results_graph_measures():
    view_graph = _twonode_viewgraph()

    # Mock flow data
    bundle_flows = {
        0: pd.DataFrame.from_records([
            ('a', 'b1', 'm', 4, 2),
            ('a', 'b2', 'm', 7, 1),
        ],
        columns=('source', 'target', 'material',
                 'value', 'another_measure')),
    }

    # Results assuming measure = 'value'
    Gr, groups = results_graph(view_graph, bundle_flows)
    assert list(Gr.edges(keys=True, data=True)) == [
        ('a^*', 'b^*', ('*', '*'), {'measures': {'value': 11},
                                    'original_flows': [0, 1],
                                    'bundles': [0]}),
    ]

    # Results using measure = 'another_measure'
    Gr, groups = results_graph(view_graph,
                               bundle_flows,
                               measures='another_measure')
    assert list(Gr.edges(keys=True, data=True)) == [
        ('a^*', 'b^*', ('*', '*'), {'measures': {'another_measure': 3},
                                    'original_flows': [0, 1],
                                    'bundles': [0]}),
    ]

    # Results using measure = 'value' but averaging 'another_measure'
    Gr, groups = results_graph(view_graph,
                               bundle_flows,
                               measures={'value': 'sum', 'another_measure': 'mean'})
    assert list(Gr.edges(keys=True, data=True)) == [
        ('a^*', 'b^*', ('*', '*'), {'measures': {'value': 11, 'another_measure': 1.5},
                                    'original_flows': [0, 1],
                                    'bundles': [0]}),
    ]


def test_results_graph_samples():
    view_graph = _threenode_viewgraph()

    # Mock flow data with multiple samples. NB missing data for sample 1 in
    # bundle 1.
    bundle_flows = {
        0: pd.DataFrame.from_records(
            [
                ('a', 'b1', 'm', 0, 2),
                ('a', 'b1', 'm', 1, 3),
                ('a', 'b2', 'm', 0, 1),
                ('a', 'b2', 'm', 1, 1),
            ],
            columns=('source', 'target', 'material', 'sample', 'value')),
        1: pd.DataFrame.from_records(
            [
                ('a', 'c1', 'm', 1, 3),
            ],
            columns=('source', 'target', 'material', 'sample', 'value')),
    }

    # Aggregation function
    index = pd.Index(np.arange(2))
    def measure(group):
        agg = group.groupby('sample').value.agg('sum')
        d = {'value': agg.reindex(index).fillna(0).values}
        return d

    # Results
    Gr, groups = results_graph(view_graph, bundle_flows, measures=measure)
    assert len(Gr.edges()) == 2
    assert np.allclose(Gr['a^*']['b^*']['*', '*']['measures']['value'], [3, 4])
    assert np.allclose(Gr['a^*']['c^*']['*', '*']['measures']['value'], [0, 3])


def test_results_graph_unused_nodes():
    # Mock flow data: b2 not used
    bundle_flows = {
        0: pd.DataFrame.from_records(
            [
                ('a1', 'b1', 'm', 3),
                ('a2', 'b1', 'n', 1),
            ],
            columns=('source', 'target', 'material', 'value'))
    }

    partition_a = Partition.Simple('process', ['a1', 'a2'])
    partition_b = Partition.Simple('process', ['b1', 'b2'])

    view_graph = LayeredGraph()
    view_graph.add_node('a', node=ProcessGroup(partition=partition_a))
    view_graph.add_node('b', node=ProcessGroup(partition=partition_b))
    view_graph.add_edges_from([('a', 'b', {'bundles': [0]}), ])
    view_graph.ordering = Ordering([[['a']], [['b']]])

    # Do partition based on flows stored in bundles
    Gr, groups = results_graph(view_graph, bundle_flows)

    assert set(Gr.nodes()) == {'a^a1', 'a^a2', 'b^b1'}
    assert sorted(Gr.edges(keys=True, data=True)) == [
        ('a^a1', 'b^b1', ('*', '*'), {'measures': {'value': 3}, 'original_flows': [0], 'bundles': [0]}),
        ('a^a2', 'b^b1', ('*', '*'), {'measures': {'value': 1}, 'original_flows': [1], 'bundles': [0]}),
    ]

    assert Gr.ordering == Ordering([
        [['a^a1', 'a^a2']],
        [['b^b1']],
    ])


def test_results_graph_with_extra_or_not_enough_groups():
    # Mock flow data
    bundle_flows = {
        0: pd.DataFrame.from_records(
            [
                ('a1', 'b1', 'm', 3),
                ('a2', 'b1', 'm', 1),
            ],
            columns=('source', 'target', 'material', 'value'))
    }

    # Group 'a3' not used. ProcessGroup 'a2' isn't in any group.
    node_a = ProcessGroup(partition=Partition.Simple('process', ['a1', 'a3']))
    node_b = ProcessGroup(partition=Partition.Simple('process', ['b1']))
    view_graph = LayeredGraph()
    view_graph.add_node('a', node=node_a)
    view_graph.add_node('b', node=node_b)
    view_graph.add_edges_from([('a', 'b', {'bundles': [0]}), ])
    view_graph.ordering = Ordering([[['a']], [['b']]])

    # Do partition based on flows stored in bundles
    Gr, groups = results_graph(view_graph, bundle_flows)

    assert set(Gr.nodes()) == {'a^a1', 'a^_', 'b^b1'}
    assert sorted(Gr.edges(keys=True, data=True)) == [
        ('a^_', 'b^b1', ('*', '*'), {'measures': {'value': 1}, 'original_flows': [1], 'bundles': [0]}),
        ('a^a1', 'b^b1', ('*', '*'), {'measures': {'value': 3}, 'original_flows': [0], 'bundles': [0]}),
    ]

    assert Gr.ordering == Ordering([
        [['a^a1', 'a^_']],
        [['b^b1']],
    ])


def test_results_graph_bands():
    bundles = [Bundle('a', 'b'), ]

    # Mock flow data
    bundle_flows = {
        bundles[0]: pd.DataFrame.from_records(
            [
                ('a1', 'b1', 'm', 3),
            ],
            columns=('source', 'target', 'material', 'value'))
    }

    view_graph = LayeredGraph()
    view_graph.add_node('a', node=ProcessGroup())
    view_graph.add_node('b', node=ProcessGroup())
    view_graph.add_edges_from([('a', 'b', {'bundles': bundles}), ])

    view_graph.ordering = Ordering([
        [['a'], []],
        [[], ['b']],
    ])

    # Do partition based on flows stored in bundles
    Gr, groups = results_graph(view_graph, bundle_flows)

    assert Gr.ordering == Ordering([
        # rank 1
        [['a^*'], []],
        # rank 2
        [[], ['b^*']],
    ])


def _twonode_viewgraph():
    view_graph = LayeredGraph()
    view_graph.add_node('a', node=ProcessGroup())
    view_graph.add_node('b', node=ProcessGroup())
    view_graph.add_edge('a', 'b', bundles=[0])
    view_graph.ordering = Ordering([
        [['a']],
        [['b']],
    ])
    return view_graph


def _threenode_viewgraph():
    view_graph = LayeredGraph()
    view_graph.add_node('a', node=ProcessGroup())
    view_graph.add_node('b', node=ProcessGroup())
    view_graph.add_node('c', node=ProcessGroup())
    view_graph.add_edge('a', 'b', bundles=[0])
    view_graph.add_edge('a', 'c', bundles=[1])
    view_graph.ordering = Ordering([
        [['a']],
        [['b', 'c']],
    ])
    return view_graph
