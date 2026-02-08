"""Debug partition tree routing attributes."""
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

# Check partition tree for bundle 0
import json
rt = spec.routing_tree

# Find a partition tree in the bundle tree
def find_partition_trees(node, path=""):
    if isinstance(node, dict):
        if 'partition_tree' in node and node['partition_tree']:
            print(f"\nPartition tree at {path}:")
            print(json.dumps(node['partition_tree'], indent=2))
        if 'branches' in node:
            for key, child in node['branches'].items():
                find_partition_trees(child, f"{path}.branches[{key}]")

find_partition_trees(rt['bundle_tree'], "bundle_tree")
