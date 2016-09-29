from sankeyview.bundle import Bundle, Elsewhere
from sankeyview.view_definition import ProcessGroup


def test_bundle_elsewhere():
    assert Bundle('a', 'b').to_elsewhere == False
    assert Bundle('a', 'b').from_elsewhere == False

    assert Bundle(Elsewhere, 'b').to_elsewhere == False
    assert Bundle(Elsewhere, 'b').from_elsewhere == True

    assert Bundle('a', Elsewhere).to_elsewhere == True
    assert Bundle('a', Elsewhere).from_elsewhere == False


def test_bundle_hashable():
    assert hash(Bundle('a', 'b'))

# def test_bundle():
#     b = Bundle('a', 'b', waypoints=['c'])
#     assert b.get_segments() == [
#         BundleSegment('a', 'c', b),
#         BundleSegment('c', 'b', b),
#     ]


# def test_bundle_get_flows():
#     n1 = ProcessGroup(0, 0, query={'query': '1'})
#     n2 = ProcessGroup(1, 0, query={'query': '2'})
#     b = Bundle(n1, n2)

#     flows = ['x']
#     class MockDataset:
#         def find_flows(self, source_query, target_query, flow_query):
#             assert source_query == n1.query
#             assert target_query == n2.query
#             assert flow_query == None
#             return flows

#     b._get_flows(MockDataset())
#     assert b.flows is flows
