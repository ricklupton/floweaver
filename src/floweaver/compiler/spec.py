"""Spec schema for compiled Sankey definitions.

This module defines the JSON-serializable spec format that represents a fully
compiled Sankey diagram definition, with selections/partitions expanded and
converted to explicit filters. The spec can be executed against flow data to
produce SankeyData results.

"""

import attr
from typing import Dict, List, Optional, Tuple, Union

from ..sankey_definition import BundleID
from .tree import Node, tree_from_dict, tree_to_dict


@attr.s(frozen=True)
class MeasureSpec:
    """Specification for a measure to aggregate from flow data."""

    column: str = attr.ib()
    aggregation: str = attr.ib()  # 'sum' or 'mean'

    def to_json(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "column": self.column,
            "aggregation": self.aggregation,
        }

    @classmethod
    def from_json(cls, data: dict) -> "MeasureSpec":
        """Create from JSON dict."""
        return cls(
            column=data["column"],
            aggregation=data["aggregation"],
        )


@attr.s(frozen=True)
class NodeSpec:
    """Specification for a single node in the Sankey diagram."""

    title: str = attr.ib()
    type: str = attr.ib()  # 'process' or 'group'
    group: Optional[str] = attr.ib()
    style: str = attr.ib()
    direction: str = attr.ib()  # 'R' or 'L'
    hidden: bool = attr.ib(default=False)

    def to_json(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "title": self.title,
            "type": self.type,
            "group": self.group,
            "style": self.style,
            "direction": self.direction,
            "hidden": self.hidden,
        }

    @classmethod
    def from_json(cls, data: dict) -> "NodeSpec":
        """Create from JSON dict."""
        return cls(
            title=data["title"],
            type=data["type"],
            group=data.get("group"),
            style=data["style"],
            direction=data["direction"],
            hidden=data.get("hidden", False),
        )


@attr.s(frozen=True)
class GroupSpec:
    """Specification for a process group."""

    id: str = attr.ib()
    title: str = attr.ib()
    nodes: List[str] = attr.ib()

    def to_json(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "id": self.id,
            "title": self.title,
            "nodes": self.nodes,
        }

    @classmethod
    def from_json(cls, data: dict) -> "GroupSpec":
        """Create from JSON dict."""
        return cls(
            id=data["id"],
            title=data["title"],
            nodes=data["nodes"],
        )


@attr.s(frozen=True)
class BundleSpec:
    """Specification for a bundle (provenance for edges)."""

    id: BundleID = attr.ib()
    source: str = attr.ib()  # ProcessGroup ID or 'Elsewhere'
    target: str = attr.ib()  # ProcessGroup ID or 'Elsewhere'

    def to_json(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
        }

    @classmethod
    def from_json(cls, data: dict) -> "BundleSpec":
        """Create from JSON dict."""
        return cls(
            id=data["id"],
            source=data["source"],
            target=data["target"],
        )


@attr.s(frozen=True)
class EdgeSpec:
    """Specification for a single edge in the Sankey diagram."""

    source: Optional[str] = attr.ib()  # None = from elsewhere
    target: Optional[str] = attr.ib()  # None = to elsewhere
    type: str = attr.ib()  # flow type (from flow_partition)
    time: str = attr.ib()  # time key (from time_partition)
    bundle_ids: List[BundleID] = (
        attr.ib()
    )  # bundle IDs this edge represents (for titles/provenance)

    def to_json(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "source": self.source,
            "target": self.target,
            "type": self.type,
            "time": self.time,
            "bundle_ids": self.bundle_ids,
        }

    @classmethod
    def from_json(cls, data: dict) -> "EdgeSpec":
        """Create from JSON dict."""
        return cls(
            source=data.get("source"),
            target=data.get("target"),
            type=data["type"],
            time=data["time"],
            bundle_ids=data["bundle_ids"],
        )


@attr.s(frozen=True)
class CategoricalColorSpec:
    """Categorical color scale specification."""

    attribute: str = attr.ib()  # 'type', 'source', 'target', or measure name
    lookup: Dict[str, str] = attr.ib()  # value -> hex color
    default: str = attr.ib()  # fallback color for unknown values
    type: str = attr.ib(default="categorical")

    def to_json(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "type": self.type,
            "attr": self.attribute,
            "lookup": self.lookup,
            "default": self.default,
        }

    @classmethod
    def from_json(cls, data: dict) -> "CategoricalColorSpec":
        """Create from JSON dict."""
        return cls(
            type=data.get("type", "categorical"),
            attribute=data["attr"],
            lookup=data["lookup"],
            default=data["default"],
        )


