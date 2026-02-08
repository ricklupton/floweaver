"""Measure execution time for compile() and execute_weave() stages.

This script uses the fruit example from test_fruit_example_from_paper() to
measure the performance of:
1. compile() - compiling the SankeyDefinition into a WeaverSpec
2. execute_weave() - executing the spec against the flow data

Compares the old filter-based approach vs the new routing tree approach.
"""

import os
import time
import json
import gzip
import numpy as np
import pandas as pd
from floweaver import (
    SankeyDefinition,
    ProcessGroup,
    Waypoint,
    Bundle,
    Partition,
    Dataset,
    Elsewhere,
    compile_sankey_definition,
    weave,
)
from floweaver.compiler import execute_weave


def sankey_data_equivalent(new_result, old_result):
    """Compare SankeyData objects with detailed assertion messages."""
    assert new_result.ordering == old_result.ordering, (
        f"Ordering mismatch: {new_result.ordering} != {old_result.ordering}"
    )

    # Compare nodes with tolerance for floating point differences
    new_nodes_sorted = sorted(new_result.nodes, key=lambda n: n.id)
    old_nodes_sorted = sorted(old_result.nodes, key=lambda n: n.id)
    assert len(new_nodes_sorted) == len(old_nodes_sorted), (
        f"Node count mismatch: {len(new_nodes_sorted)} != {len(old_nodes_sorted)}"
    )

    for new_node, old_node in zip(new_nodes_sorted, old_nodes_sorted):
        assert new_node.id == old_node.id, (
            f"Node id mismatch: {new_node.id} != {old_node.id}"
        )
        assert new_node.title == old_node.title
        assert new_node.direction == old_node.direction
        # The new implementation correctly sets hidden=True for catch-all partition
        # nodes (label='_'), while the old defaults to False. Accept this improvement.
        if new_node.hidden != old_node.hidden:
            assert new_node.id.endswith("^_"), (
                f"hidden mismatch for non-catch-all node: {new_node.id}"
            )
            assert new_node.hidden == True and old_node.hidden == False, (
                f"unexpected hidden values: new={new_node.hidden}, old={old_node.hidden}"
            )
        assert new_node.style == old_node.style

        # Compare elsewhere links with float tolerance
        assert len(new_node.from_elsewhere_links) == len(old_node.from_elsewhere_links)
        assert len(new_node.to_elsewhere_links) == len(old_node.to_elsewhere_links)

        for new_link, old_link in zip(
            new_node.from_elsewhere_links, old_node.from_elsewhere_links
        ):
            assert new_link.source == old_link.source
            assert new_link.target == old_link.target
            assert set(new_link.original_flows) == set(old_link.original_flows)
            # The old implementation has a bug where flows can be counted multiple times
            # when they match overlapping elsewhere bundles. The new implementation
            # correctly deduplicates. If unique flows match but link_width differs,
            # check if it's due to duplicates in the old result.
            if not np.isclose(new_link.link_width, old_link.link_width, rtol=1e-14):
                old_has_duplicates = len(old_link.original_flows) > len(
                    set(old_link.original_flows)
                )
                new_has_duplicates = len(new_link.original_flows) > len(
                    set(new_link.original_flows)
                )
                assert old_has_duplicates and not new_has_duplicates, (
                    f"link_width mismatch not due to old duplicates: {new_link.link_width} vs {old_link.link_width}"
                )

        for new_link, old_link in zip(
            new_node.to_elsewhere_links, old_node.to_elsewhere_links
        ):
            assert new_link.source == old_link.source
            assert new_link.target == old_link.target
            assert set(new_link.original_flows) == set(old_link.original_flows)
            # Same duplicate handling as above
            if not np.isclose(new_link.link_width, old_link.link_width, rtol=1e-14):
                old_has_duplicates = len(old_link.original_flows) > len(
                    set(old_link.original_flows)
                )
                new_has_duplicates = len(new_link.original_flows) > len(
                    set(new_link.original_flows)
                )
                assert old_has_duplicates and not new_has_duplicates, (
                    f"link_width mismatch not due to old duplicates: {new_link.link_width} vs {old_link.link_width}"
                )

    new_groups = sorted(new_result.groups, key=lambda group: group["id"])
    old_groups = sorted(old_result.groups, key=lambda group: group["id"])
    assert new_groups == old_groups, f"Groups mismatch"

    # Check link properties
    def _link_props(link):
        return (
            link.source,
            link.target,
            link.type,
            link.time,
            link.title,
            link.color,
            set(link.original_flows),
        )

    new_props = sorted([_link_props(link) for link in new_result.links])
    old_props = sorted([_link_props(link) for link in old_result.links])
    assert new_props == old_props, (
        f"Link properties mismatch:\nNew: {new_props[:3]}\nOld: {old_props[:3]}"
    )

    # Check link values
    old_links_dict = {(l.source, l.target, l.type, l.time): l for l in old_result.links}
    new_links_dict = {(l.source, l.target, l.type, l.time): l for l in new_result.links}

    assert set(old_links_dict.keys()) == set(new_links_dict.keys()), (
        "Link keys don't match"
    )

    for key in old_links_dict:
        old_link = old_links_dict[key]
        new_link = new_links_dict[key]

        assert np.isclose(old_link.link_width, new_link.link_width, rtol=1e-14), (
            f"link_width mismatch for {key}: {old_link.link_width} vs {new_link.link_width}"
        )

        assert np.isclose(old_link.opacity, new_link.opacity, rtol=1e-14), (
            f"opacity mismatch for {key}: {old_link.opacity} vs {new_link.opacity}"
        )

        for measure_key in old_link.data:
            old_val = old_link.data[measure_key]
            new_val = new_link.data[measure_key]
            if isinstance(old_val, (int, float, np.number)):
                assert np.isclose(old_val, new_val, rtol=1e-14), (
                    f"data[{measure_key}] mismatch for {key}: {old_val} vs {new_val}"
                )


