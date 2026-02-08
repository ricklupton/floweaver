"""Unit tests for the compile() function."""

import pytest
import pandas as pd

from floweaver import (
    SankeyDefinition,
    ProcessGroup,
    Waypoint,
    Bundle,
    Partition,
    Elsewhere,
    CategoricalScale,
    QuantitativeScale,
)

from floweaver.compiler.spec import (
    WeaverSpec,
    DisplaySpec,
    CategoricalColorSpec,
    QuantitativeColorSpec,
)

from floweaver.compiler import compile_sankey_definition

# =============================================================================
# Basic compilation tests
# =============================================================================


def test_compile_simple():
    """Test basic compilation with two ProcessGroups."""
    nodes = {
        "a": ProcessGroup(selection=["a1", "a2"]),
        "b": ProcessGroup(selection=["b1", "b2"]),
    }
    bundles = [Bundle("a", "b")]
    ordering = [[["a"]], [["b"]]]

    sdd = SankeyDefinition(nodes=nodes, bundles=bundles, ordering=ordering)
    spec = compile_sankey_definition(sdd)

    assert isinstance(spec, WeaverSpec)
    assert spec.version == "2.0"

    # Check nodes are expanded with ^* suffix (no partition)
    assert "a^*" in spec.nodes
    assert "b^*" in spec.nodes

    # Check node specs
    assert spec.nodes["a^*"].type == "process"
    assert spec.nodes["a^*"].group == "a"
    assert spec.nodes["b^*"].type == "process"
    assert spec.nodes["b^*"].group == "b"

    assert isinstance(spec.nodes, dict)
    assert isinstance(spec.groups, list)
    assert isinstance(spec.bundles, list)
    assert isinstance(spec.ordering, list)
    assert isinstance(spec.edges, list)
    assert isinstance(spec.measures, list)
    assert isinstance(spec.display, DisplaySpec)


# =============================================================================
# Node expansion tests
# =============================================================================


def test_compile_node_without_partition():
    """Test that nodes without partition get ^* suffix."""
    nodes = {
        "a": ProcessGroup(selection=["a1"]),
        "b": ProcessGroup(selection=["b1"]),
    }
    bundles = [Bundle("a", "b")]
    ordering = [[["a"]], [["b"]]]

    sdd = SankeyDefinition(nodes=nodes, bundles=bundles, ordering=ordering)
    spec = compile_sankey_definition(sdd)

    assert "a^*" in spec.nodes
    assert "b^*" in spec.nodes
    assert spec.nodes["a^*"].title == "a"
    assert spec.nodes["b^*"].title == "b"


def test_compile_node_with_partition():
    """Test that nodes with partition expand to multiple nodes."""
    partition = Partition.Simple("material", ["m", "n"])
    nodes = {
        "a": ProcessGroup(selection=["a1"]),
        "via": Waypoint(partition=partition),
        "b": ProcessGroup(selection=["b1"]),
    }
    bundles = [Bundle("a", "b", waypoints=["via"])]
    ordering = [[["a"]], [["via"]], [["b"]]]

    sdd = SankeyDefinition(nodes=nodes, bundles=bundles, ordering=ordering)
    spec = compile_sankey_definition(sdd)

    # Waypoint should expand to partition labels + catch-all
    assert "via^m" in spec.nodes
    assert "via^n" in spec.nodes
    assert "via^_" in spec.nodes  # catch-all

    assert spec.nodes["via^m"].title == "m"
    assert spec.nodes["via^n"].title == "n"
    assert spec.nodes["via^_"].hidden is True


def test_compile_process_partition():
    """Test ProcessGroup with process partition."""
    partition = Partition.Simple("process", ["c1", "c2"])
    nodes = {
        "a": ProcessGroup(selection=["a1"]),
        "c": ProcessGroup(selection=["c1", "c2"], partition=partition),
    }
    bundles = [Bundle("a", "c")]
    ordering = [[["a"]], [["c"]]]

    sdd = SankeyDefinition(nodes=nodes, bundles=bundles, ordering=ordering)
    spec = compile_sankey_definition(sdd)

    assert "c^c1" in spec.nodes
    assert "c^c2" in spec.nodes
    assert "c^_" in spec.nodes

    assert spec.nodes["c^c1"].type == "process"
    assert spec.nodes["c^c2"].type == "process"