@attr.s(frozen=True)
class QuantitativeColorSpec:
    """Quantitative color scale specification."""

    attribute: str = attr.ib()  # measure name
    palette: List[str] = attr.ib()  # array of hex colors for interpolation
    domain: Tuple[float, float] = attr.ib()  # [min, max] for normalization
    type: str = attr.ib(default="quantitative")
    intensity: Optional[str] = attr.ib(default=None)  # optional measure to normalize by

    def to_json(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "type": self.type,
            "attr": self.attribute,
            "palette": self.palette,
            "domain": list(self.domain),  # Convert tuple to list for JSON
            "intensity": self.intensity,
        }

    @classmethod
    def from_json(cls, data: dict) -> "QuantitativeColorSpec":
        """Create from JSON dict."""
        return cls(
            type=data.get("type", "quantitative"),
            attribute=data["attr"],
            palette=data["palette"],
            domain=tuple(data["domain"]),  # Convert list to tuple
            intensity=data.get("intensity"),
        )


# Type alias for color specs
ColorSpec = Union[CategoricalColorSpec, QuantitativeColorSpec]


@attr.s(frozen=True)
class DisplaySpec:
    """Display configuration for the Sankey diagram."""

    link_width: str = attr.ib()  # measure name
    link_color: ColorSpec = attr.ib()

    def to_json(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "link_width": self.link_width,
            "link_color": self.link_color.to_json(),
        }

    @classmethod
    def from_json(cls, data: dict) -> "DisplaySpec":
        """Create from JSON dict."""
        color_data = data["link_color"]
        if color_data.get("type") == "quantitative":
            link_color = QuantitativeColorSpec.from_json(color_data)
        else:
            link_color = CategoricalColorSpec.from_json(color_data)

        return cls(
            link_width=data["link_width"],
            link_color=link_color,
        )


@attr.s(frozen=True)
class WeaverSpec:
    """Complete specification for a compiled Sankey diagram.

    This is the top-level spec that can be serialized to JSON and executed
    against flow data to produce a SankeyData object.
    """

    version: str = attr.ib()
    nodes: Dict[str, NodeSpec] = attr.ib()
    groups: List[GroupSpec] = attr.ib()  # ProcessGroup provenance for nodes
    bundles: List[BundleSpec] = attr.ib()  # Bundle provenance for edges
    ordering: List[List[List[str]]] = attr.ib()
    edges: List[EdgeSpec] = (
        attr.ib()
    )  # includes elsewhere edges (source=None or target=None)
    measures: List[MeasureSpec] = attr.ib()
    display: DisplaySpec = attr.ib()
    routing_tree: Node[tuple[int, ...]] = attr.ib()  # decision tree for flow routing

    def to_json(self) -> dict:
        """Convert to JSON-serializable dict."""
        result = {
            "version": self.version,
            "nodes": {k: v.to_json() for k, v in self.nodes.items()},
            "groups": [g.to_json() for g in self.groups],
            "bundles": [b.to_json() for b in self.bundles],
            "ordering": self.ordering,
            "edges": [e.to_json() for e in self.edges],
            "measures": [m.to_json() for m in self.measures],
            "display": self.display.to_json(),
        }
        if self.routing_tree is not None:
            result["routing_tree"] = tree_to_dict(self.routing_tree)
        return result

    @classmethod
    def from_json(cls, data: dict) -> "WeaverSpec":
        """Create from JSON dict."""
        return cls(
            version=data["version"],
            nodes={k: NodeSpec.from_json(v) for k, v in data["nodes"].items()},
            groups=[GroupSpec.from_json(g) for g in data["groups"]],
            bundles=[BundleSpec.from_json(b) for b in data["bundles"]],
            ordering=data["ordering"],
            edges=[EdgeSpec.from_json(e) for e in data["edges"]],
            measures=[MeasureSpec.from_json(m) for m in data["measures"]],
            display=DisplaySpec.from_json(data["display"]),
            routing_tree=tree_from_dict(data["routing_tree"]),
        )
