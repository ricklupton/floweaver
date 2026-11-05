"""Tests for weave_table: tabulating the flows shown in a Sankey diagram."""

import pandas as pd
import pytest

from floweaver import (
    SankeyDefinition,
    ProcessGroup,
    Waypoint,
    Bundle,
    Partition,
    Elsewhere,
    Dataset,
    Group,
    weave_table,
    weave_compiled,
    compile_sankey_definition,
    execute_weave_table,
)
from floweaver.compiler.spec import WeaverSpec

KEY_COLUMNS = [
    "source",
    "source_subgroup",
    "via",
    "target",
    "target_subgroup",
    "type",
    "time",
]


def make_flows(records):
    return pd.DataFrame.from_records(
        records, columns=["source", "target", "material", "value"]
    )


def rows(table, measure="value"):
    """Table rows as a set of tuples, for order-independent comparison."""
    return {
        tuple(r)
        for r in table[KEY_COLUMNS + [measure]].itertuples(index=False, name=None)
    }


# A simple supply chain used by several tests:
#
#   feedstocks --> Refining --> Manufacturing --> landfill
#                     ^                |
#                     +-- Recycling <--+
FLOWS = make_flows(
    [
        ("crude", "refinery", "oil", 10),
        ("forest", "refinery", "wood", 5),
        ("grid", "refinery", "electricity", 2),
        ("refinery", "factory_a", "oil", 6),
        ("refinery", "factory_b", "wood", 4),
        ("factory_a", "landfill", "oil", 3),
        ("factory_b", "landfill", "oil", 1),
        ("recycler", "refinery", "scrap", 1),
    ]
)


# =============================================================================
# Basic structure
# =============================================================================


def test_columns():
    nodes = {
        "Refining": ProcessGroup(["refinery"], title="Refining"),
        "Manufacturing": ProcessGroup(["factory_a", "factory_b"]),
    }
    sdd = SankeyDefinition(
        nodes, [Bundle("Refining", "Manufacturing")], [["Refining"], ["Manufacturing"]]
    )
    table = weave_table(sdd, FLOWS)
    assert list(table.columns) == KEY_COLUMNS + ["value"]


def test_simple_bundle_uses_title_or_id():
    nodes = {
        "Refining": ProcessGroup(["refinery"], title="Oil refining"),
        "Manufacturing": ProcessGroup(["factory_a", "factory_b"]),  # no title
    }
    sdd = SankeyDefinition(
        nodes, [Bundle("Refining", "Manufacturing")], [["Refining"], ["Manufacturing"]]
    )
    table = weave_table(sdd, FLOWS)
    table = table[table.source == "Oil refining"]
    assert rows(table) == {
        ("Oil refining", "", "", "Manufacturing", "", "", "", 10),
    }


def test_accepts_dataset():
    nodes = {
        "Refining": ProcessGroup(["refinery"]),
        "Manufacturing": ProcessGroup(["factory_a", "factory_b"]),
    }
    sdd = SankeyDefinition(
        nodes, [Bundle("Refining", "Manufacturing")], [["Refining"], ["Manufacturing"]]
    )
    pd.testing.assert_frame_equal(
        weave_table(sdd, FLOWS), weave_table(sdd, Dataset(FLOWS))
    )


def test_empty_result():
    nodes = {
        "Refining": ProcessGroup(["refinery"]),
        "Manufacturing": ProcessGroup(["factory_a"]),
    }
    sdd = SankeyDefinition(
        nodes, [Bundle("Refining", "Manufacturing")], [["Refining"], ["Manufacturing"]]
    )
    table = weave_table(sdd, make_flows([("x", "y", "oil", 1)]))
    assert len(table) == 0
    assert list(table.columns) == KEY_COLUMNS + ["value"]


# =============================================================================
# Subgroups
# =============================================================================


def test_partitioned_process_groups():
    nodes = {
        "Refining": ProcessGroup(["refinery"]),
        "Manufacturing": ProcessGroup(
            ["factory_a", "factory_b"],
            Partition.Simple("process", [("Plant A", ["factory_a"]), "factory_b"]),
        ),
    }
    sdd = SankeyDefinition(
        nodes, [Bundle("Refining", "Manufacturing")], [["Refining"], ["Manufacturing"]]
    )
    table = weave_table(sdd, FLOWS)
    table = table[table.source == "Refining"]
    assert rows(table) == {
        ("Refining", "", "", "Manufacturing", "Plant A", "", "", 6),
        ("Refining", "", "", "Manufacturing", "factory_b", "", "", 4),
    }


