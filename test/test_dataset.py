import pytest

import pandas as pd

from floweaver.dataset import Dataset, eval_selection
from floweaver.sankey_definition import ProcessGroup, Bundle, Elsewhere


def _dataset():
    dim_process = pd.DataFrame.from_records(
        [
            ('a1', 'a'),
            ('a2', 'a'),
            ('b', 'b'),
            ('c', 'c'),
        ],
        columns=['id', 'function']).set_index('id')

    dim_material = pd.DataFrame.from_records([
        ('m1', 'type1'),
        ('m2', 'type2'),
    ], columns=['id', 'type']).set_index('id')

    dim_time = pd.DataFrame.from_records([
        ('t1', 'August'),
        ('t2', 'March'),
    ], columns=['id', 'month']).set_index('id')

    flows = pd.DataFrame.from_records(
        [
            ('a1', 'b', 'm1', 't1', 3),
            ('a2', 'b', 'm2', 't1', 4),
            ('b', 'c', 'm1', 't1', 3),
            ('b', 'c', 'm2', 't1', 4),
        ],
        columns=['source', 'target', 'material', 'time', 'value'])

    return Dataset(flows, dim_process, dim_material, dim_time)


def test_dataset_joins_tables():
    d = _dataset()
    assert len(d._table.index) == 4
    assert set(d._table.columns) == {'source', 'target', 'material', 'time', 'value',
                                     'source.function', 'target.function',
                                     'material.type', 'time.month'}


def test_dataset_checks_dim_tables_have_unique_index():
    dim_time = pd.DataFrame.from_records([
        ('same_id', 'August'),
        ('same_id', 'March'),
    ], columns=['id', 'month']).set_index('id')

    flows = pd.DataFrame.from_records(
        [
            ('a1', 'b', 'same_id', 3),
        ],
        columns=['source', 'target', 'time', 'value'])

    with pytest.raises(ValueError):
        Dataset(flows, dim_time=dim_time)


def test_selection_list():
    """ProcessGroup selection can be a list -> ids"""
    d = _dataset()
    assert list(eval_selection(d._flows, 'source', ['a1', 'a2'])) \
        == [True, True, False, False]
    assert list(eval_selection(d._flows, 'target', ['c'])) \
        == [False, False, True, True]


def test_selection_string():
    """ProcessGroup selection can be a string -> pandas eval"""
    d = _dataset()

    assert list(eval_selection(d._table, 'source', 'function == "a"')) \
        == [True, True, False, False]

    q = 'function == "a" and id in ["a1"]'
    assert list(eval_selection(d._table, 'source', q)) \
        == [True, False, False, False]


def test_dataset_only_includes_unused_flows_in_elsewhere_bundles():
    # Bundle 0 should include flow 0, bundle 1 should include flow 1
    nodes = {
        'a': ProcessGroup(selection=['a']),
        'x': ProcessGroup(selection=['x']),
    }
    bundles = {
        0: Bundle('a', 'x'),
        1: Bundle(Elsewhere, 'x'),
    }

    # Dataset
    flows = pd.DataFrame.from_records(
        [
            ('a', 'x', 'm', 1),
            ('b', 'x', 'm', 1),
        ],
        columns=('source', 'target', 'material', 'value'))
    dataset = Dataset(flows)

    bundle_flows, _ = dataset.apply_view(nodes, bundles)

    def get_source_target(b):
        return [(row['source'], row['target'])
                for i, row in bundle_flows[b].iterrows()]

    assert get_source_target(0) == [('a', 'x')]
    assert get_source_target(1) == [('b', 'x')]

    # Check it works with duplicated flow index values (old bug)
    flows.index = [0, 0]
    dataset = Dataset(flows)
    bundle_flows, _ = dataset.apply_view(nodes, bundles)
    assert get_source_target(0) == [('a', 'x')]
    assert get_source_target(1) == [('b', 'x')]


