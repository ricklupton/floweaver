"""Generic tracking of queries and rules.

These are used to describe both Bundle selections and Partition groups.

"""

from __future__ import annotations
from typing import Generic, TypeVar, Callable, Iterator, Mapping
from functools import reduce
from dataclasses import dataclass, field
from collections import defaultdict

from ..partition import Partition

T = TypeVar("T")
U = TypeVar("U")
V = TypeVar("V")


# ---------------------------------------------------------------------
# Constraints
# ---------------------------------------------------------------------


@dataclass(frozen=True)
class Constraint:
    __match_args__ = ("values",)
    values: frozenset[str] = field(init=False)

    def __init__(self, values: set[str] | frozenset[str]) -> None:
        object.__setattr__(self, "values", frozenset(values))

    def __replace__(self, **changes):
        return type(self)(changes.get("values", self.values))

    def __repr__(self) -> str:
        # Ensure constistent ordering
        values_str = "{" + ", ".join(repr(v) for v in sorted(self.values)) + "}"
        return f"{type(self).__name__}({values_str})"


class Includes(Constraint):
    pass


class Excludes(Constraint):
    pass


def intersect_constraints(c1: Constraint, c2: Constraint) -> Constraint:
    """Calculate intersection of Constraints."""
    match (c1, c2):
        case (Includes(i1), Includes(i2)):
            return Includes(i1 & i2)

        case (Includes(i), Excludes(e)) | (Excludes(e), Includes(i)):
            return Includes(i - e)

        case (Excludes(e1), Excludes(e2)):
            return Excludes(e1 | e2)

    raise ValueError(f"Cannot intersect {c1!r} and {c2!r}")


# ---------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------

Query = dict[str, Constraint]


def intersect_queries(q1: Query, q2: Query) -> Query:
    """Calculate intersection of Queries."""
    result: Query = dict(q1)

    for attr, c2 in q2.items():
        if attr in result:
            result[attr] = intersect_constraints(result[attr], c2)
        else:
            result[attr] = c2

    return result


def is_satisfiable(q: Query) -> bool:
    return all(not isinstance(c, Includes) or c.values for c in q.values())


# ---------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------


def _hashable_query(query: Query) -> frozenset:
    return frozenset((attr, type(c).__name__, c.values) for attr, c in query.items())


def _hashable_rule(rule: tuple[Query, T]) -> tuple[frozenset, T]:
    query, label = rule
    # Handle unhashable labels (like lists) by converting to tuple
    # hashable_label = tuple(label) if isinstance(label, list) else label
    # return (_hashable_query(query), hashable_label)
    return (_hashable_query(query), label)


def _format_query(q: Query) -> str:
    return repr(dict(sorted(q.items())))
    # items = sorted(q.items())
    # inner = ", ".join(f"{attr!r}: {c!r}" for attr, c in items)
    # return "{" + inner + "}"


def _format_label(label: T) -> str:
    return repr(label)
    # if isinstance(label, list):
    #     return "[" + ", ".join(_format_label(x) for x in label) + "]"
    # elif isinstance(label, tuple):
    #     inner = ", ".join(_format_label(x) for x in label)
    #     return f"({inner},)" if len(label) == 1 else f"({inner})"
    # else:
    #     return repr(label)


def _format_rule(rule: tuple[Query, T]) -> str:
    query, label = rule
    return f"({_format_query(query)}, {_format_label(label)})"


