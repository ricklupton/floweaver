import pytest

from floweaver.diagram_optimisation import optimise_node_positions
from floweaver.sankey_data import SankeyData, SankeyNode, SankeyLink, SankeyLayout


def test_node_positions_straight():
    data = SankeyData(nodes=[SankeyNode(id='a'), SankeyNode(id='b')],
                      links=[SankeyLink(source='a', target='b', link_width=3)],
                      ordering=[['a'], ['b']])
    layout = optimise_node_positions(data, margins=dict(left=10, top=20, right=10, bottom=20), scale=1)

    # Width not specified -- assumes a suitable gap between layers
    assumed_gap = 150
    assert layout.node_positions == {
        "a": [10, 20],
        "b": [10 + 150, 20],
    }


TEST_DATA_SIMPLE_MERGE = SankeyData(
    nodes=[SankeyNode(id='a1'), SankeyNode(id='a2'), SankeyNode(id='b')],
    links=[
        SankeyLink(source='a1', target='b', link_width=3),
        SankeyLink(source='a2', target='b', link_width=3),
    ],
    ordering=[['a1', 'a2'], ['b']]
)


def test_node_positions_no_overlap():
    # Check y positions do not overlap
    dy_a1 = 3
    minimum_gap = 10
    margins = dict(left=10, top=20, right=10, bottom=20)
    layout = optimise_node_positions(TEST_DATA_SIMPLE_MERGE, margins=margins, scale=1, minimum_gap=minimum_gap)
    assert layout.node_positions['a1'][1] == 20
    assert layout.node_positions['a2'][1] >= 20 + dy_a1 + minimum_gap


@pytest.mark.xfail(reason='need to account for scale when calculating node positions')
def test_node_positions_no_overlap_with_ccale():
    # Check y positions do not overlap
    scale = 2
    dy_a1 = 3 * scale
    minimum_gap = 10
    margins = dict(left=10, top=20, right=10, bottom=20)
    layout = optimise_node_positions(TEST_DATA_SIMPLE_MERGE, margins=margins, scale=scale, minimum_gap=minimum_gap)
    assert layout.node_positions['a1'][1] == 20
    assert layout.node_positions['a2'][1] >= 20 + dy_a1 + minimum_gap


@pytest.mark.xfail(reason='need to account for offset between node position and link position')
def test_node_positions_target_in_between_sources():
    layout = optimise_node_positions(TEST_DATA_SIMPLE_MERGE, scale=1)
    y = lambda k: layout.node_positions[k][1]
    assert y('b') > y('a1')
    assert y('b') + 6 <= y('a2') + 3


# This test case has a first "start" node going to the top node in the second
# layer "a1" in order to offset the lower node "a2" away from the top of the
# diagram. "a2" is connected to two nodes in the following layer, "b1" and "b2".
# We want "b2" to be aligned so that its link (the lower of the two leaving
# "a2") is straight. If the offsets between node positions and link positions
# are not accounted for properly this will fail.
TEST_DATA_OFFSETS = SankeyData(
    nodes=[
        SankeyNode(id='start'),
        SankeyNode(id='a1'),
        SankeyNode(id='a2'),
        SankeyNode(id='b1'),
        SankeyNode(id='b2'),
    ],
    links=[
        SankeyLink(source='start', target='a1', link_width=30),
        SankeyLink(source='a1', target='b1', link_width=3),
        SankeyLink(source='a2', target='b1', link_width=30),
        SankeyLink(source='a2', target='b2', link_width=30),
    ],
    ordering=[['start'], ['a1', 'a2'], ['b1', 'b2']]
)


@pytest.mark.xfail(reason='need to account for offset between node position and link position')
def test_node_positions_aligns_links_straight():
    layout = optimise_node_positions(TEST_DATA_OFFSETS, scale=1)
    y = lambda k: layout.node_positions[k][1]
    dy_link_b2_a1 = 30
    assert y('b2') == y('a2') + dy_link_b2_a1
