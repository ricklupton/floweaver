"""Property-based testing strategies for floweaver

Generators aim to create realistic scenarios including:
- Flows that don't match any bundles
- Bundles with no matching flows
- Process IDs in flows but not in process groups
- Random mix of partitions and waypoints
- Edge cases that might break implementations
"""

import pandas as pd
from hypothesis import strategies as st, assume, event, note

from floweaver import (
    SankeyDefinition,
    ProcessGroup,
    Waypoint,
    Bundle,
    Partition,
    Dataset,
    Elsewhere,
)


PROCESS_IDS = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l"]


@st.composite
def process_id(draw):
    """Generate a process ID, either used or unused."""

    process_id_info: dict = draw(st.shared(st.builds(dict), key="process_ids"))
    process_id_info.setdefault("count", 0)
    existing_id = st.integers(min_value=1, max_value=process_id_info["count"]).map(
        lambda i: f"p{i:02d}"
    )

    random_id = st.integers(min_value=1).map(lambda i: f"q{i:02d}")
    return draw(existing_id | random_id)

    # prefix = draw(st.sampled_from([]))
    # # num = draw(st.integers(min_value=1, max_value=10))
    # return prefix #f"{prefix}{num}"


@st.composite
def unique_process_id(draw):
    """Generate unique process ids for ProcessGroup definitions."""
    # Make sure all process groups use unique process ids
    process_id_info: dict = draw(st.shared(st.builds(dict), key="process_ids"))
    process_id_info.setdefault("count", 0)
    process_id_info["count"] += 1
    return f"p{process_id_info['count']:02d}"

    # id_strategy = st.text(
    #     st.characters(min_codepoint=ord("a"), max_codepoint=ord("z")),
    #     min_size=1
    # ).filter(_filter) #.filter(lambda k: k not in used_process_ids)
    # # while (k := draw(process_id())) in used_process_ids:
    # #     pass
    # k = draw(id_strategy)
    # used_process_ids.append(k)
    # return k


def material_id():
    """Generate a material ID."""
    return st.sampled_from(["m", "n"])


def dimension_name():
    """Generate a random dimension name for partitions.

    Instead of hardcoding 'process' or 'material', randomize to test
    different partition dimensions.
    """
    return st.sampled_from(
        [
            "material",  # Most common
            "process",  # Also common
            "type",  # Could be material type, process type, etc.
            "sector",  # Economic sector
            "location",  # Geographic location
            "category",  # Generic category
        ]
    )


# @st.composite
# def flow_table(draw, num_processes=None, num_materials=None):
#     """Generate a flow table - may or may not match the SankeyDefinition.

#     This is intentionally messy - flows may reference processes not in the definition,
#     or not match bundles, etc.

#     Now includes additional dimension columns (type, sector, category) to enable
#     partitioning by different dimensions.
#     """
#     num_flows = draw(st.integers(min_value=0, max_value=20))

#     if num_flows == 0:
#         # Return empty DataFrame with extra columns
#         return pd.DataFrame(columns=['source', 'target', 'material', 'type', 'sector', 'category', 'value'])

#     # Generate some process IDs (may or may not match the definition)
#     # if num_processes is None:
#     #     num_processes = draw(st.integers(min_value=1, max_value=12))
#     # processes = [draw(process_id()) for _ in range(num_processes)]
#     # processes = list(set(processes))  # Remove duplicates
#     processes = sorted(draw(st.lists(process_id(), unique=True, min_size=1, max_size=20 if num_processes is None else num_processes)))
#     materials = sorted(draw(st.lists(material_id(), unique=True, min_size=1, max_size=6 if num_materials is None else num_materials)))

#     # if num_materials is None:
#     #     num_materials = draw(st.integers(min_value=1, max_value=6))
#     # materials = [draw(material_id()) for _ in range(num_materials)]
#     # materials = list(set(materials))

#     # Generate dimension value sets
#     types = draw(st.lists(st.sampled_from(['typeA', 'typeB', 'typeC']), min_size=1, max_size=3, unique=True))
#     sectors = draw(st.lists(st.sampled_from(['gov', 'industry', 'domestic']), min_size=1, max_size=3, unique=True))
#     categories = draw(st.lists(st.sampled_from(['cat1', 'cat2', 'cat3']), min_size=1, max_size=3, unique=True))

#     flows = []
#     for _ in range(num_flows):
#         source = draw(st.sampled_from(processes))
#         # Allow self-loops sometimes
#         target = draw(st.sampled_from(processes))
#         material = draw(st.sampled_from(materials))
#         flow_type = draw(st.sampled_from(types))
#         sector = draw(st.sampled_from(sectors))
#         category = draw(st.sampled_from(categories))
#         value = draw(st.floats(min_value=0.01, max_value=100.0, allow_nan=False, allow_infinity=False))
#         flows.append((source, target, material, flow_type, sector, category, value))