def setup_fruit_example():
    """Set up the fruit example data and definition."""
    # Load dataset from cookbook directory
    cookbook_dir = os.path.join(os.path.dirname(__file__), "..", "docs", "cookbook")
    dataset = Dataset.from_csv(
        os.path.join(cookbook_dir, "fruit_flows.csv"),
        os.path.join(cookbook_dir, "fruit_processes.csv"),
    )

    # Define partitions
    farm_ids = ["farm{}".format(i) for i in range(1, 16)]
    farm_partition_5 = Partition.Simple(
        "process", [("Other farms", farm_ids[5:])] + farm_ids[:5]
    )
    partition_fruit = Partition.Simple("material", ["bananas", "apples", "oranges"])
    partition_sector = Partition.Simple(
        "process.sector", ["government", "industry", "domestic"]
    )

    # Define nodes
    nodes = {
        "inputs": ProcessGroup(["inputs"], title="Inputs"),
        "compost": ProcessGroup('function == "composting stock"', title="Compost"),
        "farms": ProcessGroup(
            'function in ["allotment", "large farm", "small farm"]', farm_partition_5
        ),
        "eat": ProcessGroup(
            'function == "consumers" and location != "London"',
            partition_sector,
            title="consumers by sector",
        ),
        "landfill": ProcessGroup(
            'function == "landfill" and location != "London"', title="Landfill"
        ),
        "composting": ProcessGroup(
            'function == "composting process" and location != "London"',
            title="Composting",
        ),
        "fruit": Waypoint(partition_fruit, title="fruit type"),
        "w1": Waypoint(direction="L", title=""),
        "w2": Waypoint(direction="L", title=""),
        "export fruit": Waypoint(
            Partition.Simple("material", ["apples", "bananas", "oranges"])
        ),
        "exports": Waypoint(title="Exports"),
    }

    # Define ordering with multiple layers and bands
    ordering = [
        [[], ["inputs", "compost"], []],
        [[], ["farms"], ["w2"]],
        [["exports"], ["fruit"], []],
        [[], ["eat"], []],
        [["export fruit"], ["landfill", "composting"], ["w1"]],
    ]

    # Define bundles
    bundles = [
        Bundle("inputs", "farms"),
        Bundle("compost", "farms"),
        Bundle("farms", "eat", waypoints=["fruit"]),
        Bundle("farms", "compost", waypoints=["w2"]),
        Bundle("eat", "landfill"),
        Bundle("eat", "composting"),
        Bundle("composting", "compost", waypoints=["w1", "w2"]),
        Bundle("farms", Elsewhere, waypoints=["exports", "export fruit"]),
    ]

    # Create SankeyDefinition with flow_partition
    sdd = SankeyDefinition(
        nodes, bundles, ordering, flow_partition=dataset.partition("material")
    )

    # Build dimension_tables dict from dataset
    dimension_tables = {}
    if dataset._dim_process is not None:
        dimension_tables["process"] = dataset._dim_process
    if dataset._dim_material is not None:
        dimension_tables["material"] = dataset._dim_material
    if dataset._dim_time is not None:
        dimension_tables["time"] = dataset._dim_time

    # Define explicit palette dictionary
    palette = {
        "inputs": "#FBB4AE",
        "compost": "#B3CDE3",
        "apples": "#CCEBC5",
        "bananas": "#DECBE4",
        "oranges": "#FED9A6",
    }

    return sdd, dataset, dimension_tables, palette


