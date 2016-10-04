from .augment_view_graph import augment, elsewhere_bundles
from .view_graph import view_graph
from .results_graph import results_graph


def sankey_view(sankey_definition,
                dataset,
                measure='value',
                agg_measures=None):

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
                               measure=measure,
                               agg_measures=agg_measures)

    return GR, groups