@dataclass
class Rules(Generic[T]):
    """A collection of (Query, label) rules defining a partial function from attribute space."""

    items: list[tuple[Query, T]]

    def __iter__(self) -> Iterator[tuple[Query, T]]:
        return iter(self.items)

    def __len__(self) -> int:
        return len(self.items)

    def __eq__(self, other) -> bool:
        if not isinstance(other, Rules):
            return NotImplemented
        if len(self.items) != len(other.items):
            return False
        self_set = {_hashable_rule(r) for r in self.items}
        other_set = {_hashable_rule(r) for r in other.items}
        return self_set == other_set

    def __repr__(self) -> str:
        sorted_items = sorted(self.items, key=_hashable_rule)
        rules_str = ",\n    ".join(_format_rule(r) for r in sorted_items)
        return f"Rules([\n    {rules_str},\n])" if sorted_items else "Rules([])"

    def map(self, f: Callable[[T], U]) -> Rules[U]:
        """Transform labels."""
        return Rules([(q, f(label)) for q, label in self.items])

    def filter(self, pred: Callable[[T], bool]) -> Rules[T]:
        """Keep only rules where predicate holds."""
        return Rules([(q, label) for q, label in self.items if pred(label)])

    def attrs(self) -> set[str]:
        """All attributes used in queries."""
        result = set()
        for query, _ in self.items:
            result.update(query.keys())
        return result

    def query_values(self, attr: str) -> set[str]:
        """All values that appear in queries for `attr`."""
        explicit_values: set[str] = set()
        for query, _ in self.items:
            match query.get(attr):
                case Constraint(values):
                    explicit_values.update(values)
        return explicit_values

    def raise_if_overlapping(self) -> Rules[T]:
        """
        Raise ValueError if any two rules can match the same row.

        Returns self for chaining.
        """
        for query, labels in self.refine():
            if len(labels) > 1:
                raise ValueError(f"Rules overlap: {labels} both match {query}")
        return self

    def refine(self) -> Rules[tuple[T]]:
        """
        Compute common refinement: find all distinct regions and collect matching labels.

        Input rules may have overlapping queries. Output rules have non-overlapping
        queries, each with a list of all labels from input rules that match that region.
        """
        attr_order = sorted(self.attrs())
        items = list(_compute_regions_recursive(self.items, attr_order, {}))
        return Rules(items)  # type: ignore

    # def with_defaults(self, default_label: T) -> Rules[T]:
    #     """Add default rules for uncovered regions."""
    #     defaults = [
    #         (query, default_label) for query, labels in self.refine() if not labels
    #     ]
    #     return Rules(self.items + defaults)

    def expand(self, f: Callable[[T], Rules[U]]) -> Rules[U]:
        """
        Expand each rule using f(label) to get new rules, intersecting queries.

        For each (query, label), calls f(label) to get Rules[U], then intersects
        query with each resulting query. Drops unsatisfiable results.
        """
        result = []
        for q1, label in self.items:
            for q2, new_label in f(label):
                combined = intersect_queries(q1, q2)
                if is_satisfiable(combined):
                    result.append((combined, new_label))
        return Rules(result)

    def expand_product(self, other: Rules[U], combine: Callable[[T, U], V]) -> Rules[V]:
        """Combine two rule sets via query intersection.

        Note: if either input has overlapping rules, output will too. For
        non-overlapping output, call refine() first.

        Equivalent to: self.expand(lambda t: other.map(lambda u: combine(t, u)))
        """
        return self.expand(lambda t: other.map(lambda u: combine(t, u)))

    # def to_tree(
    #     self,
    #     attr_order: list[str] | None = None,
    #     combine_values: Callable[[list[T]], T] = lambda vs: vs[0],
    # ) -> Node[T]:
    #     """Build decision tree from rules."""
    #     if attr_order is None:
    #         attr_order = sorted(self.attrs())
    #     return build_tree(self.items, attr_order, combine_values)

    @staticmethod
    def expand_product_all(*rule_sets: Rules, combine: Callable[..., U]) -> Rules[U]:
        """Combine multiple rule sets.

        Note: if any inputs have overlapping rules, output will too. For
        non-overlapping output, call refine() first.
        """
        if len(rule_sets) == 0:
            return Rules([])

        if len(rule_sets) == 1:
            return rule_sets[0].map(lambda x: combine(x))

        # Accumulate as tuples, then apply combine at the end
        result = rule_sets[0].map(lambda x: (x,))
        for rules in rule_sets[1:]:
            result = result.expand_product(rules, lambda acc, x: acc + (x,))

        return result.map(lambda labels: combine(*labels))


def _compute_regions_recursive(
    rules: list[tuple[Query, T]],
    remaining_attrs: list[str],
    prefix: Query,
) -> Iterator[tuple[Query, tuple[T]]]:
    """
    Recursively find default regions by branching on each attribute.

    Yields (Query, label) for each default region found.
    """

    # Finished - return matching labels
    if not remaining_attrs:
        labels = [label for _, label in rules]
        yield (prefix, tuple(labels))
        return

    attr = remaining_attrs[0]
    rest_attrs = remaining_attrs[1:]

    explicit_values = _explicit_values_for_attr(rules, attr)

    for val in explicit_values:
        restricted = _restrict_rules_to_value(rules, attr, val)
        new_prefix = {**prefix, attr: Includes(frozenset({val}))}
        yield from _compute_regions_recursive(restricted, rest_attrs, new_prefix)

    restricted = _restrict_rules_to_default(rules, attr, explicit_values)
    new_prefix = (
        {**prefix, attr: Excludes(frozenset(explicit_values))}
        if explicit_values
        else prefix
    )
    yield from _compute_regions_recursive(restricted, rest_attrs, new_prefix)


def _explicit_values_for_attr(rules: list[tuple[Query, T]], attr: str) -> set[str]:
    """Collect all values explicitly included for an attribute across rules."""
    all_values: set[str] = set()
    for query, _ in rules:
        match query.get(attr):
            case Constraint(values):
                all_values.update(values)
    return all_values


def _restrict_rules_to_value(
    rules: list[tuple[Query, T]], attr: str, val: str
) -> list[tuple[Query, T]]:
    """
    Filter rules to those matching attr=val, removing the constraint.

    Returns rules that are still potentially satisfiable given attr=val,
    with the now-redundant attr constraint removed.
    """
    result = []
    for query, label in rules:
        match query.get(attr):
            case None:
                result.append((query, label))
            case Includes(values) if val in values:
                result.append(({k: v for k, v in query.items() if k != attr}, label))
            case Excludes(values) if val not in values:
                result.append(({k: v for k, v in query.items() if k != attr}, label))
    return result


def _restrict_rules_to_default(
    rules: list[tuple[Query, T]],
    attr: str,
    explicit_values: set[str],
) -> list[tuple[Query, T]]:
    """
    Filter rules to those matching the default branch for attr.

    The default region is where attr ∉ explicit_values.
    """
    result = []
    for query, label in rules:
        match query.get(attr):
            case None:
                result.append((query, label))
            case Excludes(excluded_values) if excluded_values <= explicit_values:
                # Excludes matches default if all excluded values are in
                # explicit_values (because default already excludes those)
                result.append(({k: v for k, v in query.items() if k != attr}, label))
            # Includes never matches default
    return result
