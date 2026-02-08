"""Equivalence tests comparing the original weave() with weave_compiled().

These tests verify that the new compile+execute approach produces equivalent
results to the original weave() implementation for various scenarios.

The key aspects to compare are:
- Node IDs and their properties
- Link data values and connections
- Ordering structure
- Group structure (with some expected differences)

Some known differences that are acceptable:
- Group types may differ ('process' vs 'group')
- Color ordering may differ (same colors, different assignment order)
- Node titles for partition groups may differ slightly
"""

import numpy as np
import pandas as pd

from floweaver import (
    SankeyDefinition,
    ProcessGroup,
    Waypoint,
    Bundle,
    Partition,
    Dataset,
    CategoricalScale,
)
from floweaver.weave import weave, weave_compiled
from helpers import assert_sankey_data_equivalent


def assert_node_directions(old_result, new_result):
    """Compare node directions."""
    old_dirs = {node.id: node.direction for node in old_result.nodes}
    new_dirs = {node.id: node.direction for node in new_result.nodes}
    assert new_dirs == old_dirs


def assert_link_endpoints(old_result, new_result):
    """Compare link source/target pairs."""
    old_endpoints = sorted((link.source, link.target) for link in old_result.links)
    new_endpoints = sorted((link.source, link.target) for link in new_result.links)
    assert new_endpoints == old_endpoints


def assert_link_values(old_result, new_result, measure="value"):
    """Compare aggregated values for each link."""
    old_vals = {
        (link.source, link.target, link.type, link.time): link.data.get(measure)
        for link in old_result.links
    }
    new_vals = {
        (link.source, link.target, link.type, link.time): link.data.get(measure)
        for link in new_result.links
    }
    assert new_vals == old_vals


def assert_link_original_flows(old_result, new_result):
    """Compare original flow indices for each link."""
    old_flows = {
        (link.source, link.target, link.type, link.time): sorted(link.original_flows)
        for link in old_result.links
    }
    new_flows = {
        (link.source, link.target, link.type, link.time): sorted(link.original_flows)
        for link in new_result.links
    }
    assert new_flows == old_flows


def assert_ordering_structure(old_result, new_result):
    """Compare ordering structure (layers/bands)."""

    # Convert to list of list of set for comparison (order within band may vary)
    def normalize_ordering(ordering):
        return [[set(band) for band in layer] for layer in ordering.layers]

    old_norm = normalize_ordering(old_result.ordering)
    new_norm = normalize_ordering(new_result.ordering)
    assert new_norm == old_norm


def assert_group_nodes(old_result, new_result):
    """Compare which nodes belong to which groups."""
    old_groups = {group["id"]: set(group["nodes"]) for group in old_result.groups}
    new_groups = {group["id"]: set(group["nodes"]) for group in new_result.groups}
    assert new_groups == old_groups


class TestBasicEquivalence:
    """Basic equivalence tests for simple scenarios."""

    def test_simple_two_nodes(self):
        """Test simplest case: two ProcessGroups connected by one Bundle."""
        nodes = {
            "a": ProcessGroup(selection=["a1", "a2"]),
            "b": ProcessGroup(selection=["b1"]),
        }
        bundles = [Bundle("a", "b")]
        ordering = [["a"], ["b"]]
        sdd = SankeyDefinition(nodes, bundles, ordering)

        flows = pd.DataFrame.from_records(
            [
                ("a1", "b1", "m", 3),
                ("a2", "b1", "m", 2),
            ],
            columns=("source", "target", "material", "value"),
        )
        dataset = Dataset(flows)

        old_result = weave(sdd, dataset)
        new_result = weave_compiled(sdd, dataset)

        assert_sankey_data_equivalent(new_result, old_result)

    def test_accepts_dataframe(self):
        """Test that both implementations accept DataFrame directly."""
        nodes = {
            "a": ProcessGroup(selection=["a1"]),
            "b": ProcessGroup(selection=["b1"]),
        }
        bundles = [Bundle("a", "b")]
        ordering = [["a"], ["b"]]
        sdd = SankeyDefinition(nodes, bundles, ordering)

        flows = pd.DataFrame.from_records(
            [("a1", "b1", "m", 3)], columns=("source", "target", "material", "value")
        )

        old_result = weave(sdd, flows)
        new_result = weave_compiled(sdd, flows)

        assert_sankey_data_equivalent(new_result, old_result)


