import pandas as pd

from .layered_graph import MultiLayeredGraph, Ordering
from .partition import Partition, Group
from .sankey_definition import ProcessGroup


def results_graph(
    view_graph,
    bundle_flows,
    flow_partition=None,
    time_partition=None,
    measures="value",
    frame_partition=None,
):
    G = MultiLayeredGraph()
    groups = []

    # Add nodes to graph and to order
    layers = []
    for r, bands in enumerate(view_graph.ordering.layers):
        o = [[] for band in bands]
        for i, rank in enumerate(bands):
            for u in rank:
                attr = view_graph.nodes[u]
                node = attr["node"]
                group_nodes = []
                for x, xtitle in nodes_from_partition(u, node.partition):
                    o[i].append(x)
                    group_nodes.append(x)
                    if node.partition is None:
                        title = u if node.title is None else node.title
                    else:
                        title = xtitle
                    G.add_node(
                        x,
                        **{
                            "type": (
                                "process" if isinstance(node, ProcessGroup) else "group"
                            ),
                            "direction": node.direction,
                            "title": title,
                        },
                    )
                groups.append(
                    {
                        "id": u,
                        "type": (
                            "process" if isinstance(node, ProcessGroup) else "group"
                        ),
                        "title": node.title or "",
                        "nodes": group_nodes,
                    }
                )

                from_elsewhere_bundles = attr.get("from_elsewhere_bundles", [])
                if from_elsewhere_bundles:
                    flows = pd.concat(
                        [bundle_flows[bundle] for bundle in from_elsewhere_bundles]
                    )
                    gw = view_graph.get_node(u).partition
                    gf = None  # XXX gf = data.get('flow_partition') or flow_partition or None
                    gt = time_partition or None
                    edges = group_flows(
                        flows,
                        "__from_elsewhere_" + u,
                        None,
                        u,
                        gw,
                        gf,
                        gt,
                        measures,
                        frame_partition,
                    )
                    for _, w, m, d in edges:
                        d["bundles"] = from_elsewhere_bundles
                        # The source and target are irrelevant when stored on the node
                        G.nodes[w].setdefault("from_elsewhere_edges", []).append((m, d))

                to_elsewhere_bundles = attr.get("to_elsewhere_bundles", [])
                if to_elsewhere_bundles:
                    flows = pd.concat(
                        [bundle_flows[bundle] for bundle in to_elsewhere_bundles]
                    )
                    gv = view_graph.get_node(u).partition
                    gf = None  # XXX gf = data.get('flow_partition') or flow_partition or None
                    gt = time_partition or None
                    edges = group_flows(
                        flows,
                        u,
                        gv,
                        "__to_elsewhere_" + u,
                        None,
                        gf,
                        gt,
                        measures,
                        frame_partition,
                    )
                    for v, _, m, d in edges:
                        d["bundles"] = to_elsewhere_bundles
                        # The source and target are irrelevant when stored on the node
                        G.nodes[v].setdefault("to_elsewhere_edges", []).append((m, d))

        layers.append(o)

    G.ordering = Ordering(layers)

    # Add edges to graph
    for v, w, data in view_graph.edges(data=True):
        flows = pd.concat([bundle_flows[bundle] for bundle in data["bundles"]])
        gv = view_graph.get_node(v).partition
        gw = view_graph.get_node(w).partition
        gf = data.get("flow_partition") or flow_partition or None
        gt = time_partition or None
        edges = group_flows(flows, v, gv, w, gw, gf, gt, measures, frame_partition)
        for _, _, _, d in edges:
            d["bundles"] = data["bundles"]
        G.add_edges_from(edges)

    # remove unused nodes
    unused = [u for u, deg in G.degree if deg == 0]
    for u in unused:
        attr = G.nodes[u]
        if "from_elsewhere_edges" not in attr and "to_elsewhere_edges" not in attr:
            G.remove_node(u)

    # remove unused nodes from groups
    def filter_groups(g):
        if len(g["nodes"]) == 0:
            return False
        if len(g["nodes"]) == 1:
            # Treat empty string as equivalent to None - use group id for comparison
            return G.nodes[g["nodes"][0]]["title"] != (
                g["title"] if g["title"] else g["id"]
            )
        return True

    groups = [dict(g, nodes=[x for x in g["nodes"] if x not in unused]) for g in groups]
    groups = [g for g in groups if filter_groups(g)]

    return G, groups


def nodes_from_partition(u, partition):
    if partition is None:
        return [("{}^*".format(u), "*")]
    else:
        # _ -> other
        return [("{}^{}".format(u, value), value) for value in partition.labels + ["_"]]


def agg_one_group(agg):
    def data(group):
        result = group.groupby(lambda x: "").agg(agg)
        return {k: result[k].iloc[0] for k in result}

    return data