def test_catch_all_subgroup_is_labelled_other():
    nodes = {
        "Refining": ProcessGroup(["refinery"]),
        "Manufacturing": ProcessGroup(
            ["factory_a", "factory_b"],
            Partition.Simple("process", [("Plant A", ["factory_a"])]),
        ),
    }
    sdd = SankeyDefinition(
        nodes, [Bundle("Refining", "Manufacturing")], [["Refining"], ["Manufacturing"]]
    )
    table = weave_table(sdd, FLOWS)
    table = table[table.source == "Refining"]
    assert rows(table) == {
        ("Refining", "", "", "Manufacturing", "Plant A", "", "", 6),
        ("Refining", "", "", "Manufacturing", "(other)", "", "", 4),
    }


def test_blank_partition_labels_fall_back_to_selected_values():
    # Blank labels are sometimes used to hide labels in the diagram; the table
    # still needs to tell the subgroups apart.
    nodes = {
        "Refining": ProcessGroup(["refinery"]),
        "Manufacturing": ProcessGroup(
            ["factory_a", "factory_b", "factory_c"],
            Partition.Simple(
                "process", [(" ", ["factory_a"]), ("  ", ["factory_b", "factory_c"])]
            ),
        ),
    }
    sdd = SankeyDefinition(
        nodes, [Bundle("Refining", "Manufacturing")], [["Refining"], ["Manufacturing"]]
    )
    table = weave_table(sdd, FLOWS)
    table = table[table.source == "Refining"]
    assert rows(table) == {
        ("Refining", "", "", "Manufacturing", "factory_a", "", "", 6),
        ("Refining", "", "", "Manufacturing", "factory_b, factory_c", "", "", 4),
    }


# =============================================================================
# Flow type and time
# =============================================================================


def test_flow_partition_type_and_catch_all():
    nodes = {
        "Refining": ProcessGroup(["refinery"]),
        "Manufacturing": ProcessGroup(["factory_a", "factory_b"]),
    }
    flows = make_flows(
        [
            ("refinery", "factory_a", "oil", 6),
            ("refinery", "factory_b", "wood", 4),
            ("refinery", "factory_b", "steam", 2),
        ]
    )
    sdd = SankeyDefinition(
        nodes,
        [Bundle("Refining", "Manufacturing")],
        [["Refining"], ["Manufacturing"]],
        flow_partition=Partition.Simple("material", ["oil", "wood"]),
    )
    table = weave_table(sdd, flows)
    table = table[table.source == "Refining"]
    assert rows(table) == {
        ("Refining", "", "", "Manufacturing", "", "oil", "", 6),
        ("Refining", "", "", "Manufacturing", "", "wood", "", 4),
        ("Refining", "", "", "Manufacturing", "", "(other)", "", 2),
    }


def test_time_partition():
    nodes = {
        "Refining": ProcessGroup(["refinery"]),
        "Manufacturing": ProcessGroup(["factory_a"]),
    }
    flows = pd.DataFrame.from_records(
        [
            ("refinery", "factory_a", "oil", "2020", 6),
            ("refinery", "factory_a", "oil", "2021", 7),
        ],
        columns=["source", "target", "material", "time", "value"],
    )
    sdd = SankeyDefinition(
        nodes,
        [Bundle("Refining", "Manufacturing")],
        [["Refining"], ["Manufacturing"]],
        time_partition=Partition.Simple("time", ["2020", "2021"]),
    )
    table = weave_table(sdd, flows)
    table = table[table.source == "Refining"]
    assert set(zip(table.time, table.value)) == {("2020", 6), ("2021", 7)}


# =============================================================================
# Waypoints and `via`
# =============================================================================


