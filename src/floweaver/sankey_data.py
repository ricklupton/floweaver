"""Data structure to represent Sankey diagram data.

Author: Rick Lupton
Created: 2018-01-15
"""

from __future__ import annotations

import json
import attrs
from attrs import define, field
from typing import Any

from .sankey_definition import _validate_direction, _convert_ordering
from .ordering import Ordering

try:
    from ipysankeywidget import SankeyWidget  # ty:ignore[unresolved-import]
    from ipywidgets import Layout, Output, VBox  # ty:ignore[unresolved-import]
    from IPython.display import display, clear_output  # ty:ignore[unresolved-import]

    HAVE_WIDGETS = True
except ImportError:
    HAVE_WIDGETS = False

_validate_opt_str = attrs.validators.optional(attrs.validators.instance_of(str))


@define(slots=True, frozen=True)
class SankeyData:
    nodes: list[SankeyNode]
    links: list[SankeyLink]
    groups: list[dict] = field(default=attrs.Factory(list))
    ordering: Ordering = field(converter=_convert_ordering, default=Ordering([[]]))
    dataset: Any | None = None

    def to_json(self, filename=None, format=None):
        """Convert data to JSON-ready dictionary."""
        if format == "widget":
            data = {
                "nodes": [node.to_json(format) for node in self.nodes],
                "links": [link.to_json(format) for link in self.links],
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
                "nodes": [node.to_json(format) for node in self.nodes],
                "links": [link.to_json(format) for link in self.links],
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
    ):
        if not HAVE_WIDGETS:
            raise RuntimeError("ipysankeywidget is required")

        if margins is None:
            margins = {
                "top": 25,
                "bottom": 10,
                "left": 130,
                "right": 130,
            }

        value = self.to_json(format="widget")
        widget = SankeyWidget(
            nodes=value["nodes"],
            links=value["links"],
            order=value["order"],
            groups=value["groups"],
            align_link_types=align_link_types,
            linkLabelFormat=link_label_format,
            linkLabelMinWidth=link_label_min_width,
            layout=Layout(width=str(width), height=str(height)),
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
                    link
                    for link in (
                        self.links
                        + [
                            elsewhere_link
                            for node in self.nodes
                            for elsewhere_link in node.from_elsewhere_links
                        ]
                        + [
                            elsewhere_link
                            for node in self.nodes
                            for elsewhere_link in node.to_elsewhere_links
                        ]
                    )
                    if link.source == d["source"]
                    and link.target == d["target"]
                    and link.type == d["type"]
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


@define(slots=True, frozen=True, order=True)
class SankeyNode:
    id: str
    title: str | None = field(default=None, validator=_validate_opt_str)
    direction: str = field(validator=_validate_direction, default="R")
    hidden: bool = False
    style: str | None = field(default=None, validator=_validate_opt_str)
    from_elsewhere_links: list[SankeyLink] = field(default=attrs.Factory(list))
    to_elsewhere_links: list[SankeyLink] = field(default=attrs.Factory(list))

    def to_json(self, format=None):
        """Convert node to JSON-ready dictionary."""
        if format == "widget":
            return {
                "id": self.id,
                "title": self.title if self.title is not None else self.id,
                "direction": self.direction.lower(),
                "hidden": self.hidden is True or self.title == "",
                "type": self.style if self.style is not None else "default",
                "fromElsewhere": [
                    link.to_json(format) for link in self.from_elsewhere_links
                ],
                "toElsewhere": [
                    link.to_json(format) for link in self.to_elsewhere_links
                ],
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


@define(slots=True, frozen=True, order=True)
class SankeyLink:
    source: str | None = field(
        validator=attrs.validators.optional(attrs.validators.instance_of(str))
    )
    target: str | None = field(
        validator=attrs.validators.optional(attrs.validators.instance_of(str))
    )
    type: str | None = field(default=None, validator=_validate_opt_str)
    time: str | None = field(default=None, validator=_validate_opt_str)
    link_width: float = field(default=0.0, converter=float)
    data: dict = field(default=attrs.Factory(lambda: {"value": 0.0}))
    title: str | None = field(default=None, validator=_validate_opt_str)
    color: str | None = field(default=None, validator=_validate_opt_str)
    opacity: float = field(default=1.0, converter=float, validator=_validate_opacity)
    original_flows: list = field(default=attrs.Factory(list))

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
                "style": {
                    "color": self.color,
                    "opacity": self.opacity,
                },
            }
