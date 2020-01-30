import attr


def _validate_query(instance, attribute, value):
    if value:
        if not all(isinstance(x, tuple) and len(x) == 2 for x in value):
            raise ValueError('All elements of query should be 2-tuples')


@attr.s(slots=True, frozen=True)
class Group(object):
    label = attr.ib(converter=str)
    query = attr.ib(converter=tuple, validator=_validate_query)


@attr.s(slots=True, frozen=True)
class Partition(object):
    groups = attr.ib(default=attr.Factory(tuple), converter=tuple)

    @property
    def labels(self):
        return [g.label for g in self.groups]

    @classmethod
    def Simple(cls, dimension, values):
        def make_group(v):
            if isinstance(v, tuple):
                label, items = v
            else:
                label, items = v, (v, )
            return Group(label, [(dimension, tuple(items))])

        groups = [make_group(v) for v in values]

        # Check for duplicates
        seen_values = set()
        for i, group in enumerate(groups):
            for j, value in enumerate(group.query[0][1]):
                if value in seen_values:
                    raise ValueError('Duplicate value "{}" in partition (value {} of group {})'
                                     .format(value, j, i))
                seen_values.add(value)

        return cls(groups)

    def __add__(self, other):
        return Partition(self.groups + other.groups)

    def __mul__(self, other):
        """Cartesian product"""
        groups = [
            Group('{}/{}'.format(g1.label, g2.label), g1.query + g2.query)
            for g1 in self.groups for g2 in other.groups
        ]
        return Partition(groups)
