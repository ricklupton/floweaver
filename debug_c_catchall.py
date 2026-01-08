"""Debug c^_ node creation."""
import pandas as pd
from floweaver import (
    SankeyDefinition,
    ProcessGroup,
    Waypoint,
    Bundle,
    Partition,
    Dataset,
)
from floweaver.weave import weave_compiled

nodes = {
    'a': ProcessGroup(selection=['a1', 'a2']),
    'b': ProcessGroup(selection=['b1']),
    'c': ProcessGroup(selection=['c1', 'c2'],
                      partition=Partition.Simple('process', ['c1', 'c2'])),
    'via': Waypoint(partition=Partition.Simple('material', ['m', 'n'])),
}
bundles = [
    Bundle('a', 'c', waypoints=['via']),
    Bundle('b', 'c', waypoints=['via']),
]
ordering = [[['a', 'b']], [['via']], [['c']]]
sdd = SankeyDefinition(
    nodes, bundles, ordering,
    flow_partition=Partition.Simple('material', ['m', 'n']))

flows = pd.DataFrame.from_records(
    [
        ('a1', 'c1', 'm', 3),
        ('a2', 'c1', 'n', 1),
        ('b1', 'c1', 'm', 1),
        ('b1', 'c2', 'm', 2),
        ('b1', 'c2', 'n', 1),
    ],
    columns=('source', 'target', 'material', 'value'))
dim_process = pd.DataFrame({
    'id': list(flows.source.unique()) + list(flows.target.unique())
}).set_index('id')
dataset = Dataset(flows, dim_process)

result = weave_compiled(sdd, dataset)

print("\n=== NODES ===")
for node in result.nodes:
    print(f"{node.id}: hidden={node.hidden}")

print("\n=== LINKS involving c^_ ===")
c_catchall_links = [link for link in result.links if 'c^_' in (link.source, link.target)]
for link in c_catchall_links:
    print(f"{link.source} -> {link.target}: value={link.link_width}, flows={link.original_flows}")

print(f"\nTotal links involving c^_: {len(c_catchall_links)}")