def test_compile_node_direction():
    """Test that node direction is preserved."""
    nodes = {
        "a": ProcessGroup(selection=["a1"], direction="L"),
        "b": ProcessGroup(selection=["b1"], direction="R"),
    }
    bundles = [Bundle("a", "b")]
    ordering = [[["a"]], [["b"]]]

    sdd = SankeyDefinition(nodes=nodes, bundles=bundles, ordering=ordering)
    spec = compile_sankey_definition(sdd)

    assert spec.nodes["a^*"].direction == "L"
    assert spec.nodes["b^*"].direction == "R"


def test_compile_node_title():
    """Test that custom node titles are preserved."""
    nodes = {
        "a": ProcessGroup(selection=["a1"], title="Source A"),
        "b": ProcessGroup(selection=["b1"], title="Target B"),
    }
    bundles = [Bundle("a", "b")]
    ordering = [[["a"]], [["b"]]]

    sdd = SankeyDefinition(nodes=nodes, bundles=bundles, ordering=ordering)
    spec = compile_sankey_definition(sdd)

    assert spec.nodes["a^*"].title == "Source A"
    assert spec.nodes["b^*"].title == "Target B"


# =============================================================================
# Edge filter tests
# =============================================================================


def test_compile_data_routing_simple():
    """Test that ProcessGroup selections become include filters."""
    nodes = {
        "a": ProcessGroup(selection=["a1", "a2"]),
        "b": ProcessGroup(selection=["b1", "b2", "b3"]),
    }
    bundles = [Bundle("a", "b")]
    ordering = [[["a"]], [["b"]]]

    sdd = SankeyDefinition(nodes=nodes, bundles=bundles, ordering=ordering)
    spec = compile_sankey_definition(sdd)

    # Check that data is routed as expected
    edge_ids = spec.routing_tree.evaluate({"source": "a1", "target": "b1"})
    assert len(edge_ids) == 1
    assert spec.edges[edge_ids[0]].source == "a^*"
    assert spec.edges[edge_ids[0]].target == "b^*"

    # Check that data is routed as expected
    edge_ids = spec.routing_tree.evaluate({"source": "a1", "target": "xxx"})
    assert len(edge_ids) == 1
    assert spec.edges[edge_ids[0]].source == "a^*"
    assert spec.edges[edge_ids[0]].target == "__a>^*"


def test_compile_data_routing_simple_no_elsewhere_waypoints():
    """Test that ProcessGroup selections become include filters."""
    nodes = {
        "a": ProcessGroup(selection=["a1", "a2"]),
        "b": ProcessGroup(selection=["b1", "b2", "b3"]),
    }
    bundles = [Bundle("a", "b")]
    ordering = [[["a"]], [["b"]]]

    sdd = SankeyDefinition(nodes=nodes, bundles=bundles, ordering=ordering)
    spec = compile_sankey_definition(sdd, add_elsewhere_waypoints=False)

    # Check that data is routed as expected
    edge_ids = spec.routing_tree.evaluate({"source": "a1", "target": "xxx"})
    assert len(edge_ids) == 1
    assert spec.edges[edge_ids[0]].source == "a^*"
    assert spec.edges[edge_ids[0]].target is None


def test_compile_process_group_query_string_selection():
    """Test that query string selections are encoded correctly when dimension
    tables are available."""
    nodes = {
        "a": ProcessGroup(selection="type == 'organic'"),
        "b": ProcessGroup(selection=["b1"]),
    }
    bundles = [Bundle("a", "b")]
    ordering = [[["a"]], [["b"]]]

    sdd = SankeyDefinition(nodes=nodes, bundles=bundles, ordering=ordering)
    dim_process = pd.DataFrame.from_dict(
        {
            "a1": {"type": "organic"},
            "a2": {"type": "inorganic"},
            "b1": {"type": "inorganic"},
        },
        orient="index",
    )
    spec = compile_sankey_definition(sdd, dimension_tables={"process": dim_process})

    # a1 is organic, should be included in a->b
    edge_ids = spec.routing_tree.evaluate({"source": "a1", "target": "b1"})
    assert len(edge_ids) == 1
    assert spec.edges[edge_ids[0]].source == "a^*"
    assert spec.edges[edge_ids[0]].target == "b^*"

    # a2 is inorganic, should not be included in a->b
    edge_ids = spec.routing_tree.evaluate({"source": "a2", "target": "b1"})
    assert len(edge_ids) == 1
    assert spec.edges[edge_ids[0]].source == "__>b^*"
    assert spec.edges[edge_ids[0]].target == "b^*"


