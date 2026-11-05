"""Tests for SankeyDefinition.frame_partition: per-frame link values."""

import pandas as pd
import pytest

from floweaver import (
    Bundle,
    Elsewhere,
    Partition,
    ProcessGroup,
    SankeyDefinition,
    Waypoint,
    weave,
    weave_compiled,
)

FLOWS = pd.DataFrame(
    [
        ("farm1", "James", "apples", 5, "2020"),
        ("farm1", "Mary", "bananas", 3, "2020"),
        ("farm2", "Fred", "apples", 4, "2020"),
        ("farm1", "compost", "apples", 2, "2020"),
        ("farm2", "compost", "bananas", 1, "2020"),
        ("James", "compost", "apples", 1, "2020"),
        ("Mary", "landfill", "bananas", 1, "2020"),
        ("farm2", "landfill", "apples", 2, "2020"),
        ("imports", "Fred", "bananas", 2, "2020"),
        ("compost", "soil", "apples", 3, "2020"),
        ("farm1", "James", "apples", 6, "2021"),
        ("farm2", "landfill", "apples", 1, "2021"),
    ],
    columns=["source", "target", "type", "value", "year"],
)


def sdd(frame_partition=None):
    nodes = {
        "farms": ProcessGroup(
            ["farm1", "farm2"],
            Partition.Simple("process", ["farm1", "farm2"]),
            title="Farms",
        ),
        "eat": ProcessGroup(["James", "Mary", "Fred"]),
        "compost": ProcessGroup(["compost"], title="Compost"),
        "landfill": ProcessGroup(["landfill"]),
        "way": Waypoint(Partition.Simple("type", ["apples", "bananas"])),
    }
    ordering = [[["farms"]], [["eat"], ["way"]], [["compost"]], [["landfill"]]]
    bundles = [
        Bundle("farms", "eat"),
        Bundle("farms", "compost", waypoints=["way"]),
        Bundle("eat", "compost"),
        Bundle("eat", "landfill"),
        Bundle("farms", "landfill"),
        Bundle(Elsewhere, "eat"),
        Bundle("compost", Elsewhere),
    ]
    return SankeyDefinition(
        nodes,
        bundles,
        ordering,
        flow_partition=Partition.Simple("type", ["apples", "bananas"]),
        frame_partition=frame_partition,
    )


def _samples():
    """Three samples of the 2020 flows, scaled 1, 1.5 and 2."""
    base = FLOWS[FLOWS.year == "2020"]
    return pd.concat(
        [base.assign(sample=i, value=base.value * (1 + i / 2)) for i in range(3)],
        ignore_index=True,
    )


def _frames(samples=(0, 1, 2)):
    return Partition.Simple("sample", samples)


def _all_links(data):
    """All links, including elsewhere links, keyed by (source, target, type, time)."""
    links = list(data.links)
    for node in data.nodes:
        links += node.from_elsewhere_links + node.to_elsewhere_links
    return {(l.source, l.target, l.type, l.time): l for l in links}


def _link(data, source, target, type):
    return _all_links(data)[(source, target, type, "*")]


def test_frame_partition_gives_vector_values():
    flows = _samples()
    data = weave(sdd(frame_partition=_frames()), flows)
    assert data.frames == [{"sample": 0}, {"sample": 1}, {"sample": 2}]
    link = _link(data, "farms^farm1", "eat^*", "apples")
    assert link.link_width == [5.0, 7.5, 10.0]
    assert link.data == {"value": [5, 7.5, 10]}
    # Original flows: one list per frame, indexing the dataset.
    assert len(link.original_flows) == 3
    for i, rows in enumerate(link.original_flows):
        assert set(flows.loc[rows, "sample"]) == {i}


def test_without_frame_partition_nothing_changes():
    data = weave(sdd(), FLOWS[FLOWS.year == "2020"])
    assert data.frames is None
    link = _link(data, "farms^farm1", "eat^*", "apples")
    assert link.link_width == 5.0
    assert link.data == {"value": 5}


