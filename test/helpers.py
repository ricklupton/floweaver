"""Shared test helper functions for SankeyData comparison.

This module provides utilities for comparing SankeyData objects in tests,
with optional tolerance for known improvements in new implementations.
"""

import numpy as np
from floweaver.sankey_data import SankeyData, SankeyNode, SankeyLink
from floweaver.ordering import Ordering


def _links_dict(links):
    """Create dict of links keyed by (source, target, type, time)."""
    return {(link.source, link.target, link.type, link.time): link for link in links}


def assert_sankey_data_equivalent(
    actual, expected, *, allow_known_improvements=False, rtol=1e-14
):
    """Compare two SankeyData objects with detailed assertion messages.

    Args:
        actual: The SankeyData to check
        expected: The expected SankeyData reference
        allow_known_improvements: If True, tolerate known improvements in actual vs expected:
            - Accept correct hidden=True for catch-all partition nodes (label='_')
            - Accept deduplication of flows in elsewhere bundles
        rtol: Relative tolerance for floating point comparisons
    """
    # Compare ordering
    assert actual.ordering == expected.ordering, (
        f"Ordering mismatch: {actual.ordering} != {expected.ordering}"
    )

    # Compare nodes (order-independent)
    actual_nodes_sorted = sorted(actual.nodes, key=lambda n: n.id)
    expected_nodes_sorted = sorted(expected.nodes, key=lambda n: n.id)
    assert len(actual_nodes_sorted) == len(expected_nodes_sorted), (
        f"Node count mismatch: {len(actual_nodes_sorted)} != {len(expected_nodes_sorted)}"
    )

    for actual_node, expected_node in zip(actual_nodes_sorted, expected_nodes_sorted):
        assert actual_node.id == expected_node.id, (
            f"Node id mismatch: {actual_node.id} != {expected_node.id}"
        )
        assert actual_node.title == expected_node.title, (
            f"Node title mismatch for {actual_node.id}: "
            f"{actual_node.title} != {expected_node.title}"
        )
        assert actual_node.direction == expected_node.direction, (
            f"Node direction mismatch for {actual_node.id}: "
            f"{actual_node.direction} != {expected_node.direction}"
        )

        # Check hidden attribute with optional tolerance
        if actual_node.hidden != expected_node.hidden:
            if allow_known_improvements and actual_node.id.endswith("^_"):
                # New implementation correctly sets hidden=True for catch-all partition
                # nodes (label='_'), while old defaults to False
                assert actual_node.hidden and not expected_node.hidden, (
                    f"Unexpected hidden values for {actual_node.id}: "
                    f"actual={actual_node.hidden}, expected={expected_node.hidden}"
                )
            else:
                raise AssertionError(
                    f"Node hidden mismatch for {actual_node.id}: "
                    f"{actual_node.hidden} != {expected_node.hidden}"
                )

        assert actual_node.style == expected_node.style, (
            f"Node style mismatch for {actual_node.id}: "
            f"{actual_node.style} != {expected_node.style}"
        )

        # Compare elsewhere links
        assert len(actual_node.from_elsewhere_links) == len(
            expected_node.from_elsewhere_links
        ), (
            f"from_elsewhere_links count mismatch for {actual_node.id}: "
            f"{len(actual_node.from_elsewhere_links)} != "
            f"{len(expected_node.from_elsewhere_links)}"
        )
        assert len(actual_node.to_elsewhere_links) == len(
            expected_node.to_elsewhere_links
        ), (
            f"to_elsewhere_links count mismatch for {actual_node.id}: "
            f"{len(actual_node.to_elsewhere_links)} != "
            f"{len(expected_node.to_elsewhere_links)}"
        )

        for actual_link, expected_link in zip(
            actual_node.from_elsewhere_links, expected_node.from_elsewhere_links
        ):
            assert actual_link.source == expected_link.source
            assert actual_link.target == expected_link.target
            assert set(actual_link.original_flows) == set(expected_link.original_flows)

            # Check link_width with optional tolerance for duplicates
            if not np.isclose(
                actual_link.link_width, expected_link.link_width, rtol=rtol
            ):
                if allow_known_improvements:
                    # Old implementation has a bug where flows can be counted multiple times
                    # when they match overlapping elsewhere bundles
                    expected_has_duplicates = len(expected_link.original_flows) > len(
                        set(expected_link.original_flows)
                    )
                    actual_has_duplicates = len(actual_link.original_flows) > len(
                        set(actual_link.original_flows)
                    )
                    assert expected_has_duplicates and not actual_has_duplicates, (
                        f"link_width mismatch not due to old duplicates: "
                        f"{actual_link.link_width} vs {expected_link.link_width}"
                    )
                else:
                    raise AssertionError(
                        f"from_elsewhere link_width mismatch for {actual_node.id}: "
                        f"{actual_link.link_width} vs {expected_link.link_width}"
                    )

        for actual_link, expected_link in zip(
            actual_node.to_elsewhere_links, expected_node.to_elsewhere_links
        ):
            assert actual_link.source == expected_link.source
            assert actual_link.target == expected_link.target
            assert set(actual_link.original_flows) == set(expected_link.original_flows)

            # Same duplicate handling as above
            if not np.isclose(
                actual_link.link_width, expected_link.link_width, rtol=rtol
            ):
                if allow_known_improvements:
                    expected_has_duplicates = len(expected_link.original_flows) > len(
                        set(expected_link.original_flows)
                    )
                    actual_has_duplicates = len(actual_link.original_flows) > len(
                        set(actual_link.original_flows)
                    )
                    assert expected_has_duplicates and not actual_has_duplicates, (
                        f"link_width mismatch not due to old duplicates: "
                        f"{actual_link.link_width} vs {expected_link.link_width}"
                    )
                else:
                    raise AssertionError(
                        f"to_elsewhere link_width mismatch for {actual_node.id}: "
                        f"{actual_link.link_width} vs {expected_link.link_width}"
                    )

    # Compare groups
    actual_groups = sorted(actual.groups, key=lambda group: group["id"])
    expected_groups = sorted(expected.groups, key=lambda group: group["id"])
    assert actual_groups == expected_groups, "Groups mismatch"

    # Compare link properties (excluding floating point values)
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

    actual_props = sorted([_link_props(link) for link in actual.links])
    expected_props = sorted([_link_props(link) for link in expected.links])
    assert actual_props == expected_props, (
        f"Link properties mismatch:\nActual: {actual_props[:3]}\n"
        f"Expected: {expected_props[:3]}"
    )

    # Compare link values and opacity with floating point tolerance
    expected_links_dict = _links_dict(expected.links)
    actual_links_dict = _links_dict(actual.links)

    assert set(expected_links_dict.keys()) == set(actual_links_dict.keys()), (
        "Link keys don't match"
    )

    for key in expected_links_dict:
        expected_link = expected_links_dict[key]
        actual_link = actual_links_dict[key]

        assert np.isclose(
            expected_link.link_width, actual_link.link_width, rtol=rtol
        ), (
            f"link_width mismatch for {key}: "
            f"{expected_link.link_width} vs {actual_link.link_width}"
        )

        assert np.isclose(expected_link.opacity, actual_link.opacity, rtol=rtol), (
            f"opacity mismatch for {key}: "
            f"{expected_link.opacity} vs {actual_link.opacity}"
        )

        for measure_key in expected_link.data:
            expected_val = expected_link.data[measure_key]
            actual_val = actual_link.data[measure_key]
            if isinstance(expected_val, (int, float, np.number)):
                assert np.isclose(expected_val, actual_val, rtol=rtol), (
                    f"data[{measure_key}] mismatch for {key}: "
                    f"{expected_val} vs {actual_val}"
                )
            else:
                assert expected_val == actual_val, (
                    f"data[{measure_key}] mismatch for {key}: "
                    f"{expected_val} vs {actual_val}"
                )


