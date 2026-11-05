"""Group data values into classes that all routing rules treat identically.

Routing rules only ever test whether a value belongs to one of a known
collection of sets (from ProcessGroup selections, Bundle flow_selections and
Partition groups). Two values that belong to exactly the same sets can never be
told apart, so they can be replaced by a shared class id. Rules and decision
trees are then built over a handful of classes per attribute rather than every
distinct value, which keeps them small. At execution time each value is looked
up in a table to find its class; values not in the table are not mentioned by
any rule, so they follow the default branch of every tree.
"""

from __future__ import annotations
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from .rules import Constraint, Query


@dataclass(frozen=True)
class ValueClasses:
    """Mapping from attribute values to class ids."""

    # attribute -> value -> class id
    tables: dict[str, dict]

    def lookup(self, attr: str, value):
        """Class id for `value`, or None if it is not mentioned by any rule."""
        table = self.tables.get(attr)
        if table is None:
            return value
        return table.get(value)

    def classify_values(self, attr: str, values: Iterable) -> frozenset[str]:
        """Class ids for a set of values used in a rule.

        Every set of values used in a rule must have been included when
        computing the classes, so that it is a union of whole classes.
        """
        table = self.tables.get(attr, {})
        try:
            return frozenset(table[value] for value in values)
        except KeyError as err:
            raise ValueError(
                f"Value {err.args[0]!r} for {attr!r} was not included when "
                "computing value classes"
            ) from None

    def classify_constraint(self, attr: str, constraint: Constraint) -> Constraint:
        return type(constraint)(self.classify_values(attr, constraint.values))

    def classify_query(self, query: Query) -> Query:
        return {
            attr: self.classify_constraint(attr, constraint)
            for attr, constraint in query.items()
        }

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict: attr -> {value: class id}."""
        return {attr: dict(table) for attr, table in self.tables.items()}

    @classmethod
    def from_dict(cls, data: dict) -> "ValueClasses":
        return cls({attr: dict(table) for attr, table in data.items()})


def compute_value_classes(
    value_sets: Mapping[str, Iterable[Iterable]],
) -> ValueClasses:
    """Compute the coarsest classes distinguishing all the given value sets.

    Parameters
    ----------
    value_sets : mapping
        For each attribute, the sets of values used by routing rules.

    Returns
    -------
    ValueClasses
        Values belonging to exactly the same sets share a class id. Class ids
        are assigned deterministically, in order of the sorted values.
    """
    tables = {}
    for attr, sets in value_sets.items():
        sets = [frozenset(s) for s in sets]
        values = sorted(set().union(*sets), key=lambda v: (type(v).__name__, str(v)))
        class_ids: dict[tuple[bool, ...], str] = {}
        table = {}
        for value in values:
            signature = tuple(value in s for s in sets)
            table[value] = class_ids.setdefault(signature, f"c{len(class_ids)}")
        tables[attr] = table
    return ValueClasses(tables)