def test_inflow_via_untitled_partitioned_waypoint():
    # Only the partition labels of the waypoint are visible in the diagram.
    nodes = {
        "feedstocks": Waypoint(
            Partition.Simple("source", [("Fossil", ["crude"]), ("Bio", ["forest"])])
        ),
        "Refining": ProcessGroup(["refinery"]),
    }
    bundles = [
        Bundle(
            Elsewhere,
            "Refining",
            waypoints=["feedstocks"],
            flow_selection="material in ['oil', 'wood']",
        )
    ]
    sdd = SankeyDefinition(nodes, bundles, [["feedstocks"], ["Refining"]])
    table = weave_table(sdd, FLOWS)
    table = table[table.target == "Refining"]
    assert rows(table) == {
        ("(elsewhere)", "", "Fossil", "Refining", "", "", "", 10),
        ("(elsewhere)", "", "Bio", "Refining", "", "", "", 5),
    }


def test_titled_partitioned_waypoint_shows_title_and_label():
    nodes = {
        "feedstocks": Waypoint(
            Partition.Simple("source", [("Fossil", ["crude"]), ("Bio", ["forest"])]),
            title="Feedstocks",
        ),
        "Refining": ProcessGroup(["refinery"]),
    }
    bundles = [
        Bundle(
            Elsewhere,
            "Refining",
            waypoints=["feedstocks"],
            flow_selection="material in ['oil', 'wood']",
        )
    ]
    sdd = SankeyDefinition(nodes, bundles, [["feedstocks"], ["Refining"]])
    table = weave_table(sdd, FLOWS)
    assert set(table[table.target == "Refining"].via) == {
        "Feedstocks: Fossil",
        "Feedstocks: Bio",
    }


def test_untitled_waypoints_are_omitted_from_via():
    # A titled waypoint followed by an untitled spacer used for layout
    nodes = {
        "other_inputs": Waypoint(title="Other inputs"),
        "spacer": Waypoint(title=""),
        "Refining": ProcessGroup(["refinery"]),
    }
    bundles = [
        Bundle(
            Elsewhere,
            "Refining",
            waypoints=["other_inputs", "spacer"],
            flow_selection="material == 'electricity'",
        )
    ]
    sdd = SankeyDefinition(nodes, bundles, [["other_inputs"], ["spacer"], ["Refining"]])
    table = weave_table(sdd, FLOWS)
    table = table[table.target == "Refining"]
    assert rows(table) == {
        ("(elsewhere)", "", "Other inputs", "Refining", "", "", "", 2),
    }


def test_waypoint_without_title_shows_id():
    # Like an unpartitioned ProcessGroup, a Waypoint with title=None displays
    # its id in the diagram.
    nodes = {
        "Manufacturing": ProcessGroup(["factory_a", "factory_b"]),
        "Waste": Waypoint(),
    }
    bundles = [Bundle("Manufacturing", Elsewhere, waypoints=["Waste"])]
    sdd = SankeyDefinition(nodes, bundles, [["Manufacturing"], ["Waste"]])
    table = weave_table(sdd, FLOWS)
    table = table[table.source == "Manufacturing"]
    assert rows(table) == {
        ("Manufacturing", "", "Waste", "(elsewhere)", "", "", "", 4),
    }


def test_outflow_via_chain_of_waypoints():
    # Several untitled waypoints for layout, then a titled one at the end
    nodes = {
        "Manufacturing": ProcessGroup(["factory_a", "factory_b"]),
        "spacer1": Waypoint(title=""),
        "spacer2": Waypoint(title=""),
        "losses": Waypoint(title="Losses"),
    }
    bundles = [
        Bundle("Manufacturing", Elsewhere, waypoints=["spacer1", "spacer2", "losses"])
    ]
    sdd = SankeyDefinition(
        nodes, bundles, [["Manufacturing"], ["spacer1"], ["spacer2"], ["losses"]]
    )
    table = weave_table(sdd, FLOWS)
    table = table[table.source == "Manufacturing"]
    assert rows(table) == {
        ("Manufacturing", "", "Losses", "(elsewhere)", "", "", "", 4),
    }