#     return pd.DataFrame.from_records(flows, columns=('source', 'target', 'material', 'type', 'sector', 'category', 'value'))
def flow_table(process_ids: list[str] | None = None):
    """Generate a flow table - may or may not match the SankeyDefinition."""
    if process_ids is not None and len(process_ids) > 0:
        process_id_strategy = st.sampled_from(process_ids)
    else:
        process_id_strategy = process_id()

    row_strategy = st.tuples(
        process_id_strategy,
        process_id_strategy,
        material_id(),
        st.sampled_from(["cat1", "cat2", "cat3"]),
        st.just(1.0),  # We're not checking numerical calculations
        # st.floats(min_value=0, max_value=10, allow_nan=False, allow_infinity=False),
    )

    return st.builds(
        pd.DataFrame.from_records,
        st.lists(row_strategy, min_size=1, max_size=20),
        columns=st.just(("source", "target", "material", "category", "value")),
    )


def partition_strategy(include_process=False):
    """Generate a Partition."""
    return st.one_of(
        st.builds(
            Partition.Simple,
            st.sampled_from(
                ["source", "target"] + (["process"] if include_process else [])
            ),
            st.lists(process_id(), unique=True, max_size=4),
        ),
        st.builds(
            Partition.Simple, st.just("material"), st.lists(material_id(), unique=True)
        ),
        st.builds(
            Partition.Simple,
            st.just("category"),
            st.lists(st.sampled_from(["cat1", "cat2", "cat3", "cat4"]), unique=True),
        ),
    )


def process_groups():
    """Generate a ProcessGroup definition.

    May or may not have a partition.
    Selection may be empty, single, or multiple processes.
    Partitions now use randomized dimension names instead of hardcoded 'process'.
    """

    return st.builds(
        ProcessGroup,
        selection=st.lists(unique_process_id(), min_size=1, max_size=4),
        partition=st.none() | partition_strategy(include_process=True),
    )
    # # Select some processes (may be just one, may be many, may be all)
    # selection = draw(st.lists(
    #     st.sampled_from(available_processes),
    #     min_size=1,
    #     max_size=len(available_processes),
    #     unique=True
    # ))

    # # Maybe add a partition (50% chance if more than one process)
    # partition = None
    # if len(selection) > 1 and draw(st.booleans()):
    #     # Choose a random dimension to partition by
    #     partition_dim = draw(dimension_name())
    #     partition_values = dimension_values_map.get(partition_dim, [])
    #     # Only partition if we have values
    #     if partition_values:
    #         partition = Partition.Simple(partition_dim, partition_values)
    # return ProcessGroup(selection=selection, partition=partition)


def waypoint_def():
    """Generate a Waypoint definition.

    May partition by any dimension, or be unpartitioned.
    Partitions now use randomized dimension names.
    """
    return st.builds(Waypoint, partition=st.none() | partition_strategy())


@st.composite
def bundles_strategy(draw, process_group_ids: list[str], waypoint_ids: list[str]):
    """Generate Bundles.

    These can be based on the process groups and waypoints passed in."""

    assume(len(process_group_ids) >= 1)
    source = draw(st.sampled_from(process_group_ids) | st.just(Elsewhere))
    target_choices = [k for k in process_group_ids if k != source]
    target = draw(
        (st.sampled_from(target_choices) | st.just(Elsewhere))
        if target_choices
        else st.just(Elsewhere)
    )
    # XXX could relax this condition?
    # assume(source != target)
    assume(source is not Elsewhere or target is not Elsewhere)

    # Maybe route through some waypoints
    if waypoint_ids:
        waypoints: tuple[str] = tuple(
            draw(st.lists(st.sampled_from(waypoint_ids), min_size=0, unique=True))
        )
    else:
        waypoints = ()

    # Check for duplicates based on (source, target) only
    # Bundles with same source/target match the same flows (even with different waypoints)
    # The old implementation doesn't allow this unless flows are completely non-overlapping
    used_bundle_keys: dict[tuple[str, str], set] = draw(
        st.shared(st.builds(dict), key="used_bundle_keys")
    )
    used_selections = used_bundle_keys.setdefault((source, target), set())

    # Maybe add a flow selection
    flow_selection = draw(st.none() | material_id().map(lambda m: f'material == "{m}"'))

    # To avoid duplicate bundles, avoid duplicate flow_selections, and
    # avoid None selections combined with other bundles
    assume(
        (flow_selection is None and len(used_selections) == 0)
        or (
            flow_selection is not None
            and None not in used_selections
            and flow_selection not in used_selections
        )
    )
    used_selections.add(flow_selection)

    bundle = Bundle(source, target, waypoints=waypoints, flow_selection=flow_selection)

    return bundle


