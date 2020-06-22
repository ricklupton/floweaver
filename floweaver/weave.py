import attr
import numpy as np
import pandas as pd
import itertools

from .dataset import Dataset
from .sankey_data import SankeyData, SankeyNode, SankeyLink
from .augment_view_graph import augment, elsewhere_bundles
from .view_graph import view_graph
from .results_graph import results_graph
from .color_scales import CategoricalScale, QuantitativeScale

from palettable.colorbrewer import qualitative, sequential

# From matplotlib.colours
def rgb2hex(rgb):
    "Given an rgb or rgba sequence of 0-1 floats, return the hex string"
    return "#%02x%02x%02x" % tuple([int(np.round(val * 255)) for val in rgb[:3]])


def weave(
    sankey_definition,
    dataset,
    measures="value",
    link_width=None,
    link_color=None,
    palette=None,
):

    # Accept DataFrames as datasets -- assume it's the flow table
    if isinstance(dataset, pd.DataFrame):
        dataset = Dataset(dataset)

    # Calculate the view graph (adding dummy nodes)
    GV = view_graph(sankey_definition)

    # Add implicit to/from Elsewhere bundles to the view definition to ensure
    # consistency.
    new_waypoints, new_bundles = elsewhere_bundles(sankey_definition)
    GV2 = augment(GV, new_waypoints, new_bundles)

    # XXX messy
    bundles2 = dict(sankey_definition.bundles, **new_bundles)

    # Get the flows selected by the bundles
    bundle_flows, unused_flows = dataset.apply_view(
        sankey_definition.nodes, bundles2, sankey_definition.flow_selection
    )

    # Calculate the results graph (actual Sankey data)
    GR, groups = results_graph(
        GV2,
        bundle_flows,
        flow_partition=sankey_definition.flow_partition,
        time_partition=sankey_definition.time_partition,
        measures=measures,
    )

    # Default link width is same as default measure
    if link_width is None:
        if not isinstance(measures, str):
            raise ValueError(
                (
                    "If you set a complicated measure function, "
                    "you need to set link_width too."
                )
            )
        link_width = measures

    if callable(link_width):
        get_value = lambda link, measures: link_width(measures)
    elif isinstance(link_width, str):
        get_value = lambda link, measures: float(measures[link_width])
    else:
        raise ValueError("link_width must be a str or callable")

    # Default link color is categorical scale based on link type
    if link_color is None:
        link_color = CategoricalScale("type", palette=palette)
    elif isinstance(link_color, str):
        link_color = CategoricalScale(link_color, palette=palette)
    elif not callable(link_color):
        raise TypeError("link_color must be a str or callable")

    # Set domain for quantitative colors, if not already set
    if hasattr(link_color, "set_domain_from"):
        link_color.set_domain_from(
            [data["measures"] for _, _, data in GR.edges(data=True)]
        )

    # Package result
    links = [
        make_link(get_value, link_color, v, w, m, t, data)
        for v, w, (m, t), data in GR.edges(keys=True, data=True)
    ]
    nodes = [make_node(u, data) for u, data in GR.nodes(data=True)]
    result = SankeyData(nodes, links, groups, GR.ordering.layers, dataset)

    return result


# maybe this function should be customisable?


def make_link(get_value, get_color, v, w, m, t, data):
    link = SankeyLink(
        source=v,
        target=w,
        type=m,
        time=t,
        title=str(m),
        data=data["measures"],
        original_flows=data["original_flows"],
    )
    return attr.evolve(
        link,
        # value=get_value(link, data['measures']),
        color=get_color(link, data["measures"]),
    )


def make_node(u, data):
    return SankeyNode(
        id=u,
        title=data.get("title"),
        style=data.get("type"),
        direction=data.get("direction", "R"),
        # XXX not setting hidden here -- should have logic here or in to_json()?
    )


def prep_qualitative_palette(G, palette):
    # qualitative colours based on material
    if palette is None:
        palette = "Pastel1_8"

    if isinstance(palette, str):
        try:
            palette = getattr(qualitative, palette).hex_colors
        except AttributeError:
            raise ValueError(
                "No qualitative palette called {}".format(palette)
            ) from None

    if not isinstance(palette, dict):
        materials = sorted(set([m for v, w, (m, t) in G.edges(keys=True)]))
        palette = {m: v for m, v in zip(materials, itertools.cycle(palette))}
