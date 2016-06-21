
import pandas as pd

from sankeyview.dataset import Dataset, eval_selection

from sankeyview.node import Node
from sankeyview.bundle import Bundle, Elsewhere
from sankeyview.view_definition import ViewDefinition


def _dataset():
    processes = pd.DataFrame.from_records([
        ('a1', 'a'),
        ('a2', 'a'),
        ('b', 'b'),
        ('c', 'c'),
    ], columns=['id', 'function']).set_index('id')

    flows = pd.DataFrame.from_records([
        ('a1', 'b', 'm1', 3),
        ('a2', 'b', 'm2', 4),
        ('b', 'c', 'm1', 3),
        ('b', 'c', 'm2', 4),
    ], columns=['source', 'target', 'material', 'value'])

    return Dataset(processes, flows)


def test_selection_list():
    """Node selection can be a list -> ids"""
    d = _dataset()
    assert list(eval_selection(d._flows, 'source', ['a1', 'a2'])) == [True, True, False, False]
    assert list(eval_selection(d._flows, 'target', ['c'])) == [False, False, True, True]


def test_selection_string():
    """Node selection can be a string -> pandas eval"""
    d = _dataset()

    assert list(eval_selection(d._table, 'source', 'function == "a"')) == [True, True, False, False]

    q = 'function == "a" and id in ["a1"]'
    assert list(eval_selection(d._table, 'source', q)) == [True, False, False, False]


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
        'other': Node(selection=['other']),
        'a': Node(selection=['a']),
        'b': Node(selection=['b']),
    }
    bundles = {
        0: Bundle(Elsewhere, 'a'),
        1: Bundle(Elsewhere, 'b'),
        2: Bundle('a', Elsewhere),
        3: Bundle('b', Elsewhere),
    }

    # Dataset
    flows = pd.DataFrame.from_records([
        ('other', 'a', 'm', 1),
        ('other', 'b', 'm', 1),
        ('a', 'other', 'm', 1),
        ('b', 'other', 'm', 1),
        ('a', 'b', 'm', 1),
        ('b', 'c', 'm', 1),
    ], columns=('source', 'target', 'material', 'value'))
    processes = pd.DataFrame({'id': ['a', 'b', 'c', 'other']}).set_index('id')
    dataset = Dataset(processes, flows)

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
    """Internal flows should not be included in to/from Elsewhere bundles.

    """

    # view definition:
    # Elsewhere --> [a,b] --> Elsewhere
    #
    # dataset:
    # other --> a --> b --> other
    #
    nodes = {
        'other': Node(selection=['other']),
        'ab': Node(selection=['a', 'b']),
    }
    bundles = {
        0: Bundle(Elsewhere, 'ab'),
        1: Bundle('ab', Elsewhere),
    }

    # Dataset
    flows = pd.DataFrame.from_records([
        ('other', 'a',     'm', 1),
        ('a',     'b',     'm', 1),
        ('b',     'other', 'm', 1),
    ], columns=('source', 'target', 'material', 'value'))
    processes = pd.DataFrame({'id': ['a', 'b', 'other']}).set_index('id')
    dataset = Dataset(processes, flows)

    bundle_flows, unused = dataset.apply_view(nodes, bundles)

    def get_source_target(b):
        return [(row['source'], row['target'])
                for i, row in bundle_flows[b].iterrows()]

    assert get_source_target(0) == [('other', 'a')]
    assert get_source_target(1) == [('b', 'other')]

    assert len(unused) == 0
