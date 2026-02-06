"""Functions to compile Bundle selections into decision tree rules."""

from __future__ import annotations
from typing import TypeVar, Callable, Optional, Mapping, Any
import ast
from functools import reduce
from dataclasses import dataclass
from collections import defaultdict
import pandas as pd

from ..sankey_definition import (
    SankeyDefinition,
    Bundle,
    BundleID,
    ProcessGroup,
    Waypoint,
)
from ..partition import Partition
from .rules import Query, Rules, Includes, Excludes

T = TypeVar("T")


# --- Data structures ---


@dataclass(frozen=True)
class SingleBundleMatch:
    bundle_id: BundleID


@dataclass(frozen=True)
class ElsewhereBundlePairMatch:
    from_elsewhere_bundle_id: BundleID
    to_elsewhere_bundle_id: BundleID


BundleMatch = SingleBundleMatch | ElsewhereBundlePairMatch


# --- Queries for single bundles ---


def build_bundle_selection_query(
    bundle: Bundle,
    nodes: Mapping[str, ProcessGroup | Waypoint],
    dim_process: pd.DataFrame | None,
) -> Query:
    """Build a Query from a Bundle's selection."""
    info = _expand_bundle_selections(bundle, nodes, dim_process)
    query = _build_bundle_selection_query_from_sets(**info)
    return query


def _build_bundle_selection_query_from_sets(
    bundle,
    source_ids: set[str],
    target_ids: set[str],
    filters: dict[str, set[str]],
) -> Query:
    """Internal helper for building a Query from selection."""
    constraints: Query = {}

    if bundle.from_elsewhere:
        constraints["source"] = Excludes(target_ids)
    else:
        constraints["source"] = Includes(source_ids)

    if bundle.to_elsewhere:
        constraints["target"] = Excludes(source_ids)
    else:
        constraints["target"] = Includes(target_ids)

    for attr, values in filters.items():
        assert attr not in constraints  # FIXME should intersect
        constraints[attr] = Includes(values)

    return constraints


def _expand_bundle_selections(
    bundle: Bundle,
    nodes: Mapping[str, ProcessGroup | Waypoint],
    dim_process: pd.DataFrame | None,
):
    """Expand ProcessGroups to explicit process ID sets and filters.

    Returns a dict mapping bundle_id to expanded bundle info:
    {
        'bundle': Bundle object,
        'source_ids': set of process IDs (or None if from_elsewhere),
        'target_ids': set of process IDs (or None if to_elsewhere),
        'filters': dict of additional filters from flow_selection,
    }
    """
    info = {
        "bundle": bundle,
        "source_ids": set(),
        "target_ids": set(),
        "filters": {},
    }

    # Expand source ProcessGroup
    if not bundle.from_elsewhere:
        source_pg = nodes[bundle.source]
        assert isinstance(source_pg, ProcessGroup)
        info["source_ids"] = _expand_process_group(source_pg, dim_process)

    # Expand target ProcessGroup
    if not bundle.to_elsewhere:
        target_pg = nodes[bundle.target]
        assert isinstance(target_pg, ProcessGroup)
        info["target_ids"] = _expand_process_group(target_pg, dim_process)

    # Parse flow_selection filters
    if bundle.flow_selection:
        info["filters"] = _parse_query_string(bundle.flow_selection)

    return info


def _expand_process_group(
    pg: ProcessGroup, dim_process: pd.DataFrame | None
) -> set[str]:
    """Expand a ProcessGroup selection to a set of process IDs."""
    selection = pg.selection

    if isinstance(selection, (list, tuple)):
        return set(selection)

    if isinstance(selection, str):
        # Query string - evaluate against dimension table
        if dim_process is None:
            raise ValueError(
                f"Cannot compile query string selection '{selection}' without "
                "a process dimension table."
            )
        matching_ids = _evaluate_query_on_dimension_table(selection, dim_process)
        return set(matching_ids)

    raise ValueError(f"Cannot interpret ProcessGroup selection {selection!r}")


def _evaluate_query_on_dimension_table(
    query: str, dim_table: pd.DataFrame
) -> list[str]:
    """Evaluate a pandas query against a dimension table."""
    # XXX Why is this needed?
    # if dim_table.index.name is None:
    #     result = dim_table.T.query(query)
    # else:
    #     result = dim_table.query(query)
    result = dim_table.query(query)
    return list(result.index)


# =============================================================================
# Query parsing helpers
# =============================================================================


