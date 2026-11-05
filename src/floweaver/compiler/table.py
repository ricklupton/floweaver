"""Execute a WeaverSpec against flow data to produce a table of flows.

Where :func:`execute_weave` produces the drawable Sankey diagram (one link per
segment between adjacent Sankey nodes), :func:`execute_weave_table` produces a
tidy table describing the same flows end to end: each Bundle's flows are
summarised from their source (or Elsewhere) to their target (or Elsewhere),
with the visible Waypoints they pass through listed in a ``via`` column.

This is the level of detail a reader sees in the diagram, so it is suitable as
"source data" accompanying a published figure.
"""

import pandas as pd

from .combined_router import route_flow_paths

ELSEWHERE_LABEL = "(elsewhere)"
OTHER_LABEL = "(other)"
VIA_SEPARATOR = "; "

KEY_COLUMNS = [
    "source",
    "source_subgroup",
    "via",
    "target",
    "target_subgroup",
    "type",
    "time",
]


def execute_weave_table(spec, dataset):
    """Execute a WeaverSpec against flow data to produce a table of flows.

    Each row summarises the flows passing between one pair of endpoints in the
    diagram, by one route, of one flow type and time. Flows that look the same
    to a reader of the diagram are merged into one row, and each flow in the
    dataset contributes to at most one row.

    Parameters
    ----------
    spec : WeaverSpec
        The compiled spec with routing tree.
    dataset : Dataset or DataFrame
        The flow data.

    Returns
    -------
    DataFrame
        With columns:

        ``source``, ``target``
            The ProcessGroup at each end of the flow: its title, or its id if
            it has no title. ``"(elsewhere)"`` if the flow enters from, or
            leaves to, Elsewhere.
        ``source_subgroup``, ``target_subgroup``
            The ProcessGroup's partition group label, or blank if the
            ProcessGroup is not partitioned. The catch-all group is labelled
            ``"(other)"``. Partition labels that are blank in the diagram are
            replaced by the values the partition group selects.
        ``via``
            The visible Waypoints the flow passes through, in order, separated
            by ``"; "``. Waypoints with blank titles (and blank partition
            labels) are omitted. Partitioned Waypoints are shown as
            ``"{title}: {label}"``, or ``"{label}"`` if untitled. A flow that
            leaves the diagram to Elsewhere and re-enters elsewhere has
            ``"(elsewhere)"`` at that point.
        ``type``, ``time``
            The flow partition and time partition labels, or blank if not
            partitioned. The catch-all group is labelled ``"(other)"``.
        one column per measure
            Aggregated over all the flows in the row.
    """
    if hasattr(dataset, "_table"):
        flows = dataset._table
    else:
        flows = dataset

    labeller = _PathLabeller(spec)
    paths = route_flow_paths(flows, spec.routing_tree)

    index = []
    keys = []
    for path, rows in paths.items():
        key = labeller.path_key([spec.edges[i] for i in path])
        index.extend(rows)
        keys.extend([key] * len(rows))

    measure_columns = [m.column for m in spec.measures]
    if not index:
        return pd.DataFrame(columns=pd.Index(KEY_COLUMNS + measure_columns))

    row_index = pd.Index(index)
    key_df = pd.DataFrame(keys, columns=pd.Index(KEY_COLUMNS), index=row_index)
    measures_df = pd.DataFrame(index=row_index)
    for column in measure_columns:
        if column in flows.columns:
            measures_df[column] = flows.loc[index, column]
        else:
            measures_df[column] = 0.0

    table = (
        pd.concat([key_df, measures_df], axis=1)
        .groupby(KEY_COLUMNS, sort=False)
        .agg({m.column: m.aggregation for m in spec.measures})
        .reset_index()
    )
    return table


