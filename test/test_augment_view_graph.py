from floweaver.layered_graph import LayeredGraph
from floweaver.augment_view_graph import augment, elsewhere_bundles
from floweaver.sankey_definition import SankeyDefinition, Ordering, ProcessGroup, Waypoint, Bundle, Elsewhere
from floweaver.view_graph import view_graph


def test_elsewhere_bundles_are_added_when_no_bundles_defined():
    # make it easier to get started
    nodes = {'a': ProcessGroup(selection=['a1'])}
    bundles = {}
    order = [['a']]
    vd = SankeyDefinition(nodes, bundles, order)
    new_waypoints, new_bundles = elsewhere_bundles(vd)
    assert len(new_bundles) == 2
    assert new_waypoints == {
        '__>a': Waypoint(title='→'),
        '__a>': Waypoint(title='→'),
    }

    # when direction is to left
    nodes['a'] = ProcessGroup(selection=['a1'], direction='L')
    vd = SankeyDefinition(nodes, bundles, order)
    new_waypoints, new_bundles = elsewhere_bundles(vd)
    assert new_waypoints == {
        '__>a': Waypoint(direction='L', title='←'),
        '__a>': Waypoint(direction='L', title='←'),
    }



def test_elsewhere_bundles_not_added_at_minmax_rank_when_one_bundle_defined():
    nodes = {'a': ProcessGroup(selection=['a1'])}
    bundles = {0: Bundle('a', Elsewhere)}
    order = [['a']]
    vd = SankeyDefinition(nodes, bundles, order)
    new_waypoints, new_bundles = elsewhere_bundles(vd)
    assert len(new_waypoints) == 0
    assert len(new_bundles) == 0


def test_elsewhere_bundles_not_added_to_waypoints():
    nodes = {'waypoint': Waypoint(), }
    bundles = {}
    order = [[], ['waypoint'], []]
    vd = SankeyDefinition(nodes, bundles, order)
    new_waypoints, new_bundles = elsewhere_bundles(vd)
    assert new_waypoints == {}
    assert new_bundles == {}


def test_elsewhere_bundles():
    nodes = {'a': ProcessGroup(selection=['a1']), }
    bundles = {}
    order = [[], ['a'], []]  # not at min/max rank
    vd = SankeyDefinition(nodes, bundles, order)
    new_waypoints, new_bundles = elsewhere_bundles(vd)
    assert set(new_waypoints.keys()) == {'__a>', '__>a'}
    assert set(new_bundles.values()) == {
        Bundle('a', Elsewhere, waypoints=['__a>']),
        Bundle(Elsewhere, 'a', waypoints=['__>a']),
    }


def test_elsewhere_bundles_does_not_duplicate():
    nodes = {
        'a': ProcessGroup(selection=('a1')),
        'in': Waypoint(),
        'out': Waypoint()
    }
    bundles = {
        0: Bundle(Elsewhere, 'a', waypoints=['in']),
        1: Bundle('a', Elsewhere, waypoints=['out']),
    }
    order = [['in'], ['a'], ['out']]  # not at min/max rank
    vd = SankeyDefinition(nodes, bundles, order)
    new_waypoints, new_bundles = elsewhere_bundles(vd)
    assert new_bundles == {}


def test_augment_waypoint_alignment():
    # j -- a -- x
    #      b
    # k -- c -- y
    #
    # should insert "from b" betwen x and y
    # and "to b" between j and k
    G = LayeredGraph()
    G.add_nodes_from([
        ('a', {'node': ProcessGroup()}),
        ('b', {'node': ProcessGroup(selection=['b1'])}),
        ('c', {'node': ProcessGroup()}),
        ('x', {'node': ProcessGroup()}),
        ('y', {'node': ProcessGroup()}),
        ('j', {'node': ProcessGroup()}),
        ('k', {'node': ProcessGroup()}),
    ])
    G.add_edges_from([
        ('a', 'x', {'bundles': [2]}),
        ('k', 'c', {'bundles': [1]}),
        ('j', 'a', {'bundles': [0]}),
        ('c', 'y', {'bundles': [3]}),
    ])
    G.ordering = Ordering([[['j', 'k']], [['a', 'b', 'c']], [['x', 'y']]])

    new_waypoints = {
        'from b': Waypoint(),
        'to b': Waypoint(),
    }
    new_bundles = {
        'b>': Bundle('b', Elsewhere, waypoints=['from b']),
        '>b': Bundle(Elsewhere, 'b', waypoints=['to b']),
    }

    G2 = augment(G, new_waypoints, new_bundles)

    assert set(G2.nodes()).difference(G.nodes()) == {'from b', 'to b'}
    assert G2.ordering == Ordering([
        [['j', 'to b', 'k']], [['a', 'b', 'c']], [['x', 'from b', 'y']]
    ])