def test_compile_process_group_query_string_fails_without_dim_table():
    """Test that query string selections fail when dimension tables are not
    available."""
    nodes = {
        "a": ProcessGroup(selection="type == 'organic'"),
        "b": ProcessGroup(selection=["b1"]),
    }
    bundles = [Bundle("a", "b")]
    ordering = [[["a"]], [["b"]]]

    sdd = SankeyDefinition(nodes=nodes, bundles=bundles, ordering=ordering)

    with pytest.raises(ValueError, match="Cannot compile query string selection"):
        compile_sankey_definition(sdd)


# =============================================================================
# Flow partition tests
# =============================================================================


def test_compile_data_routing_with_partition():
    """Test that ProcessGroup selections become include filters."""
    nodes = {
        "a": ProcessGroup(["a1", "a2"], Partition.Simple("process", ["a1"])),
        "b": ProcessGroup(["b1", "b2", "b3"]),
    }
    bundles = [Bundle("a", "b")]
    ordering = [[["a"]], [["b"]]]

    sdd = SankeyDefinition(
        nodes=nodes,
        bundles=bundles,
        ordering=ordering,
        flow_partition=Partition.Simple("material", ["m", "n"]),
    )
    spec = compile_sankey_definition(sdd)

    # Check that data is routed as expected
    edge_ids = spec.routing_tree.evaluate({"source": "a1", "target": "b1"})
    assert len(edge_ids) == 1
    assert spec.edges[edge_ids[0]].source == "a^a1"
    assert spec.edges[edge_ids[0]].target == "b^*"
    assert spec.edges[edge_ids[0]].type == "_"

    edge_ids = spec.routing_tree.evaluate({"source": "a2", "target": "b1"})
    assert len(edge_ids) == 1
    assert spec.edges[edge_ids[0]].source == "a^_"
    assert spec.edges[edge_ids[0]].target == "b^*"
    assert spec.edges[edge_ids[0]].type == "_"

    edge_ids = spec.routing_tree.evaluate(
        {"source": "a2", "target": "b1", "material": "m"}
    )
    assert len(edge_ids) == 1
    assert spec.edges[edge_ids[0]].source == "a^_"
    assert spec.edges[edge_ids[0]].target == "b^*"
    assert spec.edges[edge_ids[0]].type == "m"


def test_compile_flow_partition_on_bundle():
    """Test that bundle-level flow_partition is respected."""
    flow_partition = Partition.Simple("material", ["m", "n"])
    nodes = {
        "a": ProcessGroup(selection=["a1"]),
        "b": ProcessGroup(selection=["b1"]),
    }
    # Include elsewhere bundles explicitly so we can set their flow partition
    # explicitly for the right comparison; by default the implicit elsewhere
    # bundles have no flow partition set.
    bundles_with_partition = [
        Bundle("a", "b", flow_partition=flow_partition),
        Bundle(Elsewhere, "b", flow_partition=flow_partition),
        Bundle("a", Elsewhere, flow_partition=flow_partition),
    ]
    bundles_no_partition = [
        Bundle("a", "b"),
        Bundle(Elsewhere, "b"),
        Bundle("a", Elsewhere),
    ]
    ordering = [[["a"]], [["b"]]]

    sdd1 = SankeyDefinition(
        nodes=nodes, bundles=bundles_with_partition, ordering=ordering
    )
    sdd2 = SankeyDefinition(
        nodes=nodes,
        bundles=bundles_no_partition,
        ordering=ordering,
        flow_partition=flow_partition,
    )
    spec1 = compile_sankey_definition(sdd1)
    spec2 = compile_sankey_definition(sdd2)

    assert spec1.edges == spec2.edges
    assert spec1.routing_tree == spec2.routing_tree


# =============================================================================
# Time partition tests
# =============================================================================


def test_compile_time_partition():
    """Test that time_partition creates edges with time field."""
    time_partition = Partition.Simple("year", ["2020", "2021"])
    nodes = {
        "a": ProcessGroup(selection=["a1"]),
        "b": ProcessGroup(selection=["b1"]),
    }
    bundles = [Bundle("a", "b")]
    ordering = [[["a"]], [["b"]]]

    sdd = SankeyDefinition(
        nodes=nodes, bundles=bundles, ordering=ordering, time_partition=time_partition
    )
    spec = compile_sankey_definition(sdd)

    main_edges = [e for e in spec.edges if e.source == "a^*" and e.target == "b^*"]

    # Should have 3 edges: 2020, 2021, and catch-all
    assert len(main_edges) == 3

    times = {e.time for e in main_edges}
    assert times == {"2020", "2021", "_"}


