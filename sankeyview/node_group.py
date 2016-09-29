import attr


def _validate_direction(instance, attribute, value):
    if value not in 'LR':
        raise ValueError('direction must be L or R')


@attr.s(slots=True)
class NodeGroup(object):
    direction = attr.ib(validator=_validate_direction, default='R')
    selection = attr.ib(default=None)
    partition = attr.ib(default=None)
    title = attr.ib(default=None, validator=attr.validators.optional(attr.validators.instance_of(str)))