def test_flows_outside_frames_are_excluded():
    """Thinning frames removes the excluded samples from the diagram entirely."""
    flows = pd.DataFrame(
        [
            ("a", "b", "x", 1, 0),
            ("a", "b", "x", 2, 1),
            ("a", "c", "x", 5, 1),  # only in sample 1
            ("a", "b", "x", 3, 2),
        ],
        columns=["source", "target", "type", "value", "sample"],
    )
    nodes = {
        "a": ProcessGroup(["a"]),
        "bc": ProcessGroup(["b", "c"], Partition.Simple("process", ["b", "c"])),
    }
    d = SankeyDefinition(
        nodes, [Bundle("a", "bc")], [["a"], ["bc"]], frame_partition=_frames([0, 2])
    )
    data = weave(d, flows)
    assert [(l.target, l.link_width) for l in data.links] == [("bc^b", [1.0, 3.0])]
    assert "bc^c" not in [n.id for n in data.nodes]


def test_each_frame_equals_weaving_that_frame_alone():
    """Frame i has the values of weaving with frame i's flows only; links absent
    from a frame are present with value 0."""
    flows = _samples()
    flows = flows[~((flows["sample"] == 1) & (flows.target == "landfill"))]
    framed = _all_links(weave(sdd(frame_partition=_frames()), flows))
    for i in range(3):
        alone = _all_links(weave(sdd(), flows[flows["sample"] == i]))
        assert set(alone) <= set(framed)
        for key, link in framed.items():
            expected = alone[key].link_width if key in alone else 0.0
            assert link.link_width[i] == expected, (i, key)
    landfill = [l for k, l in framed.items() if k[1] == "landfill^*"]
    assert landfill and all(l.link_width[1] == 0.0 for l in landfill)


def test_custom_measures_are_scalar_per_frame():
    calls = []

    def measures(group):
        calls.append(group["sample"].nunique())
        return {
            "value": group.value.sum(),
            "n_flows": len(group),
            "mean": group.value.mean(),
        }

    data = weave(
        sdd(frame_partition=_frames()),
        _samples(),
        measures=measures,
        link_width="value",
    )
    assert set(calls) == {1}, "each call sees one frame's flows"
    link = _link(data, "farms^farm1", "eat^*", "apples")
    assert link.data["n_flows"] == [1, 1, 1]
    assert link.data["mean"] == [5, 7.5, 10]
    assert link.link_width == [5.0, 7.5, 10.0]


def test_frame_labels():
    years_samples = Partition.Simple("year", ["2020", "2021"]) * Partition.Simple(
        "sample", [0, 1]
    )
    data = weave(sdd(frame_partition=years_samples), FLOWS.assign(sample=0))
    assert data.frames == [
        {"year": "2020", "sample": 0},
        {"year": "2020", "sample": 1},
        {"year": "2021", "sample": 0},
        {"year": "2021", "sample": 1},
    ]
    named = Partition.Simple("sample", [("low", [0, 1]), ("high", [2])])
    data = weave(sdd(frame_partition=named), _samples())
    assert data.frames == [{"sample": "low"}, {"sample": "high"}]
    link = _link(data, "farms^farm1", "eat^*", "apples")
    assert link.link_width == [12.5, 10.0]  # frame "low" sums samples 0 and 1


def test_frame_partition_errors():
    with pytest.raises(ValueError):
        weave(sdd(frame_partition=Partition.Simple("process", ["farm1"])), _samples())
    with pytest.raises(NotImplementedError):
        weave_compiled(sdd(frame_partition=_frames()), _samples())


def test_widget_json_uses_largest_frame():
    data = weave(sdd(frame_partition=_frames()), _samples())
    widget = data.to_json(format="widget")
    values = {
        (l["source"], l["target"], l["type"]): l["value"] for l in widget["links"]
    }
    assert values[("farms^farm1", "eat^*", "apples")] == 10.0


def test_to_code_includes_frame_partition():
    code = sdd(frame_partition=_frames()).to_code()
    assert "frame_partition = " in code
    assert "frame_partition=frame_partition" in code
