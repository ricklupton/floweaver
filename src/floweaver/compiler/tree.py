"""Decision tree building"""

from __future__ import annotations
from dataclasses import dataclass
from typing import TypeVar, Callable, Generic, overload
from collections import defaultdict
from collections.abc import Mapping

from .rules import Query, Rules, Includes, Excludes

T = TypeVar("T")
U = TypeVar("U")
V = TypeVar("V")


def _default_get_value(data: Mapping[str, str], key: str) -> str | None:
    return data.get(key)


class Node(Generic[T]):
    @overload
    def evaluate(self, data: Mapping[str, str], get_value: None = None) -> T: ...

    @overload
    def evaluate(self, data: U, get_value: Callable[[U, str], str | None]) -> T: ...

    def evaluate(self, data, get_value=None) -> T:
        """Evaluate decision tree against data"""
        raise NotImplementedError()


@dataclass
class LeafNode(Node, Generic[T]):
    value: T

    def evaluate(self, data, get_value=None) -> T:
        """Evaluate decision tree against data"""
        return self.value


@dataclass
class BranchNode(Node, Generic[T]):
    attr: str
    branches: dict[str, Node[T]]
    default: Node[T]

    def evaluate(self, data, get_value=None) -> T:
        """Evaluate decision tree against data"""
        if get_value is None:
            get_value = _default_get_value
        value = get_value(data, self.attr)
        if value is not None and value in self.branches:
            return self.branches[value].evaluate(data, get_value)
        else:
            return self.default.evaluate(data, get_value)


@overload
def _assert_single(vs: list[T], default=None) -> T | None: ...


@overload
def _assert_single(vs: list[T], default: U) -> T | U: ...


def _assert_single(vs: list[T], default=None):
    if len(vs) == 0:
        return default
    if len(vs) == 1:
        return vs[0]
    raise ValueError(f"Expected single value at leaf, got {len(vs)}: {vs}")


@overload
def build_tree(
    rules: Rules[T],
    *,
    attr_order: list[str] | None = None,
    combine_values: None = None,
    default_value: None = None,
) -> Node[T | None]: ...


@overload
def build_tree(
    rules: Rules[T],
    *,
    attr_order: list[str] | None = None,
    combine_values: None = None,
    default_value: U,
) -> Node[T | U]: ...


@overload
def build_tree(
    rules: Rules[T],
    *,
    attr_order: list[str] | None = None,
    combine_values: Callable[[list[T]], V],
) -> Node[V]: ...


def build_tree(
    rules,
    *,
    attr_order=None,
    combine_values=None,
    default_value=None,
):
    if attr_order is None:
        attr_order = sorted(rules.attrs())

    if len(attr_order) == 0:
        # Reached the end - terminate with all remaining labels
        all_values = [v for _, v in rules]
        if combine_values is None:
            value = _assert_single(all_values, default_value)
        else:
            value = combine_values(all_values)
        return LeafNode(value)

    attr = attr_order[0]
    rest = attr_order[1:]

    # Collect explicit values (from both Includes and Excludes)
    all_values = rules.query_values(attr)

    by_value: dict[str, list[tuple[Query, T]]] = defaultdict(list)
    default_rules = []
    everywhere_rules = []

    for query, value in rules:
        match query.get(attr):
            case None:
                everywhere_rules.append((query, value))
            case Includes(included_values):
                for val in included_values:
                    by_value[val].append((query, value))
            case Excludes(excluded_values):
                # Rule matches branches where val is NOT excluded
                for val in all_values - excluded_values:
                    by_value[val].append((query, value))
                # And matches the default branch
                default_rules.append((query, value))

    branches = {
        val: build_tree(
            Rules(by_value.get(val, []) + everywhere_rules),
            attr_order=rest,
            combine_values=combine_values,
            default_value=default_value,
        )
        for val in all_values
    }

    default = build_tree(
        Rules(default_rules + everywhere_rules),
        attr_order=rest,
        combine_values=combine_values,
        default_value=default_value,
    )

    if branches:
        return BranchNode(attr, branches, default)
    else:
        return default


def tree_to_dict(node: Node) -> dict:
    """Convert to JSON-serializable dict."""
    # TODO: in future this could use hash-consing or other structure sharing
    if isinstance(node, LeafNode):
        return {"value": node.value}
    elif isinstance(node, BranchNode):
        return {
            "attr": node.attr,
            "branches": {k: tree_to_dict(v) for k, v in node.branches.items()},
            "default": tree_to_dict(node.default),
        }
    else:
        raise ValueError("unknown node type")


def tree_from_dict(data: dict) -> Node:
    """Create from JSON dict."""
    if "value" in data:
        # Leaf node
        return LeafNode(data["value"])
    else:
        # Branch node
        return BranchNode(
            attr=data["attr"],
            branches={k: tree_from_dict(v) for k, v in data["branches"].items()},
            default=tree_from_dict(data["default"]),
        )
