import attr

from . import sentinel
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
    bundles = attr.ib(converter=_convert_bundles_to_dict,
                      validator=_validate_bundles)
    ordering = attr.ib(converter=_convert_ordering, validator=_validate_ordering)
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
    """A ProcessGroup represents a group of processes from the underlying dataset.

    The processes to include are defined by the `selection`. By default they
    are all lumped into one node in the diagram, but by defining a `partition`
    this can be controlled.

    Attributes
    ----------
    selection : list or string
        If a list of strings, they are taken as process ids.
        If a single string, it is taken as a Pandas query string run against the
        process table.
    partition : Partition, optional
        Defines how to split the ProcessGroup into subgroups.
    direction : 'R' or 'L'
        Direction of flow, default 'R' (left-to-right).
    title : string, optional
        Label for the ProcessGroup. If not set, the ProcessGroup id will be used.

    """
    selection = attr.ib(default=None)
    partition = attr.ib(default=None)
    direction = attr.ib(validator=_validate_direction, default='R')
    title = attr.ib(
        default=None,
        validator=attr.validators.optional(attr.validators.instance_of(str)))

# Waypoint


@attr.s(slots=True)
class Waypoint(object):
    """A Waypoint represents a control point along a :class:`Bundle` of flows.

    There are two reasons to define Waypoints: to control the routing of
    :class:`Bundle` s of flows through the diagram, and to split flows according
    to some attributes by setting a `partition`.

    Attributes
    ----------
    partition : Partition, optional
        Defines how to split the Waypoint into subgroups.
    direction : 'R' or 'L'
        Direction of flow, default 'R' (left-to-right).
    title : string, optional
        Label for the Waypoint. If not set, the Waypoint id will be used.

    """
    partition = attr.ib(default=None)
    direction = attr.ib(validator=_validate_direction, default='R')
    title = attr.ib(
        default=None,
        validator=attr.validators.optional(attr.validators.instance_of(str)))

# Bundle

Elsewhere = sentinel.create('Elsewhere')


def _validate_flow_selection(instance, attribute, value):
    if instance.source == instance.target and not value:
        raise ValueError('flow_selection is required for bundle with same '
                         'source and target')


@attr.s(frozen=True, slots=True)
class Bundle(object):
    """A Bundle represents a set of flows between two :class:`ProcessGroup`s.

    Attributes
    ----------
    source : string
        The id of the :class:`ProcessGroup` at the start of the Bundle.
    target : string
        The id of the :class:`ProcessGroup` at the end of the Bundle.
    waypoints : list of strings
        Optional list of ids of :class:`Waypoint`s the Bundle should pass through.
    flow_selection : string, optional
        Query string to filter the flows included in this Bundle.
    flow_partition : Partition, optional
        Defines how to split the flows in the Bundle into sub-flows. Often you want
        the same Partition for all the Bundles in the diagram, see
        :attr:`SankeyDefinition.flow_partition`.
    default_partition : Partition, optional
        Defines the Partition applied to any Waypoints automatically added to route
        the Bundle across layers of the diagram.

    """
    source = attr.ib()
    target = attr.ib()
    waypoints = attr.ib(default=attr.Factory(tuple), converter=tuple)
    flow_selection = attr.ib(default=None, validator=_validate_flow_selection)
    flow_partition = attr.ib(default=None)
    default_partition = attr.ib(default=None)

    @property
    def to_elsewhere(self):
        """True if the target of the Bundle is Elsewhere (outside the system
        boundary)."""
        return self.target is Elsewhere

    @property
    def from_elsewhere(self):
        """True if the source of the Bundle is Elsewhere (outside the system
        boundary)."""
        return self.source is Elsewhere