def test_unused_flows():
    """Unused flows are between *used* nodes
    """

    # view definition:
    # Elsewhere --> [a] --> Elsewhere
    # Elsewhere --> [b] --> Elsewhere
    #
    # dataset:
    # other --> a --> other
    # other --> b --> other
    # a --> b --> c
    #
    # The a --> b flow in the dataset is "unused"
    # The b --> c flow is not unused since c isn't visible
    #
    nodes = {
        'other': ProcessGroup(selection=['other']),
        'a': ProcessGroup(selection=['a']),
        'b': ProcessGroup(selection=['b']),
    }
    bundles = {
        0: Bundle(Elsewhere, 'a'),
        1: Bundle(Elsewhere, 'b'),
        2: Bundle('a', Elsewhere),
        3: Bundle('b', Elsewhere),
    }

    # Dataset
    flows = pd.DataFrame.from_records(
        [
            ('other', 'a', 'm', 1),
            ('other', 'b', 'm', 1),
            ('a', 'other', 'm', 1),
            ('b', 'other', 'm', 1),
            ('a', 'b', 'm', 1),
            ('b', 'c', 'm', 1),
        ],
        columns=('source', 'target', 'material', 'value'))
    dim_process = pd.DataFrame(
        {'id': ['a', 'b', 'c', 'other']}).set_index('id')
    dataset = Dataset(flows, dim_process)

    bundle_flows, unused = dataset.apply_view(nodes, bundles)

    def get_source_target(b):
        return [(row['source'], row['target'])
                for i, row in bundle_flows[b].iterrows()]

    assert get_source_target(0) == [('other', 'a')]
    assert get_source_target(1) == [('other', 'b'), ('a', 'b')]
    assert get_source_target(2) == [('a', 'other'), ('a', 'b')]
    assert get_source_target(3) == [('b', 'other'), ('b', 'c')]

    assert len(unused) == 1
    assert unused.iloc[0].equals(flows.iloc[4])


def test_internal_flows():
    nodes = {
        'a': ProcessGroup(selection=['a']),
        'bcd': ProcessGroup(selection=['b', 'c', 'd']),
        'e': ProcessGroup(selection=['e']),
    }
    bundles = {
        0: Bundle('a', 'bcd'),
        1: Bundle('bcd', 'e'),
        2: Bundle('bcd', 'bcd', flow_selection='source == "c"'),
    }
    ordering = [['a'], ['bcd'], ['e']]

    # Dataset
    flows = pd.DataFrame.from_records(
        [
            ('a', 'b', 'm', 4),
            ('b', 'c', 'm', 3),
            ('b', 'd', 'm', 1),
            ('c', 'b', 'm', 2),
            ('c', 'e', 'm', 1),
        ],
        columns=('source', 'target', 'material', 'value'))
    dataset = Dataset(flows)

    bundle_flows, unused = dataset.apply_view(nodes, bundles)

    def get_source_target(b):
        return [(row['source'], row['target'], row['value'])
                for i, row in bundle_flows[b].iterrows()]

    assert get_source_target(0) == [('a', 'b', 4)]
    assert get_source_target(1) == [('c', 'e', 1)]
    assert get_source_target(2) == [('c', 'b', 2)]

    assert len(unused) == 0


def test_internal_flows_elsewhere():
    """Internal flows should not be included in to/from Elsewhere bundles.

    """

    # view definition:
    # Elsewhere --> [a,b] --> Elsewhere
    #
    # dataset:
    # other --> a --> b --> other
    #
    nodes = {
        'other': ProcessGroup(selection=['other']),
        'ab': ProcessGroup(selection=['a', 'b']),
    }
    bundles = {
        0: Bundle(Elsewhere, 'ab'),
        1: Bundle('ab', Elsewhere),
    }

    # Dataset
    flows = pd.DataFrame.from_records(
        [
            ('other', 'a', 'm', 1),
            ('a', 'b', 'm', 1),
            ('b', 'other', 'm', 1),
        ],
        columns=('source', 'target', 'material', 'value'))
    dim_process = pd.DataFrame({'id': ['a', 'b', 'other']}).set_index('id')
    dataset = Dataset(flows, dim_process)

    bundle_flows, unused = dataset.apply_view(nodes, bundles)

    def get_source_target(b):
        return [(row['source'], row['target'])
                for i, row in bundle_flows[b].iterrows()]

    assert get_source_target(0) == [('other', 'a')]
    assert get_source_target(1) == [('b', 'other')]

    assert len(unused) == 0