def test_backward_loop_via_untitled_waypoints():
    nodes = {
        "Refining": ProcessGroup(["refinery"]),
        "Recycling": ProcessGroup(["recycler"]),
        "back1": Waypoint(title="", direction="L"),
        "back2": Waypoint(title="", direction="L"),
    }
    bundles = [Bundle("Recycling", "Refining", waypoints=["back2", "back1"])]
    ordering = [[["Refining"], []], [[], ["back1"]], [["Recycling"], ["back2"]]]
    sdd = SankeyDefinition(nodes, bundles, ordering)
    table = weave_table(sdd, FLOWS)
    table = table[table.source == "Recycling"]
    assert rows(table) == {
        ("Recycling", "", "", "Refining", "", "", "", 1),
    }


def test_bundle_from_group_back_to_itself():
    nodes = {
        "Manufacturing": ProcessGroup(
            ["factory_a", "factory_b"],
            Partition.Simple("process", ["factory_a", "factory_b"]),
        ),
        "Losses": ProcessGroup(["landfill"]),
        "internal": Waypoint(title="Internal reuse", direction="L"),
    }
    bundles = [
        Bundle("Manufacturing", "Losses"),
        Bundle(
            "Manufacturing",
            "Manufacturing",
            waypoints=["internal"],
            flow_selection="material == 'scrap'",
        ),
    ]
    flows = make_flows(
        [
            ("factory_a", "landfill", "oil", 3),
            ("factory_a", "factory_b", "scrap", 2),
            ("factory_b", "factory_a", "scrap", 1),
        ]
    )
    ordering = [[["Manufacturing"], []], [["Losses"], ["internal"]]]
    table = weave_table(SankeyDefinition(nodes, bundles, ordering), flows)
    assert rows(table) == {
        ("Manufacturing", "factory_a", "", "Losses", "", "", "", 3),
        (
            "Manufacturing",
            "factory_a",
            "Internal reuse",
            "Manufacturing",
            "factory_b",
            "",
            "",
            2,
        ),
        (
            "Manufacturing",
            "factory_b",
            "Internal reuse",
            "Manufacturing",
            "factory_a",
            "",
            "",
            1,
        ),
    }


def test_waypoint_with_blank_partition_labels_omitted_from_via():
    # Blank waypoint labels are not visible in the diagram, so are not listed.
    nodes = {
        "Refining": ProcessGroup(["refinery"]),
        "Manufacturing": ProcessGroup(["factory_a", "factory_b"]),
        "split": Waypoint(
            Partition.Simple("material", [(" ", ["oil"]), ("  ", ["wood"])])
        ),
    }
    bundles = [Bundle("Refining", "Manufacturing", waypoints=["split"])]
    sdd = SankeyDefinition(nodes, bundles, [["Refining"], ["split"], ["Manufacturing"]])
    table = weave_table(sdd, FLOWS)
    table = table[table.source == "Refining"]
    assert rows(table) == {
        ("Refining", "", "", "Manufacturing", "", "", "", 10),
    }


def test_visible_intermediate_waypoint_listed_in_via():
    nodes = {
        "Refining": ProcessGroup(["refinery"]),
        "Manufacturing": ProcessGroup(["factory_a", "factory_b"]),
        "transport": Waypoint(
            Partition.Simple("material", [("Pipeline", ["oil"]), ("Road", ["wood"])])
        ),
    }
    bundles = [Bundle("Refining", "Manufacturing", waypoints=["transport"])]
    sdd = SankeyDefinition(
        nodes, bundles, [["Refining"], ["transport"], ["Manufacturing"]]
    )
    table = weave_table(sdd, FLOWS)
    table = table[table.source == "Refining"]
    assert rows(table) == {
        ("Refining", "", "Pipeline", "Manufacturing", "", "", "", 6),
        ("Refining", "", "Road", "Manufacturing", "", "", "", 4),
    }


def test_multiple_visible_waypoints_in_order():
    nodes = {
        "Refining": ProcessGroup(["refinery"]),
        "Manufacturing": ProcessGroup(["factory_a", "factory_b"]),
        "port": Waypoint(title="Port"),
        "depot": Waypoint(title="Depot"),
    }
    bundles = [Bundle("Refining", "Manufacturing", waypoints=["port", "depot"])]
    sdd = SankeyDefinition(
        nodes, bundles, [["Refining"], ["port"], ["depot"], ["Manufacturing"]]
    )
    table = weave_table(sdd, FLOWS)
    assert list(table[table.source == "Refining"].via) == ["Port; Depot"]


