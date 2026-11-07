"""Functions to compile Partitions into decision trees."""

from __future__ import annotations
from typing import Literal
from dataclasses import dataclass
from collections import defaultdict

from ..partition import Partition
from .rules import Query, Rules, Includes


def expand_partition(
    partition: Partition | None,
    label_prefix: str | None = "",
    default_label: str = "_",
    process_side: Literal["source", "target"] | None = None,
) -> Rules[str]:
    """
    Convert partition to Rules including default buckets.

    The special attribute "process" is interpreted as the value of `process_side` (source or target).
    """
    if partition is None:
        rules = Rules([({}, "*")])
    else:
        # Build explicit rules
        rules = Rules(
            [
                (
                    {
                        _translate_attr(attr, process_side): Includes(values)
                        for attr, values in group.query
                    },
                    group.label,
                )
                for group in partition.groups
            ]
        )

    with_defaults = rules.refine().map(
        lambda labels: _resolve_labels(label_prefix, default_label, labels)
    )

    return with_defaults


def _translate_attr(attr: str, process_side: Literal["source", "target"] | None) -> str:
    if attr == "process" or attr.startswith("process."):
        if process_side is None:
            raise ValueError("Must specify process_side for attr 'process'")
        return process_side + attr[7:]
    return attr


def _resolve_labels(prefix: str | None, default: str, labels: list[str]) -> str | None:
    if not labels:
        return f"{prefix}{default}"
    if len(labels) == 1:
        if prefix is None:
            return None
        return f"{prefix}{labels[0]}"
    raise ValueError(f"Multiple labels for same region: {labels}")


# def explicit_values_for_attr(rules: list[tuple[Query, str]], attr: str) -> set[str]:
#     """Collect all values explicitly included for an attribute across rules."""
#     values = set()
#     for query, _ in rules:
#         match query.get(attr):
#             case Includes(values):
#                 values.update(values)
#     return values


# def restrict_rules_to_value(
#     rules: list[tuple[Query, str]], attr: str, val: str
# ) -> list[tuple[Query, str]]:
#     """
#     Filter rules to those matching attr=val, removing the constraint.

#     Returns rules that are still potentially satisfiable given attr=val,
#     with the now-redundant attr constraint removed.
#     """
#     result = []
#     for query, label in rules:
#         match query.get(attr):
#             case None:
#                 result.append((query, label))
#             case Includes(values) if val in values:
#                 result.append(({k: v for k, v in query.items() if k != attr}, label))
#     return result


# def restrict_rules_to_default(
#     rules: list[tuple[Query, str]], attr: str
# ) -> list[tuple[Query, str]]:
#     """
#     Filter rules to those matching the default branch for attr.

#     Only rules with no constraint on attr can match the default region.
#     """
#     return [(query, label) for query, label in rules if attr not in query]


# def compute_defaults(
#     rules: list[tuple[Query, str]], default_label: str
# ) -> list[tuple[Query, str]]:
#     """Compute default rules covering the complement of explicit rules."""
#     all_attrs = set()
#     for query, _ in rules:
#         all_attrs.update(query.keys())

#     return list(
#         _compute_defaults_recursive(rules, sorted(all_attrs), {}, default_label)
#     )


# def _compute_defaults_recursive(
#     rules: list[tuple[Query, str]],
#     remaining_attrs: list[str],
#     prefix: Query,
#     default_label: str,
# ):
#     """
#     Recursively find default regions by branching on each attribute.

#     Yields (Query, label) for each default region found.
#     """
#     if not remaining_attrs:
#         if not rules:
#             yield (prefix, default_label)
#         return

#     attr = remaining_attrs[0]
#     rest_attrs = remaining_attrs[1:]

#     explicit_values = explicit_values_for_attr(rules, attr)

#     # Branch on each explicit value
#     for val in explicit_values:
#         restricted = restrict_rules_to_value(rules, attr, val)
#         new_prefix = {**prefix, attr: Includes(frozenset({val}))}
#         yield from _compute_defaults_recursive(
#             restricted, rest_attrs, new_prefix, default_label
#         )

