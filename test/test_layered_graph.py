from floweaver.layered_graph import LayeredGraph, Ordering


def test_remove_node():
    G = LayeredGraph()
    G.add_edges_from([('a', 'b'), ('a', 'c'), ('b', 'd')])
    G.ordering = Ordering([['a'], ['b', 'c'], ['d']])
    assert sorted(G.nodes()) == ['a', 'b', 'c', 'd']

    G.remove_node('c')
    assert sorted(G.nodes()) == ['a', 'b', 'd']
    assert G.ordering == Ordering([['a'], ['b'], ['d']])
