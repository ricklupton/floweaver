"""Save Sankey data to JSON format.
"""


import json


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