def test_layer_spanning_bundle_default_partition_is_visible():
    # Waypoints added automatically to span layers take the Bundle's
    # default_partition, whose labels are visible in the diagram.
    nodes = {
        "Refining": ProcessGroup(["refinery"]),
        "Manufacturing": ProcessGroup(["factory_a", "factory_b"]),
    }
    bundles = [
        Bundle(
            "Refining",
            "Manufacturing",
            default_partition=Partition.Simple("material", ["oil", "wood"]),
        )
    ]
    sdd = SankeyDefinition(nodes, bundles, [["Refining"], [], ["Manufacturing"]])
    table = weave_table(sdd, FLOWS)
    table = table[table.source == "Refining"]
    assert rows(table) == {
        ("Refining", "", "oil", "Manufacturing", "", "", "", 6),
        ("Refining", "", "wood", "Manufacturing", "", "", "", 4),
    }


# =============================================================================
# Elsewhere
# =============================================================================


def test_implicit_elsewhere_waypoints_omitted():
    # The implicit bundles to/from Elsewhere are drawn with arrows, not labels
    nodes = {"Refining": ProcessGroup(["refinery"])}
    sdd = SankeyDefinition(nodes, [], [["Refining"]])
    table = weave_table(sdd, FLOWS)
    assert set(table.via) == {""}
    assert set(table.source[table.target == "Refining"]) == {"(elsewhere)"}


def test_elsewhere_stubs_without_waypoints():
    nodes = {
        "Refining": ProcessGroup(["refinery"]),
        "Manufacturing": ProcessGroup(["factory_a", "factory_b"]),
    }
    bundles = [Bundle("Manufacturing", Elsewhere)]
    sdd = SankeyDefinition(nodes, bundles, [["Refining"], ["Manufacturing"]])
    table = weave_table(sdd, FLOWS)
    table = table[table.source == "Manufacturing"]
    assert rows(table) == {
        ("Manufacturing", "", "", "(elsewhere)", "", "", "", 4),
    }


def test_elsewhere_pair_merged_into_one_row():
    # A flow between two ProcessGroups with no Bundle between them is drawn as
    # an outflow to Elsewhere and an inflow from Elsewhere. In the table it
    # becomes one row, with "(elsewhere)" in `via`.
    nodes = {
        "Refining": ProcessGroup(["refinery"]),
        "Recycling": ProcessGroup(["recycler"]),
        "exports": Waypoint(title="Exports"),
        "imports": Waypoint(title="Imports"),
    }
    flows = make_flows([("refinery", "recycler", "scrap", 7)])
    bundles = [
        Bundle("Refining", Elsewhere, waypoints=["exports"]),
        Bundle(Elsewhere, "Recycling", waypoints=["imports"]),
    ]
    sdd = SankeyDefinition(
        nodes, bundles, [["imports", "Refining"], ["exports", "Recycling"]]
    )
    table = weave_table(sdd, flows)
    assert rows(table) == {
        ("Refining", "", "Exports; (elsewhere); Imports", "Recycling", "", "", "", 7),
    }


def test_elsewhere_pair_with_implicit_bundles():
    nodes = {
        "Refining": ProcessGroup(["refinery"]),
        "Recycling": ProcessGroup(["recycler"]),
    }
    flows = make_flows([("refinery", "recycler", "scrap", 7)])
    sdd = SankeyDefinition(nodes, [], [["Refining"], ["Recycling"]])
    table = weave_table(sdd, flows)
    assert rows(table) == {
        ("Refining", "", "(elsewhere)", "Recycling", "", "", "", 7),
    }


# =============================================================================
# Merging and measures
# =============================================================================


def test_rows_merged_across_bundles():
    # Two bundles that look the same in the diagram give one row
    nodes = {
        "other_inputs": Waypoint(title="Other inputs"),
        "Refining": ProcessGroup(["refinery"]),
        "Manufacturing": ProcessGroup(["factory_a", "factory_b"]),
    }
    flows = make_flows(
        [
            ("grid", "refinery", "electricity", 2),
            ("boiler", "refinery", "steam", 3),
        ]
    )
    bundles = [
        Bundle(
            Elsewhere,
            "Refining",
            waypoints=["other_inputs"],
            flow_selection="material == 'electricity'",
        ),
        Bundle(
            Elsewhere,
            "Refining",
            waypoints=["other_inputs"],
            flow_selection="material == 'steam'",
        ),
    ]
    sdd = SankeyDefinition(
        nodes, bundles, [["other_inputs"], ["Refining"], ["Manufacturing"]]
    )
    table = weave_table(sdd, flows)
    assert rows(table) == {
        ("(elsewhere)", "", "Other inputs", "Refining", "", "", "", 5),
    }


