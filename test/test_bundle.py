from sankeyview.bundle import Bundle, BundleSegment
from sankeyview.node import Node


def test_bundle():
    b = Bundle('a', 'b', waypoints=['c'])
    assert b.get_segments() == [
        BundleSegment('a', 'c', b),
        BundleSegment('c', 'b', b),
    ]


def test_bundle_get_flows():
    n1 = Node(0, 0, query={'query': '1'})
    n2 = Node(1, 0, query={'query': '2'})
    b = Bundle(n1, n2)

    flows = ['x']
    class MockDataset:
        def find_flows(self, source_query, target_query, flow_query):
            assert source_query == n1.query
            assert target_query == n2.query
            assert flow_query == None
            return flows

    b._get_flows(MockDataset())
    assert b.flows is flows
