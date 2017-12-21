import networkx as nx
import pytest

from floweaver.hierarchy import Hierarchy


def test_hierarchy():
    tree = nx.DiGraph()
    tree.add_edges_from([
        ('*', 'London'),
        ('*', 'East Anglia'),
        ('East Anglia', 'Cambridge'),
        ('East Anglia', 'Ely'),
        ('East Anglia', 'Escape "'),
    ])

    h = Hierarchy(tree, 'location')

    assert h('Ely') == 'location == "Ely"'
    assert h('Cambridge') == 'location == "Cambridge"'
    assert h('East Anglia') == "location in ['Cambridge', 'Ely', 'Escape \"']"
    assert h('*') == None

    with pytest.raises(KeyError):
        h('unknown')