def _parse_query_string(query):
    """Parse a simple pandas query string into filter format.

    Returns a dict like:
    - For == or in: {column: [values]} (simple list format, backward compatible)
    - For != or not in: {column: {'exclude': [values]}} (dict format for exclusions)
    """
    tree = ast.parse(query, mode="eval")
    expr = tree.body

    if isinstance(expr, ast.Compare):
        left = expr.left
        if len(expr.ops) == 1 and len(expr.comparators) == 1:
            op = expr.ops[0]
            right = expr.comparators[0]

            if isinstance(left, ast.Name):
                column = left.id
            elif isinstance(left, ast.Attribute):
                column = _get_attribute_path(left)
            else:
                raise ValueError(f"Unsupported left side in query: {ast.dump(left)}")

            if isinstance(op, ast.Eq):
                if isinstance(right, ast.Constant):
                    return {column: [right.value]}
                else:
                    raise ValueError(
                        f"Unsupported right side for ==: {ast.dump(right)}"
                    )

            elif isinstance(op, ast.NotEq):
                if isinstance(right, ast.Constant):
                    return {column: {"exclude": [right.value]}}
                else:
                    raise ValueError(
                        f"Unsupported right side for !=: {ast.dump(right)}"
                    )

            elif isinstance(op, ast.In):
                if isinstance(right, (ast.List, ast.Tuple)):
                    values = [
                        elt.value for elt in right.elts if isinstance(elt, ast.Constant)
                    ]
                    return {column: values}
                else:
                    raise ValueError(
                        f"Unsupported right side for 'in': {ast.dump(right)}"
                    )

            elif isinstance(op, ast.NotIn):
                if isinstance(right, (ast.List, ast.Tuple)):
                    values = [
                        elt.value for elt in right.elts if isinstance(elt, ast.Constant)
                    ]
                    return {column: {"exclude": values}}
                else:
                    raise ValueError(
                        f"Unsupported right side for 'not in': {ast.dump(right)}"
                    )

            else:
                raise ValueError(f"Unsupported operator: {type(op).__name__}")

    raise ValueError(f"Unsupported query pattern: {query}")


def _get_attribute_path(node):
    """Get the full attribute path like 'source.type' from an ast.Attribute."""
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        return f"{_get_attribute_path(node.value)}.{node.attr}"
    else:
        raise ValueError(f"Unsupported node type: {type(node).__name__}")


###################
# Functions to build complete selection rules
###################


def build_selection_rules(
    bundles: Mapping[BundleID, Bundle],
    nodes: Mapping[str, ProcessGroup | Waypoint],
    dim_process: pd.DataFrame | None,
) -> Rules[BundleMatch]:
    """Build rules for bundle selections."""
    rules: Rules[BundleID] = Rules(
        [
            (
                build_bundle_selection_query(bundle, nodes, dim_process),
                bundle_id,
            )
            for bundle_id, bundle in bundles.items()
        ]
    )
    resolved_rules = rules.refine().map(
        lambda candidate_ids: resolve_candidates(candidate_ids, bundles)
    )
    resolved_rules = resolved_rules.filter(
        lambda resolved_match: resolved_match is not None
    )

    return resolved_rules


# def build_selection_tree(
#     bundle_info: dict[str, dict],
#     bundles: dict[str, "Bundle"],
# ) -> Node[BundleMatch]:
#     # Step 4: Build tree
#     attr_order = collect_attributes(resolved_rules)
#     return build_tree(resolved_rules, attr_order, combine_values=lambda vs: vs[0])


###################
###################


def resolve_candidates(
    candidates: list[T], bundles: Mapping[T, Bundle]
) -> BundleMatch | None:
    """Resolve multiple bundle matches for the same flows.

    Generally there should be only one candidate bundle. The exception is
    Elsewhere bundles, where it is valid to have a matching pair of a
    to-elsewhere and a from-elsewhere flow (which represent the ends of the
    flows, when the middle is not within the system boundary).

    In addition, bundle ids starting with "__" are assumed to be "implicit"
    Elsewhere bundles added to ensure mass balance of process, so if they
    overlap with an explicit bundle then the implicit bundle can be ignored.

    """
    if not candidates:
        return None

    explicit_regular = []
    explicit_from_elsewhere = []
    explicit_to_elsewhere = []
    implicit_from_elsewhere = []
    implicit_to_elsewhere = []

    for bundle_id in candidates:
        bundle = bundles[bundle_id]
        is_implicit = str(bundle_id).startswith("__")

        if bundle.from_elsewhere:
            target = implicit_from_elsewhere if is_implicit else explicit_from_elsewhere
        elif bundle.to_elsewhere:
            target = implicit_to_elsewhere if is_implicit else explicit_to_elsewhere
        else:
            target = explicit_regular

        target.append(bundle_id)

    # Check for conflicts
    if len(explicit_regular) > 1:
        raise ValueError(f"Multiple explicit bundles match: {explicit_regular}")
    if len(explicit_from_elsewhere) > 1:
        raise ValueError(
            f"Multiple explicit from_elsewhere bundles match: {explicit_from_elsewhere}"
        )
    if len(explicit_to_elsewhere) > 1:
        raise ValueError(
            f"Multiple explicit to_elsewhere bundles match: {explicit_to_elsewhere}"
        )

    # Priority resolution
    if explicit_regular:
        return SingleBundleMatch(explicit_regular[0])

    from_id = (explicit_from_elsewhere or implicit_from_elsewhere or [None])[0]
    to_id = (explicit_to_elsewhere or implicit_to_elsewhere or [None])[0]

    if from_id is not None and to_id is not None:
        return ElsewhereBundlePairMatch(from_id, to_id)
    elif from_id is not None:
        return SingleBundleMatch(from_id)
    elif to_id is not None:
        return SingleBundleMatch(to_id)

    return None
