from .augment_view_graph import augment, elsewhere_bundles
from .view_graph import view_graph
from .results_graph import results_graph
from .view_definition import ViewDefinition


def sankey_view(view_definition, dataset, measure='value', agg_measures=None):

    # Calculate the view graph (adding dummy nodes)
    GV, implicit_waypoints = view_graph(view_definition)

    # Add implicit to/from Elsewhere bundles to the view definition to ensure
    # consistency.
    new_waypoints, new_bundles = elsewhere_bundles(view_definition)
    GV2 = augment(GV, new_waypoints, new_bundles)

    # XXX messy
    bundles2 = dict(view_definition.bundles, **new_bundles)

    # Get the flows selected by the bundles
    bundle_flows, unused_flows = dataset.apply_view(view_definition.nodes,
                                                    bundles2, view_definition.flow_selection)

    # Calculate the results graph (actual Sankey data)
    GR, groups = results_graph(GV2, bundle_flows,
                               flow_partition=view_definition.flow_partition,
                               time_partition=view_definition.time_partition,
                               measure=measure, agg_measures=agg_measures)

    return GR, groups
