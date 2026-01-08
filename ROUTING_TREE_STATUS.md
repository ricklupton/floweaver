# Routing Tree Implementation Status

## Overview

This branch implements a new efficient routing tree structure for floweaver, transforming from a pull-based O(rows × edges) model to a push-based O(rows × tree_depth) model.

## What's Been Implemented

### Core Data Structures (`src/floweaver/router.py`)
- ✅ `TreeNode`: Decision tree nodes with branches and leaf states (Assigned/Unclaimed/Blocked)
- ✅ `RoutingTree`: Complete routing structure with bundle tree and edge mapping
- ✅ `route_row()`: Routes a single row through the tree to find matching edges
- ✅ `route_flows()`: Routes all flows and returns edge-to-rows mapping

### Compilation (`src/floweaver/compile.py`)
- ✅ **Step 1**: Expand ProcessGroups to explicit process ID sets
- ✅ **Step 2**: Collect explicit branch point values
- ✅ **Step 3**: Build bundle tree with two-pass algorithm (non-Elsewhere, then Elsewhere)
- ✅ **Step 4**: Generate edges and map bundles to edges
- ⚠️ **Partial**: Basic edge generation (waypoints not fully handled)
- ⚠️ **Partial**: Basic partition tree generation (needs refinement)

### Execution (`src/floweaver/execute.py`)
- ✅ Updated `execute_weave()` to use routing tree when available
- ✅ Backward compatibility with old filter-based specs
- ✅ Proper flow routing and aggregation

### Spec Updates (`src/floweaver/spec.py`)
- ✅ Added `id` field to `EdgeSpec`
- ✅ Added `routing_tree` field to `WeaverSpec`
- ✅ Updated JSON serialization

## Test Results

**Equivalence Tests**: 7 of 16 passing (43.75%)

### Passing Tests ✅
- `TestBasicEquivalence::test_simple_two_nodes`
- `TestBasicEquivalence::test_accepts_dataframe`
- `TestElsewhereEquivalence::test_implicit_elsewhere_bundles`
- `TestMeasureEquivalence::test_default_measure`
- `TestMeasureEquivalence::test_multiple_measures`
- `TestOrderingEquivalence::test_ordering_with_bands`
- `TestLinkWidthEquivalence::test_link_width_matches_value`

### Failing Tests (Need Waypoint/Partition Work) ❌
- All `TestPartitionEquivalence` tests (waypoint partitions not expanded)
- `TestFlowPartitionEquivalence` (flow partition handling incomplete)
- `TestColorScaleEquivalence` (depends on correct partitioning)
- `TestGroupEquivalence` (depends on correct partitioning)
- `TestDirectionEquivalence` (minor issue)
- `TestOriginalFlowsEquivalence` (minor issue)
- `TestComplexRealWorldEquivalence` (depends on waypoints/partitions)

## What Remains

### High Priority
1. **Proper Waypoint Expansion**: The `_generate_edges_for_bundle()` function needs to traverse the view graph properly to expand waypoints into intermediate nodes. Currently it only generates direct source→target edges.

2. **Partition Tree Building**: The `_build_partition_tree_for_bundle()` function needs proper implementation for:
   - Flow partitions (material, etc.)
   - Process partitions
   - Multiple partition dimensions
   - Catch-all groups

3. **Flow Partition Handling**: Flow partitions need to be properly integrated into the routing tree.

### Medium Priority
4. **Edge Generation Details**: Handle sequential edges, time partitions, and other edge attributes properly.

5. **Test Updates**: Update `test/test_compile.py` to match new compiled spec structure.

### Lower Priority
6. **Optimization**: The tree building could be optimized further.

7. **Documentation**: Add comprehensive documentation for the new system.

## Example Usage

```python
from floweaver import SankeyDefinition, ProcessGroup, Bundle, compile
from floweaver.execute import execute_weave

# Define diagram
nodes = {
    'a': ProcessGroup(selection=['a1', 'a2']),
    'b': ProcessGroup(selection=['b1']),
}
bundles = [Bundle('a', 'b')]
ordering = [['a'], ['b']]
sdd = SankeyDefinition(nodes, bundles, ordering)

# Compile (generates routing tree)
spec = compile(sdd)

# Execute against data
result = execute_weave(spec, dataset)
```

## Key Design Decisions

1. **Two-Pass Bundle Insertion**: Non-Elsewhere bundles are inserted first, then Elsewhere bundles. This ensures proper priority and prevents internal flow leakage.

2. **Pre-Populated Branches**: All branch points are pre-populated during tree construction based on explicit values collected from all bundles. This ensures consistent tree structure.

3. **Source Rechecks**: Elsewhere bundles use source/target rechecks to block internal flows (e.g., when source=Elsewhere target=T, block flows where source is also in T).

4. **Immutable Tree Nodes**: Tree nodes use attrs without frozen=True, allowing in-place modification during construction while still being serializable.

5. **Bundle-to-Edges Mapping**: The routing tree maps bundle IDs to lists of edge IDs, supporting both simple (1 bundle → 1 edge) and complex (1 bundle → many edges) scenarios.

## Files Changed

- `src/floweaver/router.py` (new)
- `src/floweaver/compile.py` (rewritten)
- `src/floweaver/spec.py` (updated)
- `src/floweaver/execute.py` (updated)
- `src/floweaver/compile_old.py` (backup of original)

## Next Steps

The highest priority is completing waypoint expansion in `_generate_edges_for_bundle()`. This requires:
1. Understanding the view graph structure
2. Traversing waypoints to create intermediate edges
3. Handling partition expansion at waypoints
4. Building appropriate partition trees for each bundle

Once waypoint handling is complete, most remaining tests should pass.
