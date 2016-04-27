
import pandas as pd

from sankeyview.dataset import Dataset, eval_selection


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