def test_compile_flow_and_time_partition():
    """Test combination of flow and time partitions."""
    flow_partition = Partition.Simple("material", ["m", "n"])
    time_partition = Partition.Simple("year", ["2020", "2021"])
    nodes = {
        "a": ProcessGroup(selection=["a1"]),
        "b": ProcessGroup(selection=["b1"]),
    }
    bundles = [Bundle("a", "b")]
    ordering = [[["a"]], [["b"]]]

    sdd = SankeyDefinition(
        nodes=nodes,
        bundles=bundles,
        ordering=ordering,
        flow_partition=flow_partition,
        time_partition=time_partition,
    )
    spec = compile_sankey_definition(sdd)

    main_edges = [e for e in spec.edges if e.source == "a^*" and e.target == "b^*"]

    # Should have 3 flow types × 3 time values = 9 edges
    assert len(main_edges) == 9

    # Check all combinations exist
    combos = {(e.type, e.time) for e in main_edges}
    expected = {
        ("m", "2020"),
        ("m", "2021"),
        ("m", "_"),
        ("n", "2020"),
        ("n", "2021"),
        ("n", "_"),
        ("_", "2020"),
        ("_", "2021"),
        ("_", "_"),
    }
    assert combos == expected


# =============================================================================
# Elsewhere bundle tests
# =============================================================================


def test_compile_elsewhere_bundles_added():
    """Test that elsewhere bundles are automatically added."""
    nodes = {
        "a": ProcessGroup(selection=["a1"]),
        "b": ProcessGroup(selection=["b1"]),
    }
    bundles = [Bundle("a", "b")]
    ordering = [[["a"]], [["b"]]]

    sdd = SankeyDefinition(nodes=nodes, bundles=bundles, ordering=ordering)
    spec = compile_sankey_definition(sdd)

    # Should have elsewhere waypoint nodes
    elsewhere_nodes = [n for n in spec.nodes.keys() if n.startswith("__")]
    assert (
        len(elsewhere_nodes) >= 2
    )  # At least to/from elsewhere for each process group


def test_compile_elsewhere_exclude_with_query_selection():
    """Test that elsewhere edges exclude flows covered by explicit bundles
    when using query-based selections.

    This is a regression test for the bug where query-based selections don't
    generate exclude filters for elsewhere bundles, causing flows to be
    counted multiple times.
    """
    nodes = {
        "a": ProcessGroup(selection='type == "source"'),
        "b": ProcessGroup(selection='type == "dest"'),
    }
    bundles = [Bundle("a", "b")]
    ordering = [[["a"]], [["b"]]]

    sdd = SankeyDefinition(nodes=nodes, bundles=bundles, ordering=ordering)

    dim_process = pd.DataFrame(
        {
            "id": ["a1", "b1", "b2"],
            "type": ["source", "dest", "dest"],
        }
    ).set_index("id")

    spec = compile_sankey_definition(
        sdd, dimension_tables={"process": dim_process}, add_elsewhere_waypoints=False
    )

    edge_ids = spec.routing_tree.evaluate({"source": "a1", "target": "b1"})
    assert len(edge_ids) == 1
    assert spec.edges[edge_ids[0]].source == "a^*"
    assert spec.edges[edge_ids[0]].target == "b^*"

    edge_ids = spec.routing_tree.evaluate({"source": "a1", "target": "xx"})
    assert len(edge_ids) == 1
    assert spec.edges[edge_ids[0]].source == "a^*"
    assert spec.edges[edge_ids[0]].target is None

    edge_ids = spec.routing_tree.evaluate({"source": "xx", "target": "b2"})
    assert len(edge_ids) == 1
    assert spec.edges[edge_ids[0]].source is None
    assert spec.edges[edge_ids[0]].target == "b^*"

    edge_ids = spec.routing_tree.evaluate({"source": "xx", "target": "xx"})
    assert len(edge_ids) == 0


# =============================================================================
# Ordering tests
# =============================================================================