class _PathLabeller:
    """Convert a path of EdgeSpecs into a row key of display labels."""

    def __init__(self, spec):
        self.nodes = spec.nodes
        self.groups = {g.id: g for g in spec.groups}
        # Waypoints automatically added for implicit Elsewhere bundles share
        # their bundle's id, and are drawn with arrows rather than labels.
        self.implicit_waypoints = {
            b.id
            for b in spec.bundles
            if str(b.id).startswith("__")
            and (b.source == "Elsewhere" or b.target == "Elsewhere")
        }

    def path_key(self, edges):
        chains = self._split_chains(edges)
        if len(chains) == 1:
            (chain,) = chains
            source = self._endpoint(chain[0].source)
            target = self._endpoint(chain[-1].target)
            via = self._via(chain)
        elif len(chains) == 2:
            outgoing, incoming = self._order_pair(chains)
            source = self._endpoint(outgoing[0].source)
            target = self._endpoint(incoming[-1].target)
            via = self._via(outgoing) + [ELSEWHERE_LABEL] + self._via(incoming)
        else:
            raise ValueError(f"Unexpected flow path with {len(chains)} parts")

        return (
            source[0],
            source[1],
            VIA_SEPARATOR.join(via),
            target[0],
            target[1],
            _flow_label([e.type for e in edges]),
            _flow_label([e.time for e in edges]),
        )

    def _is_process(self, node_id):
        return node_id is not None and self.nodes[node_id].type == "process"

    def _split_chains(self, edges):
        """Split a path into chains, each running between ProcessGroups/Elsewhere.

        Within a Bundle, all intermediate nodes are Waypoints; a chain starts at
        a ProcessGroup or Elsewhere and ends at a ProcessGroup or Elsewhere.
        """
        chains = []
        current = []
        for edge in edges:
            if current and (edge.source is None or self._is_process(edge.source)):
                chains.append(current)
                current = []
            current.append(edge)
            if edge.target is None or self._is_process(edge.target):
                chains.append(current)
                current = []
        if current:
            chains.append(current)
        return chains

    def _order_pair(self, chains):
        """Return (to-Elsewhere chain, from-Elsewhere chain) for a pair match."""
        a, b = chains
        for outgoing, incoming in [(a, b), (b, a)]:
            if (
                self._is_process(outgoing[0].source)
                and not self._is_process(outgoing[-1].target)
                and not self._is_process(incoming[0].source)
                and self._is_process(incoming[-1].target)
            ):
                return outgoing, incoming
        raise ValueError("Unexpected flow path: expected a pair of Elsewhere bundles")

    def _endpoint(self, node_id):
        """(source/target label, subgroup label) for the end of a chain."""
        if not self._is_process(node_id):
            # Elsewhere: either a stub (None), or a chain starting/ending at a
            # Waypoint, which will be listed in `via`.
            return (ELSEWHERE_LABEL, "")
        node = self.nodes[node_id]
        group = self.groups[node.group]
        title = group.title if group.title.strip() else group.id
        return (title, self._subgroup_label(node_id))

    def _subgroup_label(self, node_id):
        node = self.nodes[node_id]
        if node_id == f"{node.group}^*":
            return ""
        if node_id == f"{node.group}^_":
            return OTHER_LABEL
        if node.title.strip():
            return node.title
        if node.values:
            return ", ".join(node.values)
        return node.title

    def _via(self, chain):
        """Labels of the visible Waypoints along a chain, in order."""
        sequence = []
        for edge in chain:
            for node_id in (edge.source, edge.target):
                if node_id is not None and (not sequence or sequence[-1] != node_id):
                    sequence.append(node_id)
        labels = [
            self._waypoint_label(node_id)
            for node_id in sequence
            if not self._is_process(node_id)
        ]
        return [label for label in labels if label is not None]

    def _waypoint_label(self, node_id):
        node = self.nodes[node_id]
        if node.group in self.implicit_waypoints:
            return None
        if node_id == f"{node.group}^*":
            # Unpartitioned: the compiler has already resolved the title
            # (falling back to the id if the title is None).
            label = node.title
            return label if label.strip() else None
        label = OTHER_LABEL if node_id == f"{node.group}^_" else node.title
        if not label.strip():
            return None
        group_title = self.groups[node.group].title
        return f"{group_title}: {label}" if group_title.strip() else label


def _flow_label(values):
    """Label for the flow type or time partition along a path."""
    labels = []
    for value in values:
        if value == "*":
            label = ""
        elif value == "_":
            label = OTHER_LABEL
        else:
            label = value
        if label not in labels:
            labels.append(label)
    return VIA_SEPARATOR.join(labels)
