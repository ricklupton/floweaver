"""Save Sankey data to JSON format.
"""


import json

from .sankey_view import sankey_view
from .graph_to_sankey import graph_to_sankey


def _convert_node(node):
    return {
        'id': node['id'],
        'title': node['title'],
        'metadata': {'direction': node['direction']},
        'style': {'hidden': node['visibility'] == 'hidden', 'type': node['style']},
    }


def save_sankey_data(filename,
                     sankey_definition,
                     dataset,
                     palette=None,
                     measure='value'):
    """Save Sankey data to `filename`. Similar to show_sankey()."""

    graph, groups = sankey_view(sankey_definition, dataset, measure)
    value = graph_to_sankey(graph, groups, palette=palette)

    with open(filename, 'wt') as f:
        json.dump(serialise_data(value), f)


def serialise_data(value, version='2'):
    """Serialise `value` returned by graph_to_sankey."""
    if version != '2':
        raise ValueError('Only version 2 is supported')
    return _value_version_2(value)


def _value_version_2(value):
    nodes = [
        dict(id=node['id'],
             title=node['title'],
             metadata=dict(direction=node['direction']),
             style=dict(hidden=(node['visibility'] == 'hidden')))
        for node in value['nodes']
    ]

    links = [
        {
            'source': link['source'],
            'target': link['target'],
            'type': link['type'],
            'data': dict(value=link['value']),
            'style': {'color': link['color']}
        }
        for link in value['links']
    ]

    return {
        'format': 'sankey-v2',
        'metadata': {
            'layers': value['order'],
        },
        'nodes': nodes,
        'links': links,
    }