def test_compile_ordering_expanded():
    """Test that ordering uses expanded node IDs."""
    partition = Partition.Simple("material", ["m", "n"])
    nodes = {
        "a": ProcessGroup(selection=["a1"]),
        "via": Waypoint(partition=partition),
        "b": ProcessGroup(selection=["b1"]),
    }
    bundles = [Bundle("a", "b", waypoints=["via"])]
    ordering = [[["a"]], [["via"]], [["b"]]]

    sdd = SankeyDefinition(nodes=nodes, bundles=bundles, ordering=ordering)
    spec = compile_sankey_definition(sdd)

    # Flatten ordering to check nodes
    all_nodes_in_ordering = []
    for layer in spec.ordering:
        for band in layer:
            all_nodes_in_ordering.extend(band)

    assert "a^*" in all_nodes_in_ordering
    assert "via^m" in all_nodes_in_ordering
    assert "via^n" in all_nodes_in_ordering
    assert "via^_" in all_nodes_in_ordering
    assert "b^*" in all_nodes_in_ordering


def test_compile_ordering_bands():
    """Test that bands in ordering are preserved."""
    nodes = {
        "a": ProcessGroup(selection=["a1"]),
        "b": ProcessGroup(selection=["b1"]),
        "c": ProcessGroup(selection=["c1"]),
    }
    bundles = [Bundle("a", "b"), Bundle("a", "c")]
    ordering = [
        [["a"], []],  # Layer 0: a in band 0
        [["b"], ["c"]],  # Layer 1: b in band 0, c in band 1
    ]

    sdd = SankeyDefinition(nodes=nodes, bundles=bundles, ordering=ordering)
    spec = compile_sankey_definition(sdd)

    # Check band structure is preserved
    assert "a^*" in spec.ordering[0][0]
    assert "b^*" in spec.ordering[1][0]
    assert "c^*" in spec.ordering[1][1]


# =============================================================================
# Group and bundle spec tests
# =============================================================================


def test_compile_group_specs():
    """Test that GroupSpecs are created correctly."""
    partition = Partition.Simple("process", ["c1", "c2"])
    nodes = {
        "a": ProcessGroup(selection=["a1"], title="Source"),
        "c": ProcessGroup(selection=["c1", "c2"], partition=partition, title="Targets"),
    }
    bundles = [Bundle("a", "c")]
    ordering = [[["a"]], [["c"]]]

    sdd = SankeyDefinition(nodes=nodes, bundles=bundles, ordering=ordering)
    spec = compile_sankey_definition(sdd)

    # Find group for 'c'
    c_group = next(g for g in spec.groups if g.id == "c")
    assert c_group.title == "Targets"
    assert "c^c1" in c_group.nodes
    assert "c^c2" in c_group.nodes
    assert "c^_" in c_group.nodes


def test_compile_bundle_specs():
    """Test that BundleSpecs are created correctly."""
    nodes = {
        "a": ProcessGroup(selection=["a1"]),
        "b": ProcessGroup(selection=["b1"]),
        "c": ProcessGroup(selection=["c1"]),
    }
    bundles = [Bundle("a", "b"), Bundle("b", "c")]
    ordering = [[["a"]], [["b"]], [["c"]]]

    sdd = SankeyDefinition(nodes=nodes, bundles=bundles, ordering=ordering)
    spec = compile_sankey_definition(sdd)

    # Find bundle specs (excluding elsewhere bundles)
    bundle_0 = next((b for b in spec.bundles if b.id == "0"), None)
    bundle_1 = next((b for b in spec.bundles if b.id == "1"), None)

    assert bundle_0 is not None
    assert bundle_0.source == "a"
    assert bundle_0.target == "b"

    assert bundle_1 is not None
    assert bundle_1.source == "b"
    assert bundle_1.target == "c"


def test_compile_edge_bundle_ids_field():
    """Test that edges have correct bundle_ids field for provenance."""
    nodes = {
        "a": ProcessGroup(selection=["a1"]),
        "via": Waypoint(),
        "b": ProcessGroup(selection=["b1"]),
        "c": ProcessGroup(selection=["c1"]),
    }
    bundles = [
        Bundle("a", "b", waypoints=["via"]),
        Bundle("a", "c", waypoints=["via"]),
    ]
    ordering = [[["a"]], [["via"]], [["b", "c"]]]

    sdd = SankeyDefinition(nodes=nodes, bundles=bundles, ordering=ordering)
    spec = compile_sankey_definition(sdd)

    shared_edge = next(
        e for e in spec.edges if e.source == "a^*" and e.target == "via^*"
    )
    assert shared_edge.bundle_ids == [0, 1]

    edge_to_b = next(e for e in spec.edges if e.source == "via^*" and e.target == "b^*")
    assert edge_to_b.bundle_ids == [0]


