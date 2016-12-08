"""Save Sankey data to JSON format.
"""


import json

from .sankey_view import sankey_view
from .graph_to_sankey import graph_to_sankey


def _convert_node(node):
    return {
        'id': node['id'],
        'title': node['title'],
        'direction': node['direction'],
        'hidden': node['visibility'] == 'hidden',
        'style': node['style'],
    }


def save_sankey_data(filename,
                     sankey_definition,
                     dataset,
                     palette=None,
                     measure='value'):
    """Save Sankey data to `filename`. Similar to show_sankey()."""

    graph, groups = sankey_view(sankey_definition, dataset, measure)
    value = graph_to_sankey(graph, groups, palette=palette)


    converted_data = {
        'order': value['order'],
        'nodes': [_convert_node(n) for n in value['nodes']],
        'links': value['links'],
    }

    with open(filename, 'wt') as f:
        json.dump({'format': 'sankey-v1', 'data': converted_data}, f)