class TestPartitionEquivalence:
    """Test equivalence with partition expansion."""

    def test_waypoint_with_material_partition(self):
        """Test waypoint partitioned by material."""
        nodes = {
            "a": ProcessGroup(selection=["a1", "a2"]),
            "b": ProcessGroup(selection=["b1"]),
            "via": Waypoint(partition=Partition.Simple("material", ["m", "n"])),
        }
        bundles = [Bundle("a", "b", waypoints=["via"])]
        ordering = [[["a"]], [["via"]], [["b"]]]
        sdd = SankeyDefinition(nodes, bundles, ordering)

        flows = pd.DataFrame.from_records(
            [
                ("a1", "b1", "m", 3),
                ("a2", "b1", "n", 2),
            ],
            columns=("source", "target", "material", "value"),
        )
        dataset = Dataset(flows)

        old_result = weave(sdd, dataset)
        new_result = weave_compiled(sdd, dataset)

        assert_sankey_data_equivalent(new_result, old_result)

    def test_process_group_partition(self):
        """Test ProcessGroup with process partition."""
        nodes = {
            "a": ProcessGroup(selection=["a1", "a2"]),
            "c": ProcessGroup(
                selection=["c1", "c2"],
                partition=Partition.Simple("process", ["c1", "c2"]),
            ),
        }
        bundles = [Bundle("a", "c")]
        ordering = [[["a"]], [["c"]]]
        sdd = SankeyDefinition(nodes, bundles, ordering)

        flows = pd.DataFrame.from_records(
            [
                ("a1", "c1", "m", 3),
                ("a2", "c2", "m", 2),
            ],
            columns=("source", "target", "material", "value"),
        )
        dataset = Dataset(flows)

        old_result = weave(sdd, dataset)
        new_result = weave_compiled(sdd, dataset)

        assert_sankey_data_equivalent(new_result, old_result)

    def test_complex_partitions(self):
        """Test complex scenario with multiple partitions."""
        nodes = {
            "a": ProcessGroup(selection=["a1", "a2"]),
            "b": ProcessGroup(selection=["b1"]),
            "c": ProcessGroup(
                selection=["c1", "c2"],
                partition=Partition.Simple("process", ["c1", "c2"]),
            ),
            "via": Waypoint(partition=Partition.Simple("material", ["m", "n"])),
        }
        bundles = [
            Bundle("a", "c", waypoints=["via"]),
            Bundle("b", "c", waypoints=["via"]),
        ]
        ordering = [[["a", "b"]], [["via"]], [["c"]]]
        sdd = SankeyDefinition(nodes, bundles, ordering)

        flows = pd.DataFrame.from_records(
            [
                ("a1", "c1", "m", 3),
                ("a2", "c1", "n", 1),
                ("b1", "c1", "m", 1),
                ("b1", "c2", "m", 2),
                ("b1", "c2", "n", 1),
            ],
            columns=("source", "target", "material", "value"),
        )
        dim_process = pd.DataFrame(
            {"id": list(flows.source.unique()) + list(flows.target.unique())}
        ).set_index("id")
        dataset = Dataset(flows, dim_process)

        old_result = weave(sdd, dataset)
        new_result = weave_compiled(sdd, dataset)

        assert_sankey_data_equivalent(new_result, old_result)