def time_compile_and_execute(num_runs=10):
    """Time the compile() and execute_weave() stages separately."""
    print("Setting up fruit example...")
    sdd, dataset, dimension_tables, palette = setup_fruit_example()

    print(f"\nDataset info:")
    print(f"  Number of flow rows: {len(dataset._table)}")

    print(f"\nTiming compile() stage ({num_runs} runs)...")
    compile_times = []
    spec = None
    for i in range(num_runs):
        start = time.perf_counter()
        spec = compile_sankey_definition(
            sdd,
            measures="value",
            link_width=None,
            link_color=None,
            palette=palette,
            add_elsewhere_waypoints=True,
            dimension_tables=dimension_tables,
        )
        end = time.perf_counter()
        compile_times.append(end - start)
        if (i + 1) % 5 == 0:
            print(f"  Completed {i + 1}/{num_runs} runs")
    assert spec

    print(f"\nSpec info:")
    print(f"  Number of edges: {len(spec.edges)}")
    print(f"  Has routing tree: {spec.routing_tree is not None}")

    print(f"\nTiming execute_weave() stage ({num_runs} runs)...")
    execute_times = []
    for i in range(num_runs):
        start = time.perf_counter()
        execute_result = execute_weave(spec, dataset)
        end = time.perf_counter()
        execute_times.append(end - start)
        if (i + 1) % 5 == 0:
            print(f"  Completed {i + 1}/{num_runs} runs")

    print(f"\nTiming original weave() ({num_runs} runs)...")
    weave_times = []
    for i in range(num_runs):
        start = time.perf_counter()
        weave_result = weave(sdd, dataset, palette=palette)
        end = time.perf_counter()
        weave_times.append(end - start)
        if (i + 1) % 5 == 0:
            print(f"  Completed {i + 1}/{num_runs} runs")

    # Calculate statistics
    compile_mean = sum(compile_times) / len(compile_times)
    compile_min = min(compile_times)
    compile_max = max(compile_times)

    execute_mean = sum(execute_times) / len(execute_times)
    execute_min = min(execute_times)
    execute_max = max(execute_times)

    weave_mean = sum(weave_times) / len(weave_times)
    weave_min = min(weave_times)
    weave_max = max(weave_times)

    total_mean = compile_mean + execute_mean

    # Print results
    print("\n" + "=" * 60)
    print("TIMING RESULTS")
    print("=" * 60)
    print(f"\ncompile() stage:")
    print(f"  Mean:  {compile_mean * 1000:.2f} ms")
    print(f"  Min:   {compile_min * 1000:.2f} ms")
    print(f"  Max:   {compile_max * 1000:.2f} ms")

    print(f"\nexecute_weave() stage:")
    print(f"  Mean:  {execute_mean * 1000:.2f} ms")
    print(f"  Min:   {execute_min * 1000:.2f} ms")
    print(f"  Max:   {execute_max * 1000:.2f} ms")

    print(f"\nTotal (compile + execute):")
    print(f"  Mean:  {total_mean * 1000:.2f} ms")

    print(f"\nBreakdown:")
    print(f"  compile():       {compile_mean / total_mean * 100:.1f}%")
    print(f"  execute_weave(): {execute_mean / total_mean * 100:.1f}%")

    print(f"\noriginal weave():")
    print(f"  Mean:  {weave_mean * 1000:.2f} ms")
    print(f"  Min:   {weave_min * 1000:.2f} ms")
    print(f"  Max:   {weave_max * 1000:.2f} ms")

    print("\n" + "=" * 60)

    # Verify the result looks reasonable
    print(f"\nResult validation:")
    print(f"  Number of nodes: {len(execute_result.nodes)}")
    print(f"  Number of links: {len(execute_result.links)}")
    print(f"  Number of groups: {len(execute_result.groups)}")
    print(f"  Number of layers: {len(execute_result.ordering.layers)}")
    sankey_data_equivalent(execute_result, weave_result)

    spec_dict = spec.to_json()
    json_str = json.dumps(spec_dict, separators=(",", ":"))
    gzipped = gzip.compress(json_str.encode())

    print(f"  JSON: {len(json_str):,} bytes ({len(json_str) / 1024:.1f} KB)")
    print(f"  Gzip: {len(gzipped):,} bytes ({len(gzipped) / 1024:.1f} KB)")
    print(f"  Compression ratio: {len(gzipped) / len(json_str) * 100:.1f}%")

    return compile_mean, execute_mean, execute_result


if __name__ == "__main__":
    time_compile_and_execute(num_runs=10)