# =============================================================================
# Measures tests
# =============================================================================


def test_compile_measures_string():
    """Test measures as string."""
    nodes = {
        "a": ProcessGroup(selection=["a1"]),
        "b": ProcessGroup(selection=["b1"]),
    }
    bundles = [Bundle("a", "b")]
    ordering = [[["a"]], [["b"]]]

    sdd = SankeyDefinition(nodes=nodes, bundles=bundles, ordering=ordering)
    spec = compile_sankey_definition(sdd, measures="value")

    assert len(spec.measures) == 1
    assert spec.measures[0].column == "value"
    assert spec.measures[0].aggregation == "sum"


def test_compile_measures_list():
    """Test measures as list."""
    nodes = {
        "a": ProcessGroup(selection=["a1"]),
        "b": ProcessGroup(selection=["b1"]),
    }
    bundles = [Bundle("a", "b")]
    ordering = [[["a"]], [["b"]]]

    sdd = SankeyDefinition(nodes=nodes, bundles=bundles, ordering=ordering)
    spec = compile_sankey_definition(sdd, measures=["value", "cost"])

    assert len(spec.measures) == 2
    assert spec.measures[0].column == "value"
    assert spec.measures[0].aggregation == "sum"
    assert spec.measures[1].column == "cost"
    assert spec.measures[1].aggregation == "sum"


def test_compile_measures_dict():
    """Test measures as dict with aggregation functions."""
    nodes = {
        "a": ProcessGroup(selection=["a1"]),
        "b": ProcessGroup(selection=["b1"]),
    }
    bundles = [Bundle("a", "b")]
    ordering = [[["a"]], [["b"]]]

    sdd = SankeyDefinition(nodes=nodes, bundles=bundles, ordering=ordering)
    spec = compile_sankey_definition(
        sdd, measures={"value": "sum", "intensity": "mean"}
    )

    assert len(spec.measures) == 2
    measure_dict = {m.column: m.aggregation for m in spec.measures}
    assert measure_dict["value"] == "sum"
    assert measure_dict["intensity"] == "mean"


def test_compile_measures_callable_raises():
    """Test that callable measures raise an error."""
    nodes = {
        "a": ProcessGroup(selection=["a1"]),
        "b": ProcessGroup(selection=["b1"]),
    }
    bundles = [Bundle("a", "b")]
    ordering = [[["a"]], [["b"]]]

    sdd = SankeyDefinition(nodes=nodes, bundles=bundles, ordering=ordering)

    with pytest.raises(ValueError, match="callable measures not supported"):
        compile_sankey_definition(sdd, measures=lambda x: x)


# =============================================================================
# Display and color tests
# =============================================================================


def test_compile_link_width_default():
    """Test default link_width uses first measure."""
    nodes = {
        "a": ProcessGroup(selection=["a1"]),
        "b": ProcessGroup(selection=["b1"]),
    }
    bundles = [Bundle("a", "b")]
    ordering = [[["a"]], [["b"]]]

    sdd = SankeyDefinition(nodes=nodes, bundles=bundles, ordering=ordering)
    spec = compile_sankey_definition(sdd, measures="value")

    assert spec.display.link_width == "value"


def test_compile_link_width_explicit():
    """Test explicit link_width."""
    nodes = {
        "a": ProcessGroup(selection=["a1"]),
        "b": ProcessGroup(selection=["b1"]),
    }
    bundles = [Bundle("a", "b")]
    ordering = [[["a"]], [["b"]]]

    sdd = SankeyDefinition(nodes=nodes, bundles=bundles, ordering=ordering)
    spec = compile_sankey_definition(sdd, measures=["value", "cost"], link_width="cost")

    assert spec.display.link_width == "cost"