def sankey_data_from_json(json_dict):
    """Parse a JSON dictionary into a SankeyData object.

    This is the inverse of SankeyData.to_json() and is primarily used for
    testing JS executor results.

    Args:
        json_dict: Dictionary with keys 'nodes', 'links', 'ordering' (or 'order'),
                  and optionally 'groups'

    Returns:
        SankeyData object
    """
    # Parse nodes
    nodes = []
    for n in json_dict["nodes"]:
        # Parse elsewhere links if present
        from_elsewhere = []
        to_elsewhere = []

        if "from_elsewhere_links" in n:
            from_elsewhere = [
                SankeyLink(
                    source=link["source"],
                    target=link["target"],
                    type=link.get("type"),
                    time=link.get("time"),
                    link_width=link.get("link_width", link.get("value", 0.0)),
                    data=link.get("data", {"value": link.get("value", 0.0)}),
                    title=link.get("title"),
                    color=link.get("color"),
                    opacity=link.get("opacity", 1.0),
                    original_flows=link.get("original_flows", []),
                )
                for link in n["from_elsewhere_links"]
            ]

        if "to_elsewhere_links" in n:
            to_elsewhere = [
                SankeyLink(
                    source=link["source"],
                    target=link["target"],
                    type=link.get("type"),
                    time=link.get("time"),
                    link_width=link.get("link_width", link.get("value", 0.0)),
                    data=link.get("data", {"value": link.get("value", 0.0)}),
                    title=link.get("title"),
                    color=link.get("color"),
                    opacity=link.get("opacity", 1.0),
                    original_flows=link.get("original_flows", []),
                )
                for link in n["to_elsewhere_links"]
            ]

        nodes.append(
            SankeyNode(
                id=n["id"],
                title=n.get("title"),
                direction=n.get("direction", "R"),
                hidden=n.get("hidden", False),
                style=n.get("style"),
                from_elsewhere_links=from_elsewhere,
                to_elsewhere_links=to_elsewhere,
            )
        )

    # Parse links
    links = []
    for link in json_dict["links"]:
        links.append(
            SankeyLink(
                source=link["source"],
                target=link["target"],
                type=link.get("type"),
                time=link.get("time"),
                link_width=link.get("link_width", link.get("value", 0.0)),
                data=link.get("data", {"value": link.get("value", 0.0)}),
                title=link.get("title"),
                color=link.get("color"),
                opacity=link.get("opacity", 1.0),
                original_flows=link.get("original_flows", []),
            )
        )

    # Parse ordering - handle both 'ordering' and 'order' keys
    ordering_data = json_dict.get("ordering", json_dict.get("order", [[]]))
    ordering = Ordering(ordering_data)

    # Parse groups
    groups = json_dict.get("groups", [])

    return SankeyData(nodes=nodes, links=links, groups=groups, ordering=ordering)