class TestFlowPartitionEquivalence:
    """Test equivalence with flow_partition."""

    def test_flow_partition_on_definition(self):
        """Test flow_partition set on SankeyDefinition."""
        nodes = {
            "a": ProcessGroup(selection=["a1", "a2"]),
            "b": ProcessGroup(selection=["b1"]),
            "c": ProcessGroup(
                selection=["c1", "c2"],
                partition=Partition.Simple("process", ["c1", "c2"]),
            ),
            "via": Waypoint(partition=Partition.Simple("material", ["m", "n"])),
        }
        bundles = [
            Bundle("a", "c", waypoints=["via"]),
            Bundle("b", "c", waypoints=["via"]),
        ]
        ordering = [[["a", "b"]], [["via"]], [["c"]]]
        sdd = SankeyDefinition(
            nodes,
            bundles,
            ordering,
            flow_partition=Partition.Simple("material", ["m", "n"]),
        )

        flows = pd.DataFrame.from_records(
            [
                ("a1", "c1", "m", 3),
                ("a2", "c1", "n", 1),
                ("b1", "c1", "m", 1),
                ("b1", "c2", "m", 2),
                ("b1", "c2", "n", 1),
            ],
            columns=("source", "target", "material", "value"),
        )
        dim_process = pd.DataFrame(
            {"id": list(flows.source.unique()) + list(flows.target.unique())}
        ).set_index("id")
        dataset = Dataset(flows, dim_process)

        old_result = weave(sdd, dataset)
        new_result = weave_compiled(sdd, dataset)

        assert_sankey_data_equivalent(new_result, old_result)


class TestColorScaleEquivalence:
    """Test equivalence with color scales."""

    def test_categorical_color_by_type(self):
        """Test categorical color scale by type."""
        nodes = {
            "a": ProcessGroup(selection=["a1", "a2"]),
            "b": ProcessGroup(selection=["b1"]),
            "c": ProcessGroup(
                selection=["c1", "c2"],
                partition=Partition.Simple("process", ["c1", "c2"]),
            ),
            "via": Waypoint(partition=Partition.Simple("material", ["m", "n"])),
        }
        bundles = [
            Bundle("a", "c", waypoints=["via"]),
            Bundle("b", "c", waypoints=["via"]),
        ]
        ordering = [[["a", "b"]], [["via"]], [["c"]]]
        sdd = SankeyDefinition(
            nodes,
            bundles,
            ordering,
            flow_partition=Partition.Simple("material", ["m", "n"]),
        )

        flows = pd.DataFrame.from_records(
            [
                ("a1", "c1", "m", 3),
                ("a2", "c1", "n", 1),
                ("b1", "c1", "m", 1),
                ("b1", "c2", "m", 2),
                ("b1", "c2", "n", 1),
            ],
            columns=("source", "target", "material", "value"),
        )
        dim_process = pd.DataFrame(
            {"id": list(flows.source.unique()) + list(flows.target.unique())}
        ).set_index("id")
        dataset = Dataset(flows, dim_process)

        scale = CategoricalScale("type", palette=["red", "blue"])
        scale.set_domain(["m", "n"])

        old_result = weave(sdd, dataset, link_color=scale)
        new_result = weave_compiled(sdd, dataset, link_color=scale)

        # Compare that all link values match
        assert_link_values(old_result, new_result)

        # Compare that colors are consistent for each type
        old_colors_by_type = {link.type: link.color for link in old_result.links}
        new_colors_by_type = {link.type: link.color for link in new_result.links}
        assert old_colors_by_type == new_colors_by_type


class TestElsewhereEquivalence:
    """Test equivalence with elsewhere flows."""

    def test_implicit_elsewhere_bundles(self):
        """Test that implicit elsewhere bundles are handled consistently."""
        nodes = {
            "a": ProcessGroup(selection=["a1"]),
            "b": ProcessGroup(selection=["b1"]),
        }
        bundles = [Bundle("a", "b")]
        ordering = [["a"], ["b"]]
        sdd = SankeyDefinition(nodes, bundles, ordering)

        # Include flows from/to outside the system
        flows = pd.DataFrame.from_records(
            [
                ("a1", "b1", "m", 3),
                ("x1", "a1", "m", 2),  # from elsewhere to a
                ("b1", "y1", "m", 1),  # from b to elsewhere
            ],
            columns=("source", "target", "material", "value"),
        )
        dataset = Dataset(flows)

        old_result = weave(sdd, dataset, add_elsewhere_waypoints=True)
        new_result = weave_compiled(sdd, dataset, add_elsewhere_waypoints=True)

        # Compare main links
        assert_link_values(old_result, new_result)