def test_compile_categorical_color_default():
    """Test default categorical color by type."""
    nodes = {
        "a": ProcessGroup(selection=["a1"]),
        "b": ProcessGroup(selection=["b1"]),
    }
    bundles = [Bundle("a", "b")]
    ordering = [[["a"]], [["b"]]]

    sdd = SankeyDefinition(nodes=nodes, bundles=bundles, ordering=ordering)
    spec = compile_sankey_definition(sdd)

    assert isinstance(spec.display.link_color, CategoricalColorSpec)
    assert spec.display.link_color.attribute == "type"


def test_compile_categorical_color_explicit():
    """Test explicit categorical color scale."""
    nodes = {
        "a": ProcessGroup(selection=["a1"]),
        "b": ProcessGroup(selection=["b1"]),
    }
    bundles = [Bundle("a", "b")]
    ordering = [[["a"]], [["b"]]]
    flow_partition = Partition.Simple("material", ["m", "n"])

    sdd = SankeyDefinition(
        nodes=nodes, bundles=bundles, ordering=ordering, flow_partition=flow_partition
    )
    scale = CategoricalScale("type", palette=["#ff0000", "#00ff00"])
    spec = compile_sankey_definition(sdd, link_color=scale)

    assert isinstance(spec.display.link_color, CategoricalColorSpec)
    # Lookup should include colors for types
    assert "m" in spec.display.link_color.lookup
    assert "n" in spec.display.link_color.lookup


def test_compile_categorical_color_string():
    """Test categorical color from string attribute."""
    nodes = {
        "a": ProcessGroup(selection=["a1"]),
        "b": ProcessGroup(selection=["b1"]),
    }
    bundles = [Bundle("a", "b")]
    ordering = [[["a"]], [["b"]]]

    sdd = SankeyDefinition(nodes=nodes, bundles=bundles, ordering=ordering)
    spec = compile_sankey_definition(sdd, link_color="source")

    assert isinstance(spec.display.link_color, CategoricalColorSpec)
    assert spec.display.link_color.attribute == "source"


def test_compile_quantitative_color():
    """Test quantitative color scale."""
    nodes = {
        "a": ProcessGroup(selection=["a1"]),
        "b": ProcessGroup(selection=["b1"]),
    }
    bundles = [Bundle("a", "b")]
    ordering = [[["a"]], [["b"]]]

    sdd = SankeyDefinition(nodes=nodes, bundles=bundles, ordering=ordering)
    scale = QuantitativeScale("value", domain=(0, 100))
    spec = compile_sankey_definition(sdd, link_color=scale)

    assert isinstance(spec.display.link_color, QuantitativeColorSpec)
    assert spec.display.link_color.attribute == "value"
    assert spec.display.link_color.domain == (0, 100)
    assert len(spec.display.link_color.palette) == 9  # Default samples


# =============================================================================
# JSON serialization tests
# =============================================================================


def test_compile_spec_to_json():
    """Test that compiled spec can be serialized to JSON."""
    nodes = {
        "a": ProcessGroup(selection=["a1"]),
        "b": ProcessGroup(selection=["b1"]),
    }
    bundles = [Bundle("a", "b")]
    ordering = [[["a"]], [["b"]]]

    sdd = SankeyDefinition(nodes=nodes, bundles=bundles, ordering=ordering)
    spec = compile_sankey_definition(sdd)

    json_data = spec.to_json()

    assert json_data["version"] == "2.0"
    assert "nodes" in json_data
    assert "edges" in json_data
    assert "measures" in json_data
    assert "display" in json_data


def test_compile_spec_roundtrip():
    """Test that spec can be serialized and deserialized."""
    partition = Partition.Simple("material", ["m", "n"])
    nodes = {
        "a": ProcessGroup(selection=["a1"]),
        "via": Waypoint(partition=partition),
        "b": ProcessGroup(selection=["b1"]),
    }
    bundles = [Bundle("a", "b", waypoints=["via"])]
    ordering = [[["a"]], [["via"]], [["b"]]]

    sdd = SankeyDefinition(
        nodes=nodes,
        bundles=bundles,
        ordering=ordering,
        flow_partition=Partition.Simple("type", ["x", "y"]),
    )
    spec = compile_sankey_definition(sdd, measures=["value", "cost"])

    # Roundtrip
    json_data = spec.to_json()
    spec2 = WeaverSpec.from_json(json_data)

    assert spec2.version == spec.version
    assert set(spec2.nodes.keys()) == set(spec.nodes.keys())
    assert len(spec2.edges) == len(spec.edges)
    assert len(spec2.measures) == len(spec.measures)
