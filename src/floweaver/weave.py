import attr
import numpy as np
import pandas as pd
import itertools

from .dataset import Dataset
from .sankey_data import SankeyData, SankeyNode, SankeyLink
from .augment_view_graph import augment, elsewhere_bundles
from .view_graph import view_graph
from .results_graph import frame_labels, results_graph
from .color_scales import CategoricalScale

from palettable.colorbrewer import qualitative


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
    add_elsewhere_waypoints=True,
):
    # Accept DataFrames as datasets -- assume it's the flow table
    if isinstance(dataset, pd.DataFrame):
        dataset = Dataset(dataset)

    # Calculate the view graph (adding dummy nodes)
    GV = view_graph(sankey_definition)

    # Add implicit to/from Elsewhere bundles to the view definition to ensure
    # consistency.
    new_waypoints, new_bundles = elsewhere_bundles(
        sankey_definition, add_elsewhere_waypoints
    )
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
        frame_partition=sankey_definition.frame_partition,
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

        def get_value(link, measures):
            return link_width(measures)
    elif isinstance(link_width, str):

        def get_value(link, measures):
            return float(measures[link_width])
    else:
        raise ValueError("link_width must be a str or callable")

    # Default link color is categorical scale based on link type
    if link_color is None:
        link_color = CategoricalScale("type", palette=palette)
    elif isinstance(link_color, str):
        link_color = CategoricalScale(link_color, palette=palette)
    elif not callable(link_color):
        raise TypeError("link_color must be a str or callable")

    # With a frame partition, measures hold one value per frame: link widths
    # are computed per frame, and colours (for now) from each measure's
    # largest value across frames.
    frames = sankey_definition.frame_partition
    if frames is not None:
        n_frames = len(frames.groups)
        get_scalar_value, scalar_color = get_value, link_color

        def get_value(link, measures):
            return [
                get_scalar_value(link, {k: v[i] for k, v in measures.items()})
                for i in range(n_frames)
            ]

        def link_color(link, measures):
            return scalar_color(link, _largest(measures))

        color_domain = [
            _largest(data["measures"]) for _, _, data in GR.edges(data=True)
        ]
        scale = scalar_color
    else:
        color_domain = [data["measures"] for _, _, data in GR.edges(data=True)]
        scale = link_color

    # Set domain for quantitative colors, if not already set
    if hasattr(scale, "set_domain_from"):
        scale.set_domain_from(color_domain)  # ty:ignore[call-non-callable]

    # Package result
    links = [
        make_link(get_value, link_color, v, w, m, t, data)
        for v, w, (m, t), data in GR.edges(keys=True, data=True)
    ]
    nodes = [
        make_node(get_value, link_color, u, data) for u, data in GR.nodes(data=True)
    ]
    result = SankeyData(
        nodes,
        links,
        groups,
        GR.ordering.layers,
        dataset,
        frames=None if frames is None else frame_labels(frames),
    )

    return result


def _largest(measures):
    """Reduce per-frame measures to their largest value (non-numeric: first)."""
    out = {}
    for k, values in measures.items():
        try:
            out[k] = max(values)
        except TypeError:
            out[k] = values[0]
    return out


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
        link_width=get_value(link, data["measures"]),
        color=get_color(link, data["measures"]),
    )


def make_node(get_value, get_color, u, data):
    return SankeyNode(
        id=u,
        title=data.get("title"),
        style=data.get("type"),
        direction=data.get("direction", "R"),
        from_elsewhere_links=[
            make_link(get_value, get_color, None, u, m, t, data)
            for (m, t), data in data.get("from_elsewhere_edges", [])
        ],
        to_elsewhere_links=[
            make_link(get_value, get_color, u, None, m, t, data)
            for (m, t), data in data.get("to_elsewhere_edges", [])
        ],
        # XXX not setting hidden here -- should have logic here or in to_json()?
    )


def weave_compiled(
    sankey_definition,
    dataset,
    measures="value",
    link_width=None,
    link_color=None,
    palette=None,
    add_elsewhere_waypoints=True,
    dimension_tables=None,
):
    """New implementation of weave using the compile + execute approach.

    This function compiles a SankeyDefinition into a WeaverSpec, then
    executes the spec against flow data to produce SankeyData. This
    produces equivalent results to the original weave() function.

    Parameters
    ----------
    sankey_definition : SankeyDefinition
        The high-level definition of the Sankey diagram.
    dataset : Dataset or DataFrame
        The flow data to visualize.
    measures : str, list, or dict
        Measures to aggregate. Defaults to 'value'.
    link_width : str, optional
        Measure name to use for link width. Defaults to first measure.
    link_color : str or ColorScale, optional
        Color scale for links. Defaults to categorical by flow type.
    palette : str or list, optional
        Color palette name or list of hex colors.
    add_elsewhere_waypoints : bool
        Whether to add waypoints for elsewhere flows. Default True.
    dimension_tables : dict, optional
        Dimension tables for query string selection resolution.

    Returns
    -------
    SankeyData
        The resulting Sankey diagram data with nodes and links.
    """
    from .compiler import compile_sankey_definition, execute_weave

    # Accept DataFrames as datasets -- assume it's the flow table
    if isinstance(dataset, pd.DataFrame):
        dataset = Dataset(dataset)

    # Compile the definition into a spec
    spec = compile_sankey_definition(
        sankey_definition,
        measures=measures,
        link_width=link_width,
        link_color=link_color,
        palette=palette,
        add_elsewhere_waypoints=add_elsewhere_waypoints,
        dimension_tables=dimension_tables,
    )
    # Execute the spec against the dataset
    return execute_weave(spec, dataset)


def weave_table(
    sankey_definition,
    dataset,
    measures="value",
    dimension_tables=None,
):
    """Tabulate the flows shown in a Sankey diagram.

    Where :func:`weave` produces the drawable diagram, ``weave_table`` produces
    a tidy table of the same flows, summarised end to end from source to target
    rather than split into segments between Waypoints. Labels are those a reader
    sees in the diagram, so the result is suitable as "source data"
    accompanying a published figure (e.g. via ``DataFrame.to_excel``).

    Parameters
    ----------
    sankey_definition : SankeyDefinition
        The high-level definition of the Sankey diagram.
    dataset : Dataset or DataFrame
        The flow data.
    measures : str, list, or dict
        Measures to aggregate. Defaults to 'value'.
    dimension_tables : dict, optional
        Dimension tables for query string selection resolution.

    Returns
    -------
    DataFrame
        See :func:`floweaver.execute_weave_table` for a description of the
        columns.
    """
    from .compiler import compile_sankey_definition, execute_weave_table

    if isinstance(dataset, pd.DataFrame):
        dataset = Dataset(dataset)

    spec = compile_sankey_definition(
        sankey_definition,
        measures=measures,
        dimension_tables=dimension_tables,
    )
    return execute_weave_table(spec, dataset)


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