def test_multiple_and_mean_measures():
    nodes = {
        "Refining": ProcessGroup(["refinery"]),
        "Manufacturing": ProcessGroup(["factory_a", "factory_b"]),
    }
    flows = pd.DataFrame.from_records(
        [
            ("refinery", "factory_a", "oil", 6, 1.0),
            ("refinery", "factory_b", "oil", 4, 3.0),
        ],
        columns=["source", "target", "material", "value", "price"],
    )
    sdd = SankeyDefinition(
        nodes, [Bundle("Refining", "Manufacturing")], [["Refining"], ["Manufacturing"]]
    )
    table = weave_table(sdd, flows, measures={"value": "sum", "price": "mean"})
    assert list(table.columns) == KEY_COLUMNS + ["value", "price"]
    row = table[table.source == "Refining"].iloc[0]
    assert row["value"] == 10
    assert row["price"] == 2.0


# =============================================================================
# Consistency with the diagram
# =============================================================================


def supply_chain_sdd():
    """A diagram combining most of the features above."""
    nodes = {
        "feedstocks": Waypoint(
            Partition.Simple("source", [("Fossil", ["crude"]), ("Bio", ["forest"])])
        ),
        "other_inputs": Waypoint(title="Other inputs"),
        "spacer": Waypoint(title=""),
        "Refining": ProcessGroup(["refinery"], title="Refining"),
        "Manufacturing": ProcessGroup(
            ["factory_a", "factory_b"],
            Partition.Simple("process", [(" ", ["factory_a"]), ("  ", ["factory_b"])]),
        ),
        "Recycling": ProcessGroup(["recycler"]),
        "losses": Waypoint(title="Losses"),
        "back1": Waypoint(title="", direction="L"),
        "back2": Waypoint(title="", direction="L"),
    }
    bundles = [
        Bundle(
            Elsewhere,
            "Refining",
            waypoints=["feedstocks"],
            flow_selection="material in ['oil', 'wood']",
        ),
        Bundle(
            Elsewhere,
            "Refining",
            waypoints=["other_inputs", "spacer"],
            flow_selection="material == 'electricity'",
        ),
        Bundle("Refining", "Manufacturing"),
        Bundle("Manufacturing", Elsewhere, waypoints=["losses"]),
        Bundle("Recycling", "Refining", waypoints=["back2", "back1"]),
    ]
    ordering = [
        [["feedstocks", "other_inputs"], []],
        [["spacer"], []],
        [["Refining"], []],
        [["Manufacturing"], ["back1"]],
        [["losses"], ["Recycling", "back2"]],
    ]
    return SankeyDefinition(
        nodes,
        bundles,
        ordering,
        flow_partition=Partition.Simple("material", ["oil", "wood"]),
    )


SUPPLY_CHAIN_FLOWS = make_flows(
    [
        ("crude", "refinery", "oil", 10),
        ("forest", "refinery", "wood", 5),
        ("grid", "refinery", "electricity", 2),
        ("refinery", "factory_a", "oil", 6),
        ("refinery", "factory_b", "wood", 4),
        ("factory_a", "landfill", "oil", 3),
        ("factory_b", "landfill", "wood", 1),
        ("recycler", "refinery", "scrap", 1),
        ("refinery", "recycler", "scrap", 7),  # Elsewhere pair
    ]
)


