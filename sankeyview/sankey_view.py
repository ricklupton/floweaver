from .augment_view_definition import augment
from .view_graph import view_graph
from .results_graph import results_graph


def sankey_view(view_definition, dataset, return_unused_flows=False,
                return_bundle_flows=False):
    # Add implicit to/from Elsewhere bundles to the view definition to ensure
    # consistency.
    augmented_view = augment(view_definition)

    # Calculate the view graph (adding dummy nodes)
    GV, oV = view_graph(augmented_view)

    # Get the flows selected by the bundles
    bundle_flows, unused_flows = dataset.apply_view(augmented_view)

    # Calculate the results graph (actual Sankey data)
    GR, oR = results_graph(GV, oV, bundle_flows,
                           flow_grouping=view_definition.flow_grouping)

    result = (GR, oR)
    if return_unused_flows:
        result += (unused_flows,)
    if return_bundle_flows:
        result += (bundle_flows,)
    return result
