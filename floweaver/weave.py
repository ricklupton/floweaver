import attr
import numpy as np
import pandas as pd
import itertools
import json

from .dataset import Dataset
from sankeydata import SankeyData, SankeyNode, SankeyLink
from .augment_view_graph import augment, elsewhere_bundles
from .view_graph import view_graph
from .results_graph import results_graph
from .color_scales import CategoricalScale, QuantitativeScale

from palettable.colorbrewer import qualitative, sequential

try:
    from ipysankeywidget import SankeyWidget
    from ipywidgets import Layout, Output, VBox
    from IPython.display import display, clear_output
except ImportError:
    SankeyWidget = None


class FloweaverSankeyData(SankeyData):
    def to_json(self, filename=None):
        """Convert data to JSON-ready dictionary."""
        data = super().to_json()

        if filename is None:
            return data
        else:
            with open(filename, 'wt') as f:
                json.dump(data, f)

    def to_widget(self, width=700, height=500, margins=None,
                  align_link_types=False, debugging=False):

        if SankeyWidget is None:
            raise RuntimeError('ipysankeywidget is required')

        if margins is None:
            margins = {
                'top': 25,
                'bottom': 10,
                'left': 130,
                'right': 130,
            }

        widget = SankeyWidget(nodes=[self._node_to_widget(n) for n in self.nodes],
                              links=[self._link_to_widget(l) for l in self.links],
                              order=self.ordering,
                              groups=self.groups,
                              align_link_types=align_link_types,
                              layout=Layout(width=str(width), height=str(height)),
                              margins=margins)

        if debugging:
            output = Output()
            def callback(_, d):
                with output:
                    clear_output()
                if not d:
                    return
                link = [l for l in self.links
                        if l.source == d['source']
                        and l.target == d['target']
                        and l.type == d['type']]
                assert len(link) == 1
                link = link[0]
                with output:
                    display('Flows in dataset contributing to this link:')
                    if self.dataset:
                        display(self.dataset._table.loc[link.original_flows])
                    else:
                        display(link.original_flows)
            widget.on_link_clicked(callback)
            return VBox([widget, output])
        else:
            return widget

    def _node_to_widget(self, node):
        """Convert node to JSON-ready dictionary."""
        return {
            'id': node.id,
            'title': node.title if node.title is not None else node.id,
            'direction': node.direction.lower(),
            'hidden': node.hidden is True or node.title == '',
            'type': node.style if node.style is not None else 'default',
        }

    def _link_to_widget(self, link):
        """Convert link to JSON-ready dictionary."""
        return {
            'source': link.source,
            'target': link.target,
            'type': link.type,
            'time': link.time,
            'value': link.value,
            'title': link.title,
            'color': link.color,
            'opacity': link.opacity,
        }


# From matplotlib.colours
def rgb2hex(rgb):
    'Given an rgb or rgba sequence of 0-1 floats, return the hex string'
    return '#%02x%02x%02x' % tuple([int(np.round(val * 255)) for val in rgb[:3]])


def weave(sankey_definition,
          dataset,
          measures='value',
          link_width=None,
          link_color=None,
          palette=None):

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
        sankey_definition.nodes, bundles2, sankey_definition.flow_selection)

    # Calculate the results graph (actual Sankey data)
    GR, groups = results_graph(GV2,
                               bundle_flows,
                               flow_partition=sankey_definition.flow_partition,
                               time_partition=sankey_definition.time_partition,
                               measures=measures)

    # Default link width is same as default measure
    if link_width is None:
        if not isinstance(measures, str):
            raise ValueError(('If you set a complicated measure function, '
                              'you need to set link_width too.'))
        link_width = measures

    if callable(link_width):
        get_value = lambda link, measures: link_width(measures)
    elif isinstance(link_width, str):
        get_value = lambda link, measures: float(measures[link_width])
    else:
        raise ValueError('link_width must be a str or callable')

    # Default link color is categorical scale based on link type
    if link_color is None:
        link_color = CategoricalScale('type', palette=palette)
    elif isinstance(link_color, str):
        link_color = CategoricalScale(link_color, palette=palette)
    elif not callable(link_color):
        raise TypeError('link_color must be a str or callable')

    # Set domain for quantitative colors, if not already set
    if hasattr(link_color, 'set_domain_from'):
        link_color.set_domain_from([data['measures'] for _, _, data in GR.edges(data=True)])

    # Package result
    links = [
        make_link(get_value, link_color, v, w, m, t, data)
        for v, w, (m, t), data in GR.edges(keys=True, data=True)
    ]
    nodes = [
        make_node(u, data)
        for u, data in GR.nodes(data=True)
    ]
    result = FloweaverSankeyData(nodes, links, groups, GR.ordering.layers, dataset)

    return result


# maybe this function should be customisable?

def make_link(get_value, get_color, v, w, m, t, data):
    link = SankeyLink(
        source=v,
        target=w,
        type=m,
        time=t,
        title=str(m),
        original_flows=data['original_flows']
    )
    return attr.evolve(
        link,
        value=get_value(link, data['measures']),
        color=get_color(link, data['measures']),
    )


def make_node(u, data):
    return SankeyNode(
        id=u,
        title=data.get('title'),
        style=data.get('type'),
        direction=data.get('direction', 'R'),
        # XXX not setting hidden here -- should have logic here or in to_json()?
    )


def prep_qualitative_palette(G, palette):
    # qualitative colours based on material
    if palette is None:
        palette = 'Pastel1_8'

    if isinstance(palette, str):
        try:
            palette = getattr(qualitative, palette).hex_colors
        except AttributeError:
            raise ValueError('No qualitative palette called {}'.format(palette)) from None

    if not isinstance(palette, dict):
        materials = sorted(set([m for v, w, (m, t) in G.edges(keys=True)]))
        palette = {m: v
                    for m, v in zip(materials, itertools.cycle(palette))}
