import attr

from .ordering import Ordering


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
    for b in bundles.values():
        if not b.from_elsewhere:
            if b.source not in instance.process_groups:
                raise ValueError('Unknown process_group "{}" in bundle'.format(b.source))
        if not b.to_elsewhere:
            if b.target not in instance.process_groups:
                raise ValueError('Unknown process_group "{}" in bundle'.format(b.target))
        for u in b.waypoints:
            if u not in instance.waypoints:
                raise ValueError('Unknown waypoint "{}" in bundle'.format(u))


def _validate_ordering(instance, attribute, ordering):
    for layer_bands in ordering.layers:
        for band_nodes in layer_bands:
            for u in band_nodes:
                if u not in instance.process_groups and u not in instance.waypoints:
                    raise ValueError('Unknown node "{}" in ordering'.format(u))


@attr.s(slots=True, frozen=True)
class ViewDefinition(object):
    process_groups = attr.ib()
    waypoints = attr.ib()
    bundles = attr.ib(convert=_convert_bundles_to_dict, validator=_validate_bundles)
    ordering = attr.ib(convert=_convert_ordering, validator=_validate_ordering)
    flow_selection = attr.ib(default=None)
    flow_partition = attr.ib(default=None)
    time_partition = attr.ib(default=None)

    def copy(self):
        return self.__class__(self.process_groups.copy(), self.waypoints.copy(),
                              self.bundles.copy(),
                              self.ordering, self.flow_partition,
                              self.flow_selection, self.time_partition)


########################################


def _validate_direction(instance, attribute, value):
    if value not in 'LR':
        raise ValueError('direction must be L or R')


@attr.s(slots=True)
class ProcessGroup(object):
    selection = attr.ib(default=None)
    direction = attr.ib(validator=_validate_direction, default='R')
    partition = attr.ib(default=None)
    title = attr.ib(default=None, validator=attr.validators.optional(attr.validators.instance_of(str)))


@attr.s(slots=True)
class Waypoint(object):
    direction = attr.ib(validator=_validate_direction, default='R')
    partition = attr.ib(default=None)
    title = attr.ib(default=None, validator=attr.validators.optional(attr.validators.instance_of(str)))