class TestMeasureEquivalence:
    """Test equivalence with different measure configurations."""

    def test_default_measure(self):
        """Test default measure (value with sum)."""
        nodes = {
            "a": ProcessGroup(selection=["a1"]),
            "b": ProcessGroup(selection=["b1"]),
        }
        bundles = [Bundle("a", "b")]
        ordering = [["a"], ["b"]]
        sdd = SankeyDefinition(nodes, bundles, ordering)

        flows = pd.DataFrame.from_records(
            [
                ("a1", "b1", "m", 3),
                ("a1", "b1", "n", 2),
            ],
            columns=("source", "target", "material", "value"),
        )
        dataset = Dataset(flows)

        old_result = weave(sdd, dataset)
        new_result = weave_compiled(sdd, dataset)

        assert_link_values(old_result, new_result)

    def test_multiple_measures(self):
        """Test multiple measures."""
        nodes = {
            "a": ProcessGroup(selection=["a1"]),
            "b": ProcessGroup(selection=["b1"]),
        }
        bundles = [Bundle("a", "b")]
        ordering = [["a"], ["b"]]
        sdd = SankeyDefinition(nodes, bundles, ordering)

        flows = pd.DataFrame.from_records(
            [
                ("a1", "b1", "m", 3, 10),
                ("a1", "b1", "n", 2, 20),
            ],
            columns=("source", "target", "material", "value", "cost"),
        )
        dataset = Dataset(flows)

        # Old weave() requires link_width when passing list of measures
        old_result = weave(sdd, dataset, measures=["value", "cost"], link_width="value")
        new_result = weave_compiled(
            sdd, dataset, measures=["value", "cost"], link_width="value"
        )

        # Check both measures
        assert_link_values(old_result, new_result, "value")
        assert_link_values(old_result, new_result, "cost")


class TestOrderingEquivalence:
    """Test equivalence of ordering structure."""

    def test_ordering_with_bands(self):
        """Test that bands are preserved correctly."""
        nodes = {
            "a": ProcessGroup(selection=["a1"]),
            "b": ProcessGroup(selection=["b1"]),
            "c": ProcessGroup(selection=["c1"]),
        }
        bundles = [Bundle("a", "b"), Bundle("a", "c")]
        ordering = [
            [["a"]],
            [["b"], ["c"]],  # b and c in different bands
        ]
        sdd = SankeyDefinition(nodes, bundles, ordering)

        flows = pd.DataFrame.from_records(
            [
                ("a1", "b1", "m", 3),
                ("a1", "c1", "m", 2),
            ],
            columns=("source", "target", "material", "value"),
        )
        dataset = Dataset(flows)

        old_result = weave(sdd, dataset)
        new_result = weave_compiled(sdd, dataset)

        assert_ordering_structure(old_result, new_result)


class TestGroupEquivalence:
    """Test equivalence of group structure."""

    def test_groups_with_partitions(self):
        """Test that groups contain the correct nodes."""
        nodes = {
            "a": ProcessGroup(selection=["a1", "a2"]),
            "b": ProcessGroup(selection=["b1"]),
            "c": ProcessGroup(
                selection=["c1", "c2"],
                partition=Partition.Simple("process", ["c1", "c2"]),
            ),
            "via": Waypoint(partition=Partition.Simple("material", ["m", "n"])),
        }
        bundles = [
            Bundle("a", "c", waypoints=["via"]),
            Bundle("b", "c", waypoints=["via"]),
        ]
        ordering = [[["a", "b"]], [["via"]], [["c"]]]
        sdd = SankeyDefinition(nodes, bundles, ordering)

        flows = pd.DataFrame.from_records(
            [
                ("a1", "c1", "m", 3),
                ("a2", "c1", "n", 1),
                ("b1", "c1", "m", 1),
                ("b1", "c2", "m", 2),
                ("b1", "c2", "n", 1),
            ],
            columns=("source", "target", "material", "value"),
        )
        dim_process = pd.DataFrame(
            {"id": list(flows.source.unique()) + list(flows.target.unique())}
        ).set_index("id")
        dataset = Dataset(flows, dim_process)

        old_result = weave(sdd, dataset)
        new_result = weave_compiled(sdd, dataset)

        # Compare which nodes are in each group
        assert_group_nodes(old_result, new_result)


