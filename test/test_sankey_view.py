import pandas as pd

from sankeyview.sankey_definition import SankeyDefinition, Ordering, ProcessGroup, Waypoint, Bundle
from sankeyview.sankey_view import sankey_view
from sankeyview.partition import Partition
from sankeyview.dataset import Dataset


def test_sankey_view_results():
    nodes = {
        'a': ProcessGroup(selection=['a1', 'a2']),
        'b': ProcessGroup(selection=['b1']),
        'c': ProcessGroup(selection=['c1', 'c2'],
                          partition=Partition.Simple('process', ['c1', 'c2'])),
        'via': Waypoint(partition=Partition.Simple('material', ['m', 'n'])),
    }
    bundles = [
        Bundle('a', 'c', waypoints=['via']),
        Bundle('b', 'c', waypoints=['via']),
    ]
    ordering = [[['a', 'b']], [['via']], [['c']]]
    vd = SankeyDefinition(nodes, bundles, ordering)

    # Dataset
    flows = pd.DataFrame.from_records(
        [
            ('a1', 'c1', 'm', 3),
            ('a2', 'c1', 'n', 1),
            ('b1', 'c1', 'm', 1),
            ('b1', 'c2', 'm', 2),
            ('b1', 'c2', 'n', 1),
        ],
        columns=('source', 'target', 'material', 'value'))
    processes = pd.DataFrame({
        'id': list(flows.source.unique()) + list(flows.target.unique())
    }).set_index('id')
    dataset = Dataset(processes, flows)

    GR, groups = sankey_view(vd, dataset)

    assert set(GR.nodes()) == {'a^*', 'b^*', 'via^m', 'via^n', 'c^c1', 'c^c2'}
    assert sorted(GR.edges(keys=True, data=True)) == [
        ('a^*', 'via^m', ('*', '*'), {'value': 3,
                                      'bundles': [0]}),
        ('a^*', 'via^n', ('*', '*'), {'value': 1,
                                      'bundles': [0]}),
        ('b^*', 'via^m', ('*', '*'), {'value': 3,
                                      'bundles': [1]}),
        ('b^*', 'via^n', ('*', '*'), {'value': 1,
                                      'bundles': [1]}),
        ('via^m', 'c^c1', ('*', '*'), {'value': 4,
                                       'bundles': [0, 1]}),
        ('via^m', 'c^c2', ('*', '*'), {'value': 2,
                                       'bundles': [0, 1]}),
        ('via^n', 'c^c1', ('*', '*'), {'value': 1,
                                       'bundles': [0, 1]}),
        ('via^n', 'c^c2', ('*', '*'), {'value': 1,
                                       'bundles': [0, 1]}),
    ]

    assert GR.ordering == Ordering([
        [['a^*', 'b^*']],
        [['via^m', 'via^n']],
        [['c^c1', 'c^c2']],
    ])
    assert groups == [
        {'id': 'a',
         'title': '',
         'type': 'process',
         'nodes': ['a^*']},
        {'id': 'b',
         'title': '',
         'type': 'process',
         'nodes': ['b^*']},
        {'id': 'via',
         'title': '',
         'type': 'group',
         'nodes': ['via^m', 'via^n']},
        {'id': 'c',
         'title': '',
         'type': 'process',
         'nodes': ['c^c1', 'c^c2']},
    ]

    # Can also set flow_partition for all bundles at once
    vd2 = SankeyDefinition(
        nodes,
        bundles,
        ordering,
        flow_partition=Partition.Simple('material', ['m', 'n']))
    GR, groups = sankey_view(vd2, dataset)
    assert sorted(GR.edges(keys=True, data=True)) == [
        ('a^*', 'via^m', ('m', '*'), {'value': 3,
                                      'bundles': [0]}),
        ('a^*', 'via^n', ('n', '*'), {'value': 1,
                                      'bundles': [0]}),
        ('b^*', 'via^m', ('m', '*'), {'value': 3,
                                      'bundles': [1]}),
        ('b^*', 'via^n', ('n', '*'), {'value': 1,
                                      'bundles': [1]}),
        ('via^m', 'c^c1', ('m', '*'), {'value': 4,
                                       'bundles': [0, 1]}),
        ('via^m', 'c^c2', ('m', '*'), {'value': 2,
                                       'bundles': [0, 1]}),
        ('via^n', 'c^c1', ('n', '*'), {'value': 1,
                                       'bundles': [0, 1]}),
        ('via^n', 'c^c2', ('n', '*'), {'value': 1,
                                       'bundles': [0, 1]}),
    ]


def test_sankey_view_results_time_partition():
    nodes = {
        'a': ProcessGroup(selection=['a1']),
        'b': ProcessGroup(selection=['b1']),
    }
    bundles = [Bundle('a', 'b')]
    ordering = [[['a']], [['b']]]
    time_partition = Partition.Simple('time', [1, 2])
    vd = SankeyDefinition(
        nodes, bundles, ordering,
        time_partition=time_partition)

    # Dataset
    flows = pd.DataFrame.from_records(
        [
            ('a1', 'b1', 'm', 1, 3),
            ('a1', 'b1', 'm', 2, 2),
        ],
        columns=('source', 'target', 'material', 'time', 'value'))
    processes = pd.DataFrame({'id': ['a1', 'b1']}).set_index('id')
    dataset = Dataset(processes, flows)

    GR, groups = sankey_view(vd, dataset)
    assert set(GR.nodes()) == {'a^*', 'b^*'}
    assert sorted(GR.edges(keys=True, data=True)) == [
        ('a^*', 'b^*', ('*', '1'), {'value': 3,
                                    'bundles': [0]}),
        ('a^*', 'b^*', ('*', '2'), {'value': 2,
                                    'bundles': [0]}),
    ]
    assert GR.ordering == Ordering([[['a^*']], [['b^*']]])
