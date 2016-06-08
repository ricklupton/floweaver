import pytest

import pandas as pd

from sankeyview.view_definition import ViewDefinition
from sankeyview.sankey_view import sankey_view
from sankeyview.node import Node
from sankeyview.bundle import Bundle
from sankeyview.grouping import Grouping
from sankeyview.dataset import Dataset


def test_sankey_view_unused_flows():
    """Unused flows are between *used* nodes
    """
    nodes = {
        'a': Node(selection=['a']),
        'b': Node(selection=['b']),
        'c': Node(selection=['c']),
    }
    bundles = [
        Bundle('a', 'b'),
        Bundle('b', 'c'),
    ]
    order = [
        [['a']], [['b']], [['c']]
    ]
    vd = ViewDefinition(nodes, bundles, order)

    # Dataset
    flows = pd.DataFrame.from_records([
        ('a', 'b', 'm', 3),
        ('b', 'c', 'm', 3),
        ('a', 'c', 'm', 1),  # UNUSED
    ], columns=('source', 'target', 'material', 'value'))
    processes = pd.DataFrame({'id': ['a', 'b', 'c']}).set_index('id')
    dataset = Dataset(processes, flows)

    GR, oR, groups, unused_flows = sankey_view(vd, dataset, return_unused_flows=True)

    assert len(unused_flows) == 1
    assert unused_flows.iloc[0].equals(flows.iloc[2])

    assert set(GR.nodes()) == {'a^*', 'b^*', 'c^*', 'from a^*', 'to c^*'}
    assert sorted(GR.edges(keys=True, data=True)) == [
        ('a^*', 'b^*', '*', {'value': 3}),
        ('a^*', 'from a^*', '*', {'value': 1}),
        ('b^*', 'c^*', '*', {'value': 3}),
        ('to c^*', 'c^*', '*', {'value': 1}),
    ]


def test_sankey_view_results():
    nodes = {
        'a': Node(selection=['a1', 'a2']),
        'b': Node(selection=['b1']),
        'c': Node(selection=['c1', 'c2'], grouping=Grouping.Simple('node', ['c1', 'c2'])),
        'via': Node(grouping=Grouping.Simple('material', ['m', 'n'])),
    }
    bundles = [
        Bundle('a', 'c', waypoints=['via']),
        Bundle('b', 'c', waypoints=['via']),
    ]
    order = [
        [['a', 'b']], [['via']], [['c']]
    ]
    vd = ViewDefinition(nodes, bundles, order)

    # Dataset
    flows = pd.DataFrame.from_records([
        ('a1', 'c1', 'm', 3),
        ('a2', 'c1', 'n', 1),
        ('b1', 'c1', 'm', 1),
        ('b1', 'c2', 'm', 2),
        ('b1', 'c2', 'n', 1),
    ], columns=('source', 'target', 'material', 'value'))
    processes = pd.DataFrame({
        'id': list(flows.source.unique()) + list(flows.target.unique())}).set_index('id')
    dataset = Dataset(processes, flows)

    GR, oR, groups = sankey_view(vd, dataset)

    assert set(GR.nodes()) == {'a^*', 'b^*', 'via^m', 'via^n', 'c^c1', 'c^c2'}
    assert sorted(GR.edges(keys=True, data=True)) == [
        ('a^*', 'via^m', '*', { 'value': 3 }),
        ('a^*', 'via^n', '*', { 'value': 1 }),
        ('b^*', 'via^m', '*', { 'value': 3 }),
        ('b^*', 'via^n', '*', { 'value': 1 }),
        ('via^m', 'c^c1', '*', { 'value': 4 }),
        ('via^m', 'c^c2', '*', { 'value': 2 }),
        ('via^n', 'c^c1', '*', { 'value': 1 }),
        ('via^n', 'c^c2', '*', { 'value': 1 }),
    ]

    assert oR == [
        [ ['a^*', 'b^*'] ],
        [ ['via^m', 'via^n'] ],
        [ ['c^c1', 'c^c2'] ],
    ]
    assert groups == [
        {'id': 'a', 'title': '', 'processes': ['a^*']},
        {'id': 'b', 'title': '', 'processes': ['b^*']},
        {'id': 'via', 'title': '', 'processes': ['via^m', 'via^n']},
        {'id': 'c', 'title': '', 'processes': ['c^c1', 'c^c2']},
    ]

    # Can also set flow_grouping for all bundles at once
    vd2 = ViewDefinition(nodes, bundles, order,
                         flow_grouping=Grouping.Simple('material', ['m', 'n']))
    GR, oR, groups = sankey_view(vd2, dataset)
    assert sorted(GR.edges(keys=True, data=True)) == [
        ('a^*', 'via^m', 'm', { 'value': 3 }),
        ('a^*', 'via^n', 'n', { 'value': 1 }),
        ('b^*', 'via^m', 'm', { 'value': 3 }),
        ('b^*', 'via^n', 'n', { 'value': 1 }),
        ('via^m', 'c^c1', 'm', { 'value': 4 }),
        ('via^m', 'c^c2', 'm', { 'value': 2 }),
        ('via^n', 'c^c1', 'n', { 'value': 1 }),
        ('via^n', 'c^c2', 'n', { 'value': 1 }),
    ]


# @pytest.mark.xfail
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


# @pytest.mark.xfail
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


# def edges_ignoring_elsewhere(v, data=False):
#     if data:
#         return [(a, b, data) for a, b, data in v.high_level.edges(data=True)
#                 if not (a.startswith('from') or b.startswith('from') or
#                         a.startswith('to') or b.startswith('to'))]
#     else:
#         return [(a, b) for a, b in v.high_level.edges(data=False)
#                 if not (a.startswith('from') or b.startswith('from') or
#                         a.startswith('to') or b.startswith('to'))]


# def nodes_ignoring_elsewhere(v):
#     return [u for u in v.high_level.nodes(data=False)
#             if not (u.startswith('from') or u.startswith('to'))]