#     # Branch on default (not in explicit values)
#     restricted = restrict_rules_to_default(rules, attr)
#     new_prefix = (
#         {**prefix, attr: Excludes(frozenset(explicit_values))}
#         if explicit_values
#         else prefix
#     )
#     yield from _compute_defaults_recursive(
#         restricted, rest_attrs, new_prefix, default_label
#     )


# ---------------------------------------------------------------------
# Segments of bundles -> partition routing rules
# ---------------------------------------------------------------------


@dataclass(frozen=True)
class EdgeKey:
    s: str | None  # source
    t: str | None  # target
    m: str  # material
    z: str  # time


def build_segment_routing(
    source_node: str | None,
    target_node: str | None,
    source_partition: Partition | None = None,
    target_partition: Partition | None = None,
    material_partition: Partition | None = None,
    time_partition: Partition | None = None,
) -> Rules[EdgeKey]:
    """
    Build routing rules for one segment.

    Each partition is expanded with a label prefix based on the node name,
    then combined via product to create EdgeKey tuples.
    """
    # if source_node is not Elsewhere:
    #     source_rules = expand_partition(
    #         source_partition, label_prefix=f"{source_node}^"
    #     )
    # else:
    #     source_rules = Rules([({}, None)])
    # if target_node is not Elsewhere:
    #     target_rules = expand_partition(
    #         target_partition, label_prefix=f"{target_node}^"
    #     )
    # else:
    #     target_rules = Rules([({}, None)])
    source_prefix = f"{source_node}^" if source_node else None
    target_prefix = f"{target_node}^" if target_node else None
    return Rules.expand_product_all(
        expand_partition(source_partition, source_prefix, process_side="source"),
        expand_partition(target_partition, target_prefix, process_side="target"),
        expand_partition(material_partition),
        expand_partition(time_partition),
        combine=EdgeKey,
    )


# Merge segments
def merge_segment_routings(*segments: Rules[EdgeKey]) -> Rules[tuple[EdgeKey]]:
    """
    Merge multiple segment routings.

    A data row flowing through multiple segments collects one EdgeKey per segment.
    """
    return Rules.expand_product_all(*segments, combine=lambda *edges: tuple(edges))


# # Bundle selection with map for resolution
# def build_selection_rules(
#     bundle_info: dict[str, dict],
#     bundles: dict[str, Bundle],
# ) -> Rules[BundleMatch]:
#     candidate_rules = Rules(
#         [
#             (bundle_to_query(info["bundle"], ...), bundle_id)
#             for bundle_id, info in bundle_info.items()
#         ]
#     )

#     # regions() gives Rules[list[str]], then map resolves each list
#     return candidate_rules.regions().map(
#         lambda candidates: resolve_candidates(candidates, bundles)
#     )


# @dataclass
# class BundleSegment:
#     source_id: str
#     target_id: str
#     source_partition: Optional[Partition] = None
#     target_partition: Optional[Partition] = None
#     flow_partition: Optional[Partition] = None
#     time_partition: Optional[Partition] = None


@dataclass
class LeafNode:
    edge_ids: list[int]


@dataclass
class BranchNode:
    attr: str
    branches: dict[str, "Node"]
    default: "Node"


Node = LeafNode | BranchNode


def build_tree(rules: list[tuple[Query, list[int]]], attr_order: list[str]) -> Node:
    if not attr_order:
        all_ids = []
        for _, ids in rules:
            all_ids.extend(ids)
        return LeafNode(all_ids)

    attr = attr_order[0]
    rest = attr_order[1:]

    by_value: dict[str, list[tuple[Query, list[int]]]] = defaultdict(list)
    default_rules = []
    everywhere_rules = []

    for query, edge_ids in rules:
        constraint = query.get(attr)

        if constraint is None:
            everywhere_rules.append((query, edge_ids))
        elif isinstance(constraint, Includes):
            for val in constraint.values:
                by_value[val].append((query, edge_ids))
        else:
            default_rules.append((query, edge_ids))

    branches = {
        val: build_tree(val_rules + everywhere_rules, rest)
        for val, val_rules in by_value.items()
    }

    default_child = build_tree(default_rules + everywhere_rules, rest)

    return BranchNode(attr, branches, default_child)


def collect_attributes(rules: list[tuple[Query, list[int]]]) -> list[str]:
    attrs = set()
    for query, _ in rules:
        attrs.update(query.keys())
    return sorted(attrs)
