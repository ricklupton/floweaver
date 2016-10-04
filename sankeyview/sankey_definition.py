import attr
import sentinel

from .ordering import Ordering

# SankeyDefinition


def _convert_bundles_to_dict(bundles):
    if not isinstance(bundles, dict):
        bundles = {k: v for k, v in enumerate(bundles)}
    return bundles


def _convert_ordering(ordering):
    if isinstance(ordering, Ordering):
        return ordering
    else:
        return Ordering(ordering)


def _validate_bundles(instance, attribute, bundles):
    # Check bundles
    for k, b in bundles.items():
        if not b.from_elsewhere:
            if b.source not in instance.nodes:
                raise ValueError('Unknown source "{}" in bundle {}'.format(
                    b.source, k))
            if not isinstance(instance.nodes[b.source], ProcessGroup):
                raise ValueError(
                    'Source of bundle {} is not a process group'.format(k))
        if not b.to_elsewhere:
            if b.target not in instance.nodes:
                raise ValueError('Unknown target "{}" in bundle {}'.format(
                    b.target, k))
            if not isinstance(instance.nodes[b.target], ProcessGroup):
                raise ValueError(
                    'Target of bundle {} is not a process group'.format(k))
        for u in b.waypoints:
            if u not in instance.nodes:
                raise ValueError('Unknown waypoint "{}" in bundle {}'.format(
                    u, k))
            if not isinstance(instance.nodes[u], Waypoint):
                raise ValueError(
                    'Waypoint "{}" of bundle {} is not a waypoint'.format(u,
                                                                          k))


def _validate_ordering(instance, attribute, ordering):
    for layer_bands in ordering.layers:
        for band_nodes in layer_bands:
            for u in band_nodes:
                if u not in instance.nodes:
                    raise ValueError('Unknown node "{}" in ordering'.format(u))


@attr.s(slots=True, frozen=True)
class SankeyDefinition(object):
    nodes = attr.ib()
    bundles = attr.ib(convert=_convert_bundles_to_dict,
                      validator=_validate_bundles)
    ordering = attr.ib(convert=_convert_ordering, validator=_validate_ordering)
    flow_selection = attr.ib(default=None)
    flow_partition = attr.ib(default=None)
    time_partition = attr.ib(default=None)

    def copy(self):
        return self.__class__(self.nodes.copy(), self.bundles.copy(),
                              self.ordering, self.flow_partition,
                              self.flow_selection, self.time_partition)

# ProcessGroup


def _validate_direction(instance, attribute, value):
    if value not in 'LR':
        raise ValueError('direction must be L or R')


@attr.s(slots=True)
class ProcessGroup(object):
    selection = attr.ib(default=None)
    partition = attr.ib(default=None)
    direction = attr.ib(validator=_validate_direction, default='R')
    title = attr.ib(
        default=None,
        validator=attr.validators.optional(attr.validators.instance_of(str)))

# Waypoint


@attr.s(slots=True)
class Waypoint(object):
    partition = attr.ib(default=None)
    direction = attr.ib(validator=_validate_direction, default='R')
    title = attr.ib(
        default=None,
        validator=attr.validators.optional(attr.validators.instance_of(str)))

# Bundle

Elsewhere = sentinel.create('Elsewhere')


@attr.s(slots=True)
class Bundle(object):
    source = attr.ib()
    target = attr.ib()
    waypoints = attr.ib(default=attr.Factory(tuple), convert=tuple)
    flow_selection = attr.ib(default=None)
    flow_partition = attr.ib(default=None)
    default_partition = attr.ib(default=None)

    @property
    def to_elsewhere(self):
        return self.target is Elsewhere

    @property
    def from_elsewhere(self):
        return self.source is Elsewhere
