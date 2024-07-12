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
    from ipywidgets import Layout, Output, VBox
    from IPython.display import display, clear_output
except ImportError:
    SankeyWidget = None

_validate_opt_str = attr.validators.optional(attr.validators.instance_of(str))


@attr.s(slots=True, frozen=True)
class SankeyData(object):
    nodes = attr.ib()
    links = attr.ib()
    groups = attr.ib(default=attr.Factory(list))
    ordering = attr.ib(converter=_convert_ordering, default=Ordering([[]]))
    dataset = attr.ib(default=None)

    def to_json(self, filename=None, format=None):
        """Convert data to JSON-ready dictionary."""
        if format == "widget":
            data = {
                "nodes": [n.to_json(format) for n in self.nodes],
                "links": [l.to_json(format) for l in self.links],
                "order": self.ordering.layers,
                "groups": self.groups,
            }
        else:
            data = {
                "format": "sankey-v2",
                "metadata": {
                    "title": "A Sankey diagram",
                    "authors": [],
                    "layers": self.ordering.layers,
                },
                "nodes": [n.to_json(format) for n in self.nodes],
                "links": [l.to_json(format) for l in self.links],
                "groups": self.groups,
            }

        if filename is None:
            return data
        else:
            with open(filename, "wt") as f:
                json.dump(data, f)

    def to_widget(
        self,
        width=700,
        height=500,
        margins=None,
        align_link_types=False,
        link_label_format="",
        link_label_min_width=5,
        debugging=False,
        forceY=None,
        y_scale=1
    ):

        if SankeyWidget is None:
            raise RuntimeError("ipysankeywidget is required")

        if margins is None:
            margins = {
                "top": 25,
                "bottom": 10,
                "left": 130,
                "right": 130,
            }

        value = self.to_json(format="widget")

        # Assertain the max possible space inc margins
        max_w = width - margins['left'] - margins['right']
    
        # If forceY exists then force the y coordinates
        if forceY:
            # Loop through all the layers
            for i, layer in enumerate(value['order']):
                # Loop through each band in the order
                for band in layer:
                    # Loop through all the nodes in each band:
                    for node in band:
                        # Need to loop through the nodes dict and add the force coords
                        for n in value['nodes']:
                            # If the n[id] matches node then add the positions
                            if node == n['id']:
                                n['position'] = [ (i*max_w)/(len(value['order'])-1), forceY[node]*y_scale]
    
        if forceY:
            widget = SankeyWidget(
                nodes=value["nodes"],
                links=value["links"],
                order=value["order"],
                groups=value["groups"],
                align_link_types=align_link_types,
                linkLabelFormat=link_label_format,
                linkLabelMinWidth=link_label_min_width,
                layout= Layout(width=str(width), height=str(height)),
                margins=margins,
                node_position_attr = 'position'
            )
            widget.scale = y_scale
        
        else:
            widget = SankeyWidget(
                nodes=value["nodes"],
                links=value["links"],
                order=value["order"],
                groups=value["groups"],
                align_link_types=align_link_types,
                linkLabelFormat=link_label_format,
                linkLabelMinWidth=link_label_min_width,
                layout= Layout(width=str(width), height=str(height)),
                margins=margins,
            )
            
        if debugging:
            output = Output()

            def callback(_, d):
                with output:
                    clear_output()
                if not d:
                    return
                if d["source"].startswith("__from_elsewhere_"):
                    d["source"] = None
                elif d["target"].startswith("__to_elsewhere_"):
                    d["target"] = None
                link = [
                    l
                    for l in (
                            self.links +
                            [l for n in self.nodes for l in n.from_elsewhere_links] +
                            [l for n in self.nodes for l in n.to_elsewhere_links]
                    )
                    if l.source == d["source"]
                    and l.target == d["target"]
                    and l.type == d["type"]
                ]
                assert len(link) == 1
                link = link[0]
                with output:
                    display("Flows in dataset contributing to this link:")
                    if self.dataset:
                        display(self.dataset._table.loc[link.original_flows])
                    else:
                        display(link.original_flows)

            widget.on_link_clicked(callback)
            return VBox([widget, output])
        else:
            return widget


@attr.s(slots=True, frozen=True)
class SankeyNode(object):
    id = attr.ib(validator=attr.validators.instance_of(str))
    title = attr.ib(default=None, validator=_validate_opt_str)
    direction = attr.ib(validator=_validate_direction, default="R")
    hidden = attr.ib(default=False)
    style = attr.ib(default=None, validator=_validate_opt_str)
    from_elsewhere_links = attr.ib(default=list)
    to_elsewhere_links = attr.ib(default=list)

    def to_json(self, format=None):
        """Convert node to JSON-ready dictionary."""
        if format == "widget":
            return {
                "id": self.id,
                "title": self.title if self.title is not None else self.id,
                "direction": self.direction.lower(),
                "hidden": self.hidden is True or self.title == "",
                "type": self.style if self.style is not None else "default",
                "fromElsewhere": [l.to_json(format) for l in self.from_elsewhere_links],
                "toElsewhere": [l.to_json(format) for l in self.to_elsewhere_links]
            }
        else:
            return {
                "id": self.id,
                "title": self.title if self.title is not None else self.id,
                "style": {
                    "direction": self.direction.lower(),
                    "hidden": self.hidden is True or self.title == "",
                    "type": self.style if self.style is not None else "default",
                },
            }


def _validate_opacity(instance, attr, value):
    if not isinstance(value, float):
        raise ValueError("opacity must be a number")
    if value < 0 or value > 1:
        raise ValueError("opacity must be between 0 and 1")


@attr.s(slots=True, frozen=True)
class SankeyLink(object):
    source = attr.ib(validator=attr.validators.optional(attr.validators.instance_of(str)))
    target = attr.ib(validator=attr.validators.optional(attr.validators.instance_of(str)))
    type = attr.ib(default=None, validator=_validate_opt_str)
    time = attr.ib(default=None, validator=_validate_opt_str)
    link_width = attr.ib(default=0.0, converter=float)
    data = attr.ib(default=lambda: {"value": 0.0})
    title = attr.ib(default=None, validator=_validate_opt_str)
    color = attr.ib(default=None, validator=_validate_opt_str)
    opacity = attr.ib(default=1.0, converter=float, validator=_validate_opacity)
    original_flows = attr.ib(default=attr.Factory(list))

    def to_json(self, format=None):
        """Convert link to JSON-ready dictionary."""
        if format == "widget":
            return {
                "source": self.source,
                "target": self.target,
                "type": self.type,
                "time": self.time,
                "value": self.link_width,
                "title": self.title,
                "color": self.color,
                "opacity": self.opacity,
                "data": self.data,
            }
        else:
            return {
                "source": self.source,
                "target": self.target,
                "type": self.type,
                "title": self.title,
                "time": self.time,
                "link_width": self.link_width,
                "data": self.data,
                "style": {"color": self.color, "opacity": self.opacity,},
            }