@st.composite
def sankey_definitions(draw):
    """Generate a random SankeyDefinition and Dataset.

    This is intentionally messy and realistic:
    - May have 0 to 3 waypoints
    - May have 1-5 process groups
    - Some groups may have partitions, some may not
    - Bundles may route through 0-2 waypoints
    - Dataset may have flows that don't match bundles
    - Dataset may have processes not in the definition
    - Some bundles may have no matching flows
    """
    # First generate flow data to know what processes/materials exist
    # flows_df = draw(flow_table())

    # # Extract available processes and dimension values from the flows
    # all_processes = list(set(flows_df['source'].tolist() + flows_df['target'].tolist()))

    # # Maybe add some extra processes that aren't in flows
    # min_extra = 1 if len(all_processes) == 0 else 0
    # extra_processes = draw(st.lists(process_id(), min_size=min_extra, max_size=5))
    # all_processes = list(set(all_processes + extra_processes))

    # # Build dimension values map for partitioning
    # dimension_values_map: dict[str, list[str]] = {
    #     'process': all_processes,
    #     'material': list(set(flows_df['material'].tolist())),
    #     'category': list(set(flows_df['category'].tolist())),
    # }

    # # Create 1-6 process groups
    # num_groups = draw(st.integers(min_value=1, max_value=min(6, len(all_processes))))

    # # Split processes randomly among groups
    # process_assignments = {}
    # used_processes = set()
    # node_ids = [f"node{i}" for i in range(num_groups)]

    # for node_id in node_ids[:-1]:
    #     # Select processes for this group
    #     available = [p for p in all_processes if p not in used_processes]
    #     if not available:
    #         break
    #     max_procs = max(1, len(available) // 2)
    #     procs = draw(st.lists(st.sampled_from(available), min_size=1, max_size=max_procs, unique=True))
    #     process_assignments[node_id] = procs
    #     used_processes.update(procs)

    # # Last node gets remaining processes
    # remaining = [p for p in all_processes if p not in used_processes]
    # if remaining:
    #     process_assignments[node_ids[-1]] = remaining

    # # Create process groups
    # nodes = {}
    # for node_id, procs in process_assignments.items():
    #     group = draw(process_group_def(procs, dimension_values_map))
    #     if group:
    #         nodes[node_id] = group

    pgroups = draw(st.lists(process_groups(), min_size=1, max_size=6))
    waypoints = draw(st.lists(waypoint_def(), max_size=3))

    nodes = {}
    for i, node in enumerate(pgroups):
        nodes[f"node{i}"] = node
    for i, node in enumerate(waypoints):
        nodes[f"waypoint{i}"] = node
    process_group_ids = [f"node{i}" for i in range(len(pgroups))]
    waypoint_ids = [f"waypoint{i}" for i in range(len(waypoints))]

    # Create bundles connecting process groups
    # Some bundles may route through waypoints, some may not
    # Some bundles may have flow_selection filters
    # Some bundles may go to/from Elsewhere
    bundles = draw(
        st.lists(
            bundles_strategy(process_group_ids, waypoint_ids), min_size=1, max_size=5
        )
    )

    # Stats
    num_bundles_with_selections = len([b for b in bundles if b.flow_selection])
    event("num_bundles", payload=len(bundles))
    event("num_bundles_with_selections", payload=num_bundles_with_selections)

    # Create ordering - simple linear ordering with all process groups and waypoints
    all_node_ids = list(nodes.keys())
    ordering = [[nid] for nid in all_node_ids]

    # Add a global filter - Filter to exclude one material (so we still have
    # some flows)
    # available_materials = dimension_values_map.get('material', [])
    # excluded_material = draw((st.sampled_from(available_materials) | st.none()) if available_materials else st.none())
    # global_flow_selection = f'material != "{excluded_material}"' if excluded_material else None
    # global_flow_selection = draw(
    #     st.none() |
    #     material_id().map(lambda m: f'material == "{m}"')
    # )
    global_flow_selection = None
    note(f"global_flow_selection = {global_flow_selection}")

    # Maybe partition all flows by a dimension
    # Note: 'process' is only valid for ProcessGroup partitions, not flow partitions
    # Flow partitions must use actual flow data columns
    global_flow_partition = draw(st.none() | partition_strategy())

    # Create SankeyDefinition with optional global filters/partitions
    sdd = SankeyDefinition(
        nodes,
        bundles,
        ordering,
        flow_selection=global_flow_selection,
        flow_partition=global_flow_partition,
    )

    return sdd


@st.composite
def datasets(draw, sankey_definition):
    # Create dataset

    # Could use this to direct process IDs within flow_table()? But currently
    # works ok due to process_ids() strategy mixing used and unused ids.
    #
    # sdd_process_ids = set(
    #     pid
    #     for node in sankey_definition.nodes.values()
    #     if isinstance(node, ProcessGroup)
    #     for pid in node.selection
    # )

    # # Maybe add some extra processes that aren't in flows
    # extra_process_ids: set[str] = draw(st.sets(unique_process_id(), min_size=0, max_size=5))
    # all_process_ids = list(sdd_process_ids | extra_process_ids)

    # First generate flow data to know what processes/materials exist
    flows_df = draw(flow_table())
    all_process_ids = list(set(flows_df["source"]) | set(flows_df["target"]))
    if all_process_ids:
        dim_process = pd.DataFrame({"id": all_process_ids}).set_index("id")
    else:
        dim_process = None
    dataset = Dataset(flows_df, dim_process)

    return dataset