def test_supply_chain_table():
    table = weave_table(supply_chain_sdd(), SUPPLY_CHAIN_FLOWS)
    assert rows(table) == {
        ("(elsewhere)", "", "Fossil", "Refining", "", "oil", "", 10),
        ("(elsewhere)", "", "Bio", "Refining", "", "wood", "", 5),
        ("(elsewhere)", "", "Other inputs", "Refining", "", "(other)", "", 2),
        ("Refining", "", "", "Manufacturing", "factory_a", "oil", "", 6),
        ("Refining", "", "", "Manufacturing", "factory_b", "wood", "", 4),
        ("Manufacturing", "factory_a", "Losses", "(elsewhere)", "", "oil", "", 3),
        ("Manufacturing", "factory_b", "Losses", "(elsewhere)", "", "wood", "", 1),
        ("Recycling", "", "", "Refining", "", "(other)", "", 1),
        ("Refining", "", "(elsewhere)", "Recycling", "", "(other)", "", 7),
    }


def test_process_group_totals_match_diagram():
    sdd = supply_chain_sdd()
    table = weave_table(sdd, SUPPLY_CHAIN_FLOWS)
    sankey = weave_compiled(sdd, SUPPLY_CHAIN_FLOWS)

    def diagram_totals(group_id):
        prefix = group_id + "^"
        inflow = sum(
            link.link_width for link in sankey.links if link.target.startswith(prefix)
        )
        outflow = sum(
            link.link_width for link in sankey.links if link.source.startswith(prefix)
        )
        for node in sankey.nodes:
            if node.id.startswith(prefix):
                inflow += sum(link.link_width for link in node.from_elsewhere_links)
                outflow += sum(link.link_width for link in node.to_elsewhere_links)
        return inflow, outflow

    for group_id, label in [
        ("Refining", "Refining"),
        ("Manufacturing", "Manufacturing"),
        ("Recycling", "Recycling"),
    ]:
        table_inflow = table.value[table.target == label].sum()
        table_outflow = table.value[table.source == label].sum()
        assert (table_inflow, table_outflow) == diagram_totals(group_id), group_id


def test_each_flow_counted_once():
    table = weave_table(supply_chain_sdd(), SUPPLY_CHAIN_FLOWS)
    assert table.value.sum() == SUPPLY_CHAIN_FLOWS.value.sum()


# =============================================================================
# Compiled spec
# =============================================================================


def test_execute_from_json_spec():
    spec = compile_sankey_definition(supply_chain_sdd())
    spec2 = WeaverSpec.from_json(spec.to_json())
    pd.testing.assert_frame_equal(
        execute_weave_table(spec, SUPPLY_CHAIN_FLOWS),
        execute_weave_table(spec2, SUPPLY_CHAIN_FLOWS),
    )


def test_node_spec_values():
    spec = compile_sankey_definition(supply_chain_sdd())
    # Partitioned nodes record the values selected by their partition group
    assert spec.nodes["feedstocks^Fossil"].values == ["crude"]
    assert spec.nodes["feedstocks^Bio"].values == ["forest"]
    # Unpartitioned and catch-all nodes have none
    assert spec.nodes["Refining^*"].values is None
    assert spec.nodes["feedstocks^_"].values is None
    # Only serialised when present
    assert spec.nodes["feedstocks^Fossil"].to_json()["values"] == ["crude"]
    assert "values" not in spec.nodes["Refining^*"].to_json()


def test_node_spec_values_multiple_dimensions():
    partition = Partition(
        [
            # Group with a query on two dimensions
            Group("Oil from A", [("process", ("factory_a",)), ("material", ("oil",))])
        ]
    )
    nodes = {
        "Refining": ProcessGroup(["refinery"]),
        "Manufacturing": ProcessGroup(["factory_a", "factory_b"], partition),
    }
    sdd = SankeyDefinition(
        nodes, [Bundle("Refining", "Manufacturing")], [["Refining"], ["Manufacturing"]]
    )
    spec = compile_sankey_definition(sdd)
    assert spec.nodes["Manufacturing^Oil from A"].values == ["factory_a", "oil"]


@pytest.mark.parametrize("bad_label", ["", "   "])
def test_blank_process_group_title_falls_back_to_id(bad_label):
    nodes = {
        "Refining": ProcessGroup(["refinery"], title=bad_label),
        "Manufacturing": ProcessGroup(["factory_a", "factory_b"]),
    }
    sdd = SankeyDefinition(
        nodes, [Bundle("Refining", "Manufacturing")], [["Refining"], ["Manufacturing"]]
    )
    table = weave_table(sdd, FLOWS)
    assert "Refining" in set(table.source)