def group_flows(
    flows,
    v,
    partition1,
    w,
    partition2,
    flow_partition,
    time_partition,
    measures,
    frame_partition=None,
):
    if callable(measures):
        data = measures
    elif isinstance(measures, str):
        data = agg_one_group({measures: "sum"})
    elif isinstance(measures, list):
        data = agg_one_group({k: "sum" for k in measures})
    elif isinstance(measures, dict):
        data = agg_one_group(measures)
    else:
        raise ValueError("measure must be str, list, dict or callable")

    e = flows.copy()
    set_partition_keys(e, partition1, "k1", v + "^", process_side="source")
    set_partition_keys(e, partition2, "k2", w + "^", process_side="target")
    set_partition_keys(e, flow_partition, "k3", "")
    set_partition_keys(e, time_partition, "k4", "")
    if frame_partition is not None:
        return _group_frames(e, data, frame_partition)
    grouped = e.groupby(["k1", "k2", "k3", "k4"])

    return [
        (
            source,
            target,
            (material, time),
            {"measures": data(group), "original_flows": list(group.index)},
        )
        for (source, target, material, time), group in grouped
    ]


def set_partition_keys(df, partition, key_column, prefix, process_side=None):
    if partition is None:
        partition = Partition([Group("*", [])])
    df[key_column] = prefix + "_"  # other
    seen = df.index != df.index  # False
    for group in partition.groups:
        q = df.index == df.index  # True
        for dim, values in group.query:
            if dim.startswith("process") and process_side:
                dim = process_side + dim[7:]
            q = q & df[dim].isin(values)
        if any(q & seen):
            dup = df[q & seen]
            raise ValueError(
                "Duplicate values in group {} ({}): {}".format(
                    group,
                    process_side,
                    ", ".join(
                        ["{}-{}".format(e.source, e.target) for _, e in dup.iterrows()]
                    ),
                )
            )
        df.loc[q, key_column] = prefix + str(group.label)
        seen = seen | q


def frame_index(df, partition):
    """Index of the frame each flow belongs to, or -1 if it is in none.

    Like other partitions, a flow may belong to at most one frame's group. But
    unlike them there is no catch-all group: flows outside every frame are
    left out of the diagram, as if by a flow selection.
    """
    index = pd.Series(-1, index=df.index)
    for i, group in enumerate(partition.groups):
        q = pd.Series(True, index=df.index)
        for dim, values in group.query:
            if dim == "process" or dim.startswith("process."):
                raise ValueError(
                    "frame_partition cannot use 'process' dimensions; "
                    "use 'source' or 'target' instead"
                )
            q &= df[dim].isin(values)
        if (q & (index >= 0)).any():
            raise ValueError(
                f"flows belong to more than one frame (frame {group.label!r})"
            )
        index[q] = i
    return index


def frame_labels(partition):
    """Frame labels for a frame partition, as coordinate dicts.

    A group that selects one value of each dimension, and is labelled just by
    those values, gets the values themselves (so ``Partition.Simple("sample",
    [0, 1])`` gives ``{"sample": 0}``, and a product of partitions gives
    ``{"year": 2020, "sample": 3}``). Otherwise a group of one dimension gets
    ``{dimension: label}``, and anything else ``{"frame": label}``.
    """
    labels = []
    for g in partition.groups:
        single = g.query and all(len(values) == 1 for _, values in g.query)
        if single and g.label == "/".join(str(values[0]) for _, values in g.query):
            labels.append({dim: values[0] for dim, values in g.query})
        elif len(g.query) == 1:
            labels.append({g.query[0][0]: g.label})
        else:
            labels.append({"frame": g.label})
    return labels


def _group_frames(e, data, frame_partition):
    """Group flows into links as usual, with one set of measures per frame.

    Measures are computed separately for each frame's flows, so a custom
    measures function sees one frame at a time and returns plain values. Each
    measure becomes a list with one entry per frame, and ``original_flows`` a
    list of lists. A link with no flows in a frame has every measure 0 there.
    """
    n = len(frame_partition.groups)
    e["k5"] = frame_index(e, frame_partition)
    e = e[e["k5"] >= 0]
    result = []
    for (source, target, material, time), group in e.groupby(["k1", "k2", "k3", "k4"]):
        per_frame = dict(iter(group.groupby("k5")))
        computed = {i: data(per_frame[i]) for i in per_frame}
        keys = list(next(iter(computed.values())).keys())
        measures = {
            k: [computed[i][k] if i in computed else 0.0 for i in range(n)]
            for k in keys
        }
        original = [
            list(per_frame[i].index) if i in per_frame else [] for i in range(n)
        ]
        result.append(
            (
                source,
                target,
                (material, time),
                {"measures": measures, "original_flows": original},
            )
        )
    return result
