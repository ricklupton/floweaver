import pandas as pd

from floweaver.sankey_definition import SankeyDefinition, Ordering, ProcessGroup, Waypoint, Bundle
from floweaver.color_scales import CategoricalScale
from floweaver.weave import weave
from floweaver.partition import Partition
from floweaver.dataset import Dataset
from floweaver.sankey_data import SankeyNode, SankeyLink

from matchers import inst


def test_weave_accepts_dataframe_as_dataset():
    nodes = {
        'a': ProcessGroup(selection=['a']),
        'b': ProcessGroup(selection=['b']),
    }
    bundles = [
        Bundle('a', 'b'),
    ]
    ordering = [['a'], ['b']]
    sdd = SankeyDefinition(nodes, bundles, ordering)

    flows = pd.DataFrame.from_records(
        [('a', 'b', 'm', 3)],
        columns=('source', 'target', 'material', 'value'))

    result = weave(sdd, flows)


def test_weave_results():
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
    sdd = SankeyDefinition(nodes, bundles, ordering)

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
    dim_process = pd.DataFrame({
        'id': list(flows.source.unique()) + list(flows.target.unique())
    }).set_index('id')
    dataset = Dataset(flows, dim_process)

    result = weave(sdd, dataset)

    def link(src, tgt, original_flows, value, link_type='*', color='#FBB4AE'):
        return SankeyLink(source=src, target=tgt, type=link_type, time='*',
                          data={'value': value}, title=link_type, color=color,
                          original_flows=original_flows)

    assert set(n.id for n in result.nodes) == {'a^*', 'b^*', 'via^m', 'via^n', 'c^c1', 'c^c2'}

    assert sorted(result.links) == [
        link('a^*', 'via^m',  [0], 3),
        link('a^*', 'via^n',  [1], 1),
        link('b^*', 'via^m',  [2, 3], 3),
        link('b^*', 'via^n',  [4], 1),
        link('via^m', 'c^c1', [0, 2], 4),
        link('via^m', 'c^c2', [3], 2),
        link('via^n', 'c^c1', [1], 1),
        link('via^n', 'c^c2', [4], 1),
    ]

    assert result.ordering == Ordering([
        [['a^*', 'b^*']],
        [['via^m', 'via^n']],
        [['c^c1', 'c^c2']],
    ])

    assert result.groups == [
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
    sdd2 = SankeyDefinition(
        nodes,
        bundles,
        ordering,
        flow_partition=Partition.Simple('material', ['m', 'n']))

    scale = CategoricalScale('type', palette=['red', 'blue'])
    scale.set_domain(['m', 'n'])
    result = weave(sdd2, dataset, link_color=scale)

    assert sorted(result.links) == [
        link('a^*', 'via^m',  [0], 3, 'm', 'red'),
        link('a^*', 'via^n',  [1], 1, 'n', 'blue'),
        link('b^*', 'via^m',  [2, 3], 3, 'm', 'red'),
        link('b^*', 'via^n',  [4], 1, 'n', 'blue'),
        link('via^m', 'c^c1', [0, 2], 4, 'm', 'red'),
        link('via^m', 'c^c2', [3], 2, 'm', 'red'),
        link('via^n', 'c^c1', [1], 1, 'n', 'blue'),
        link('via^n', 'c^c2', [4], 1, 'n', 'blue'),
    ]


def test_weave_adds_implicit_Elsewhere_bundles_without_waypoints():
    # This was a bug, that the implicit Elsewhere bundles were not being added
    # to the *nodes* lists of from_elsewhere_bundles and to_elsewhere_bundles
    nodes = {
        'source': ProcessGroup(selection=['source']),
        'a': ProcessGroup(selection=['a']),
    }
    bundles = [
        Bundle('source', 'a'),
    ]
    ordering = [[['source']], [['a']]]
    sdd = SankeyDefinition(nodes, bundles, ordering)

    # Dataset
    flows = pd.DataFrame.from_records(
        [
            ('source', 'a', 'm', 3),
            ('source', 'b', 'm', 1),
        ],
        columns=('source', 'target', 'material', 'value'))

    # Part A -> with add_elsewhere_waypoints=True, the implicit elsewhere
    # bundle should be added to the main list of links

    result = weave(sdd, flows)

    assert result.links == [
        inst(SankeyLink, source='source^*', target='a^*', data={"value": 3},
             original_flows=[0]),
        inst(SankeyLink, source='source^*', target='__source>^*', data={"value": 1},
             original_flows=[1]),
    ]
    assert result.nodes == [
        inst(SankeyNode, id='source^*', to_elsewhere_links=[]),
        inst(SankeyNode, id='a^*', to_elsewhere_links=[]),
        inst(SankeyNode, id='__source>^*', to_elsewhere_links=[]),
    ]

    # Part B -> with add_elsewhere_waypoints=False, the implicit elsewhere
    # bundle should be added to the node

    result = weave(sdd, flows, add_elsewhere_waypoints=False)

    assert result.links == [
        inst(SankeyLink, source='source^*', target='a^*', data={"value": 3}, original_flows=[0])
    ]
    assert result.nodes == [
        inst(SankeyNode, id='source^*', to_elsewhere_links=[
            inst(SankeyLink, source='source^*', target=None, data={"value": 1}, original_flows=[1])
        ]),
        inst(SankeyNode, id='a^*', to_elsewhere_links=[]),
    ]

# def test_sankey_view_results_time_partition():
#     nodes = {
#         'a': ProcessGroup(selection=['a1']),
#         'b': ProcessGroup(selection=['b1']),
#     }
#     bundles = [Bundle('a', 'b')]
#     ordering = [[['a']], [['b']]]
#     time_partition = Partition.Simple('time', [1, 2])
#     sdd = SankeyDefinition(
#         nodes, bundles, ordering,
#         time_partition=time_partition)

#     # Dataset
#     flows = pd.DataFrame.from_records(
#         [
#             ('a1', 'b1', 'm', 1, 3),
#             ('a1', 'b1', 'm', 2, 2),
#         ],
#         columns=('source', 'target', 'material', 'time', 'value'))
#     dim_process = pd.DataFrame({'id': ['a1', 'b1']}).set_index('id')
#     dataset = Dataset(flows, dim_process)

#     GR, groups = sankey_view(sdd, dataset)
#     assert set(GR.nodes()) == {'a^*', 'b^*'}
#     assert sorted(GR.edges(keys=True, data=True)) == [
#         ('a^*', 'b^*', ('*', '1'), {'value': 3, 'measures': {},
#                                     'bundles': [0]}),
#         ('a^*', 'b^*', ('*', '2'), {'value': 2, 'measures': {},
#                                     'bundles': [0]}),
#     ]
#     assert GR.ordering == Ordering([[['a^*']], [['b^*']]])
