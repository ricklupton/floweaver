"""Debug script for flow partition compatibility."""
import pandas as pd
from floweaver import (
    SankeyDefinition,
    ProcessGroup,
    Waypoint,
    Bundle,
    Partition,
    Dataset,
    compile,
)

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

# Compile
spec = compile(sdd)

print("\n=== EDGES (first 20) ===")
for i, edge in enumerate(spec.edges[:20]):
    print(f"{edge.id}: {edge.source} -> {edge.target} (type={edge.type}, bundles={edge.bundles})")

print(f"\nTotal edges: {len(spec.edges)}")

# Check how many edges involve via
via_edges = [e for e in spec.edges if 'via' in (e.source or '') or 'via' in (e.target or '')]
print(f"Edges involving via: {len(via_edges)}")
for e in via_edges[:10]:
    print(f"  {e.id}: {e.source} -> {e.target} (type={e.type})")
