import json

from flask import Flask, request, make_response

from .sankey_view import SankeyView, Elsewhere
from .node import Node
from .bundle import Bundle
from .dataset import Dataset

from flask.ext.cors import CORS


app = Flask(__name__)
CORS(app)

dataset = Dataset.load('fruit_dataset.h5')


def parse_json(s):
    o = json.loads(s)
    o['bundles'] = [Bundle(x['source'], x['target'], waypoints=x['waypoints'])
                    for x in o['bundles']]
    o['nodes'] = {x['id']: Node(x['rank'], x['depth'], query=x['selection'].split(','),
                                reversed=x.get('reversed', False))
                  for x in o['nodes']}
    return o


@app.route("/view")
def view():
    json_def = request.args.get('def', '{}')

    try:
        viewdef = parse_json(json_def)
    except Exception as err:
        return make_response(json.dumps({
            'error': 'Bad request: {}'.format(err)
        }), 400)

    try:
        v = SankeyView(viewdef['nodes'], viewdef['bundles'])
    except Exception as err:
        return make_response(json.dumps({
            'error': 'Error building view: {}'.format(err)
        }), 400)

    try:
        G, order = v.build(dataset)
        value = v.graph_to_sankey(G, order)
    except Exception as err:
        return make_response(json.dumps({
            'error': str(err)
        }), 400)

    print('----------')
    print(json.dumps(value, indent=2))
    print('----------')
    return json.dumps(value)


if __name__ == "__main__":
    app.run(debug=True)
