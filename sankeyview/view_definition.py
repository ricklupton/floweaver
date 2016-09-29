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
            if b.source not in instance.node_groups:
                raise ValueError('Unknown node_group "{}" in bundle'.format(b.source))
            if not instance.node_groups[b.source].selection:
                raise ValueError('b {} - {}: source must define selection'
                                    .format(b.source, b.target))
        if not b.to_elsewhere:
            if b.target not in instance.node_groups:
                raise ValueError('Unknown node_group "{}" in bundle'.format(b.target))
            if not instance.node_groups[b.target].selection:
                raise ValueError('b {} - {}: target must define selection'
                                    .format(b.source, b.target))
        for u in b.waypoints:
            if u not in instance.node_groups:
                raise ValueError('Unknown waypoint "{}" in bundle'.format(u))


def _validate_ordering(instance, attribute, ordering):
    for layer_bands in ordering.layers:
        for band_nodes in layer_bands:
            for u in band_nodes:
                if u not in instance.node_groups:
                    raise ValueError('Unknown node "{}" in ordering'.format(u))


@attr.s(slots=True, frozen=True)
class ViewDefinition(object):
    node_groups = attr.ib()
    bundles = attr.ib(convert=_convert_bundles_to_dict, validator=_validate_bundles)
    ordering = attr.ib(convert=_convert_ordering, validator=_validate_ordering)
    flow_selection = attr.ib(default=None)
    flow_partition = attr.ib(default=None)
    time_partition = attr.ib(default=None)

    def copy(self):
        return self.__class__(self.node_groups.copy(), self.bundles.copy(),
                              self.ordering, self.flow_partition,
                              self.flow_selection, self.time_partition)
