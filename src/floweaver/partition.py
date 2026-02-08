from collections.abc import Iterable
import attrs
from attrs import define, field


def _validate_query(instance, attribute, value):
    if value:
        if not all(isinstance(x, tuple) and len(x) == 2 for x in value):
            raise ValueError("All elements of query should be 2-tuples")


@define(slots=True, frozen=True)
class Group(object):
    label: str = field(converter=str)
    query: tuple[tuple[str, tuple], ...] = field(
        converter=tuple, validator=_validate_query
    )

    # Define this explicitly to help type checkers
    def __init__(
        self,
        label: object,
        query: Iterable,
    ):
        self.__attrs_init__(label, query)  # type: ignore


@define(slots=True, frozen=True)
class Partition(object):
    groups: tuple[Group, ...] = field(default=attrs.Factory(tuple), converter=tuple)

    # Define this explicitly to help type checkers
    def __init__(
        self,
        groups: Iterable[Group],
    ):
        self.__attrs_init__(tuple(groups))  # type: ignore

    @property
    def labels(self):
        return [g.label for g in self.groups]

    @classmethod
    def Simple(cls, dimension: str, values: Iterable):
        def make_group(v: tuple[object, Iterable] | object):
            if isinstance(v, tuple):
                label, items = v
            else:
                label, items = v, (v,)
            if not isinstance(items, Iterable):
                items = (items,)
            return Group(label, [(dimension, tuple(items))])

        groups = [make_group(v) for v in values]

        # Check for duplicates
        seen_values = set()
        for i, group in enumerate(groups):
            for j, value in enumerate(group.query[0][1]):
                if value in seen_values:
                    raise ValueError(
                        'Duplicate value "{}" in partition (value {} of group {})'.format(
                            value, j, i
                        )
                    )
                seen_values.add(value)

        return cls(groups)

    def __add__(self, other):
        return Partition(self.groups + other.groups)

    def __mul__(self, other):
        """Cartesian product"""
        groups = [
            Group("{}/{}".format(g1.label, g2.label), g1.query + g2.query)
            for g1 in self.groups
            for g2 in other.groups
        ]
        return Partition(groups)
