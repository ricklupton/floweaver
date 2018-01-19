"""Data structure to represent Sankey diagram data.

Author: Rick Lupton
Created: 2018-01-15
"""

import json
import attr
from collections import defaultdict

from .sankey_definition import _validate_direction, _convert_ordering
from .ordering import Ordering

try:
    from ipysankeywidget import SankeyWidget
    from ipywidgets import Layout
except ImportError:
    SankeyWidget = None

_validate_opt_str = attr.validators.optional(attr.validators.instance_of(str))


@attr.s(slots=True, frozen=True)
class SankeyData(object):
    nodes = attr.ib()
    links = attr.ib()
    groups = attr.ib(default=attr.Factory(list))
    ordering = attr.ib(convert=_convert_ordering, default=Ordering([[]]))

    def to_json(self, filename=None):
        """Convert data to JSON-ready dictionary."""
        data = {
            'nodes': [n.to_json() for n in self.nodes],
            'links': [l.to_json() for l in self.links],
            'order': self.ordering.layers,
            'groups': self.groups,
        }

        if filename is None:
            return data
        else:
            with open(filename, 'wt') as f:
                json.dump(data, f)

    def to_widget(self, width=700, height=500, margins=None,
                  align_link_types=False):

        if SankeyWidget is None:
            raise RuntimeError('ipysankeywidget is required')

        if margins is None:
            margins = {
                'top': 25,
                'bottom': 10,
                'left': 130,
                'right': 130,
            }

        value = self.to_json()
        return SankeyWidget(nodes=value['nodes'],
                            links=value['links'],
                            order=value['order'],
                            groups=value['groups'],
                            align_link_types=align_link_types,
                            layout=Layout(width=str(width), height=str(height)),
                            margins=margins)



@attr.s(slots=True, frozen=True)
class SankeyNode(object):
    id = attr.ib(validator=attr.validators.instance_of(str))
    title = attr.ib(default=None, validator=_validate_opt_str)
    direction = attr.ib(validator=_validate_direction, default='R')
    hidden = attr.ib(default=False)
    style = attr.ib(default=None, validator=_validate_opt_str)

    def to_json(self):
        """Convert node to JSON-ready dictionary."""
        return {
            'id': self.id,
            'title': self.title if self.title is not None else self.id,
            'style': {
                'direction': self.direction.lower(),
                'hidden': self.hidden is True or self.title == '',
                'type': self.style if self.style is not None else 'default',
            },
        }


def _validate_opacity(instance, attr, value):
    if not isinstance(value, float):
        raise ValueError('opacity must be a number')
    if value < 0 or value > 1:
        raise ValueError('opacity must be between 0 and 1')


@attr.s(slots=True, frozen=True)
class SankeyLink(object):
    source = attr.ib(validator=attr.validators.instance_of(str))
    target = attr.ib(validator=attr.validators.instance_of(str))
    type = attr.ib(default=None, validator=_validate_opt_str)
    time = attr.ib(default=None, validator=_validate_opt_str)
    value = attr.ib(default=0.0, convert=float)
    title = attr.ib(default=None, validator=_validate_opt_str)
    color = attr.ib(default=None, validator=_validate_opt_str)
    opacity = attr.ib(default=1.0, convert=float, validator=_validate_opacity)

    def to_json(self):
        """Convert link to JSON-ready dictionary."""
        return {
            'source': self.source,
            'target': self.target,
            'type': self.type,
            'time': self.time,
            'value': self.value,
            'title': self.title,
            # XXX format
            # 'style': {
            'color': self.color,
            'opacity': self.opacity,
            # }
        }