class TestLinkWidthEquivalence:
    """Test equivalence of link width calculation."""

    def test_link_width_matches_value(self):
        """Test that link_width values match."""
        nodes = {
            "a": ProcessGroup(selection=["a1"]),
            "b": ProcessGroup(selection=["b1"]),
        }
        bundles = [Bundle("a", "b")]
        ordering = [["a"], ["b"]]
        sdd = SankeyDefinition(nodes, bundles, ordering)

        flows = pd.DataFrame.from_records(
            [
                ("a1", "b1", "m", 3),
                ("a1", "b1", "n", 2),
            ],
            columns=("source", "target", "material", "value"),
        )
        dataset = Dataset(flows)

        old_result = weave(sdd, dataset)
        new_result = weave_compiled(sdd, dataset)

        old_widths = {
            (link.source, link.target): link.link_width for link in old_result.links
        }
        new_widths = {
            (link.source, link.target): link.link_width for link in new_result.links
        }
        assert old_widths == new_widths


class TestDirectionEquivalence:
    """Test equivalence of node direction settings."""

    def test_node_directions_preserved(self):
        """Test that node directions (R/L) are preserved."""
        nodes = {
            "a": ProcessGroup(selection=["a1"], direction="L"),
            "b": ProcessGroup(selection=["b1"], direction="R"),
        }
        bundles = [Bundle("a", "b")]
        ordering = [["a"], ["b"]]
        sdd = SankeyDefinition(nodes, bundles, ordering)

        flows = pd.DataFrame.from_records(
            [("a1", "b1", "m", 3)], columns=("source", "target", "material", "value")
        )
        dataset = Dataset(flows)

        old_result = weave(sdd, dataset)
        new_result = weave_compiled(sdd, dataset)

        assert_node_directions(old_result, new_result)


class TestOriginalFlowsEquivalence:
    """Test that original_flows tracking is equivalent."""

    def test_original_flows_tracked(self):
        """Test that original flow indices are tracked correctly."""
        nodes = {
            "a": ProcessGroup(selection=["a1", "a2"]),
            "b": ProcessGroup(selection=["b1"]),
            "via": Waypoint(partition=Partition.Simple("material", ["m", "n"])),
        }
        bundles = [Bundle("a", "b", waypoints=["via"])]
        ordering = [[["a"]], [["via"]], [["b"]]]
        sdd = SankeyDefinition(nodes, bundles, ordering)

        flows = pd.DataFrame.from_records(
            [
                ("a1", "b1", "m", 3),
                ("a2", "b1", "m", 2),
                ("a1", "b1", "n", 1),
            ],
            columns=("source", "target", "material", "value"),
        )
        dataset = Dataset(flows)

        old_result = weave(sdd, dataset)
        new_result = weave_compiled(sdd, dataset)

        assert_link_original_flows(old_result, new_result)


class TestComplexRealWorldEquivalence:
    """Test equivalence with complex real-world example (fruit database)."""

    def test_fruit_example_from_paper(self):
        """Test complex fruit example from Hybrid Sankey diagrams paper.

        This test uses the data from docs/cookbook/hybrid-sankey-diagrams-paper-fruit-example.ipynb
        and exercises many features together:
        - Multiple ProcessGroups with query-based selection
        - Multiple Waypoints with various partitions
        - Complex multi-layer ordering with bands
        - Elsewhere flows
        - Flow partition on SankeyDefinition
        - Dimensional metadata (dim_process)
        """
        import os
        from floweaver import Elsewhere

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
                'function in ["allotment", "large farm", "small farm"]',
                farm_partition_5,
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

        # Build dimension_tables dict from dataset for weave_compiled
        dimension_tables = {}
        if dataset._dim_process is not None:
            dimension_tables["process"] = dataset._dim_process
        if dataset._dim_material is not None:
            dimension_tables["material"] = dataset._dim_material
        if dataset._dim_time is not None:
            dimension_tables["time"] = dataset._dim_time

        # Define explicit palette dictionary to ensure consistent colors
        # (list-based palettes have undefined ordering between implementations)
        palette = {
            "inputs": "#FBB4AE",
            "compost": "#B3CDE3",
            "apples": "#CCEBC5",
            "bananas": "#DECBE4",
            "oranges": "#FED9A6",
        }

        # Run both implementations
        old_result = weave(sdd, dataset, palette=palette)
        new_result = weave_compiled(
            sdd, dataset, dimension_tables=dimension_tables, palette=palette
        )

        assert_sankey_data_equivalent(new_result, old_result)
