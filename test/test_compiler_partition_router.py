import pytest
from floweaver import (
    Partition,
    Group,
)
from floweaver.compiler.rules import Rules, Includes, Excludes
from floweaver.compiler.partition_router import (
    expand_partition,
    build_segment_routing,
    merge_segment_routings,
    EdgeKey,
)


def test_expand_partition_none():
    """No partition - everything goes to "*" group."""
    rules = expand_partition(None)
    assert rules == Rules(
        [
            ({}, "*"),
        ]
    )


def test_expand_partition_empty():
    """Empty partition - everything goes to default."""
    rules = expand_partition(Partition([]))
    assert rules == Rules(
        [
            ({}, "_"),
        ]
    )


def test_expand_partition_simple():
    partition = Partition.Simple("material", ["m", "n"])
    rules = expand_partition(partition)
    assert rules == Rules(
        [
            ({"material": Includes({"m"})}, "m"),
            ({"material": Includes({"n"})}, "n"),
            ({"material": Excludes({"m", "n"})}, "_"),
        ]
    )


def test_expand_partition_single_group():
    """Single group with default."""
    rules = expand_partition(Partition([Group("only", (("x", ["a"]),))]))
    assert rules == Rules(
        [
            ({"x": Includes({"a"})}, "only"),
            ({"x": Excludes({"a"})}, "_"),
        ]
    )


def test_expand_partition_disjoint_attributes():
    """Groups constrain different attributes - defaults need both."""
    partition = Partition(
        [
            Group("p", (("attr1", ["x"]),)),
            Group("q", (("attr2", ["y"]),)),
        ]
    )
    with pytest.raises(ValueError, match="Multiple labels.*'p', 'q'"):
        expand_partition(partition)


def test_expand_partition_multiple_values():
    """Group matching multiple values for one attribute."""
    rules = expand_partition(
        Partition(
            [
                Group("ab", (("x", ["a", "b"]),)),
                Group("c", (("x", ["c"]),)),
            ]
        )
    )
    assert rules == Rules(
        [
            ({"x": Includes({"a"})}, "ab"),
            ({"x": Includes({"b"})}, "ab"),
            ({"x": Includes({"c"})}, "c"),
            ({"x": Excludes({"a", "b", "c"})}, "_"),
        ]
    )


def test_expand_partition_label_prefix():
    """Label prefix applied to all labels."""
    rules = expand_partition(Partition.Simple("m", ["x", "y"]), label_prefix="node^")
    assert rules == Rules(
        [
            ({"m": Includes({"x"})}, "node^x"),
            ({"m": Includes({"y"})}, "node^y"),
            ({"m": Excludes({"x", "y"})}, "node^_"),
        ]
    )


def test_expand_partition_not_simple():
    partition = Partition(
        [
            Group("m", (("material", ["m"]),)),
            Group("n1", (("material", ["n"]), ("type", ["t1"]))),
            Group("n2+", (("material", ["n"]), ("type", ["t2", "t3"]))),
        ]
    )
    rules = expand_partition(partition)
    assert rules == Rules(
        [
            ({"material": Includes({"m"})}, "m"),
            ({"material": Includes({"n"}), "type": Includes({"t1"})}, "n1"),
            ({"material": Includes({"n"}), "type": Includes({"t2"})}, "n2+"),
            ({"material": Includes({"n"}), "type": Includes({"t3"})}, "n2+"),
            ({"material": Includes({"n"}), "type": Excludes({"t1", "t2", "t3"})}, "_"),
            ({"material": Excludes({"m", "n"})}, "_"),
        ]
    )


def test_expand_partition_three_attributes():
    """Complex case with three attributes, partial overlap."""
    partition = Partition(
        [
            Group("a", (("x", ["1"]), ("y", ["1"]))),
            Group("b", (("x", ["1"]), ("y", ["2"]))),
            Group("c", (("x", ["2"]), ("z", ["1"]))),
        ]
    )
    rules = expand_partition(partition)
    assert rules == Rules(
        [
            # Explicit rules
            ({"x": Includes({"1"}), "y": Includes({"1"})}, "a"),
            ({"x": Includes({"1"}), "y": Includes({"2"})}, "b"),
            ({"x": Includes({"2"}), "z": Includes({"1"})}, "c"),
            # Defaults - regions not covered:
            # x=1, y∉{1,2} (any z)
            # x=2, z∉{1} (any y)
            # x∉{1,2} (any y, z)
            ({"x": Includes({"2"}), "z": Excludes({"1"})}, "_"),
            ({"x": Includes({"1"}), "y": Excludes({"1", "2"})}, "_"),
            ({"x": Excludes({"1", "2"})}, "_"),
        ]
    )


@pytest.mark.parametrize("side", ["source", "target"])
def test_expand_partition_process_attr(side):
    """The attribute "process" should resolve to source/target"""
    groups = ["a1", "a2"]
    rules1 = expand_partition(Partition.Simple("process", groups), process_side=side)
    rules2 = expand_partition(Partition.Simple(side, groups))
    assert rules1 == rules2


def test_build_segment_routing():
    """
    Segment a->via:
    - source partition: split by "source" attribute into a1, a2
    - target partition: everything to default
    - material partition: split by "material" into m, else _
    - time partition: everything to default
    """
    seg1 = build_segment_routing(
        source_node="a",
        target_node="via",
        source_partition=Partition.Simple("source", ["a1", "a2"]),
        target_partition=None,
        material_partition=Partition.Simple("material", ["m"]),
    )

    assert seg1 == Rules(
        [
            (
                {"source": Includes({"a1"}), "material": Includes({"m"})},
                EdgeKey("a^a1", "via^*", "m", "*"),
            ),
            (
                {"source": Includes({"a1"}), "material": Excludes({"m"})},
                EdgeKey("a^a1", "via^*", "_", "*"),
            ),
            (
                {"source": Includes({"a2"}), "material": Includes({"m"})},
                EdgeKey("a^a2", "via^*", "m", "*"),
            ),
            (
                {"source": Includes({"a2"}), "material": Excludes({"m"})},
                EdgeKey("a^a2", "via^*", "_", "*"),
            ),
            (
                {"source": Excludes({"a1", "a2"}), "material": Includes({"m"})},
                EdgeKey("a^_", "via^*", "m", "*"),
            ),
            (
                {"source": Excludes({"a1", "a2"}), "material": Excludes({"m"})},
                EdgeKey("a^_", "via^*", "_", "*"),
            ),
        ]
    )


def test_build_segment_routing_target_partitioned():
    """
    Segment via->b:
    - source partition: everything to default
    - target partition: split by "material" into m, n (node b partitioned by material)
    - material partition: split by "material" into m, else _
    - time partition: everything to default
    """
    seg2 = build_segment_routing(
        source_node="via",
        target_node="b",
        source_partition=None,
        target_partition=Partition.Simple("material", ["m", "n"]),
        material_partition=Partition.Simple("material", ["m"]),
    )

    assert seg2 == Rules(
        [
            ({"material": Includes({"m"})}, EdgeKey("via^*", "b^m", "m", "*")),
            ({"material": Includes({"n"})}, EdgeKey("via^*", "b^n", "_", "*")),
            ({"material": Excludes({"m", "n"})}, EdgeKey("via^*", "b^_", "_", "*")),
        ]
    )


def test_build_segment_routing_elsewhere():
    """Test build_segment_routing with source or target being Elsewhere"""
    rules = build_segment_routing(
        source_node=None,
        target_node="b",
        target_partition=Partition.Simple("material", ["m", "n"]),
    )

    assert rules == Rules(
        [
            (
                {"material": Includes({"m"})},
                EdgeKey(None, "b^m", "*", "*"),
            ),
            (
                {"material": Includes({"n"})},
                EdgeKey(None, "b^n", "*", "*"),
            ),
            (
                {"material": Excludes({"m", "n"})},
                EdgeKey(None, "b^_", "*", "*"),
            ),
        ]
    )


def test_build_segment_routing_process_attr():
    """Test that 'process' resolves to source/target"""
    seg = build_segment_routing(
        source_node="a",
        target_node="b",
        source_partition=Partition.Simple("process", ["a1", "a2"]),
        target_partition=None,
    )

    assert seg == Rules(
        [
            (
                {"source": Includes({"a1"})},
                EdgeKey("a^a1", "b^*", "*", "*"),
            ),
            (
                {"source": Includes({"a2"})},
                EdgeKey("a^a2", "b^*", "*", "*"),
            ),
            (
                {"source": Excludes({"a1", "a2"})},
                EdgeKey("a^_", "b^*", "*", "*"),
            ),
        ]
    )

    seg = build_segment_routing(
        source_node="a",
        target_node="b",
        source_partition=None,
        target_partition=Partition.Simple("process", ["b1", "b2"]),
    )

    assert seg == Rules(
        [
            (
                {"target": Includes({"b1"})},
                EdgeKey("a^*", "b^b1", "*", "*"),
            ),
            (
                {"target": Includes({"b2"})},
                EdgeKey("a^*", "b^b2", "*", "*"),
            ),
            (
                {"target": Excludes({"b1", "b2"})},
                EdgeKey("a^*", "b^_", "*", "*"),
            ),
        ]
    )


def test_merge_segment_routings():
    """
    Merge a->via and via->b to get full routing.

    A data row flows through both segments, collecting an EdgeKey from each.
    """
    material_partition = Partition.Simple("material", ["m"])
    seg1 = build_segment_routing(
        source_node="a",
        target_node="via",
        source_partition=Partition.Simple("source", ["a1", "a2"]),
        target_partition=None,
        material_partition=material_partition,
    )

    seg2 = build_segment_routing(
        source_node="via",
        target_node="b",
        source_partition=None,
        target_partition=Partition.Simple("material", ["m", "n"]),
        material_partition=material_partition,
    )

    merged = merge_segment_routings(seg1, seg2)

    assert merged == Rules(
        [
            # source=a1, material=m
            (
                {"source": Includes({"a1"}), "material": Includes({"m"})},
                (EdgeKey("a^a1", "via^*", "m", "*"), EdgeKey("via^*", "b^m", "m", "*")),
            ),
            # source=a1, material=n
            (
                {"source": Includes({"a1"}), "material": Includes({"n"})},
                (EdgeKey("a^a1", "via^*", "_", "*"), EdgeKey("via^*", "b^n", "_", "*")),
            ),
            # source=a1, material=other
            (
                {"source": Includes({"a1"}), "material": Excludes({"m", "n"})},
                (EdgeKey("a^a1", "via^*", "_", "*"), EdgeKey("via^*", "b^_", "_", "*")),
            ),
            # source=a2, material=m
            (
                {"source": Includes({"a2"}), "material": Includes({"m"})},
                (EdgeKey("a^a2", "via^*", "m", "*"), EdgeKey("via^*", "b^m", "m", "*")),
            ),
            # source=a2, material=n
            (
                {"source": Includes({"a2"}), "material": Includes({"n"})},
                (EdgeKey("a^a2", "via^*", "_", "*"), EdgeKey("via^*", "b^n", "_", "*")),
            ),
            # source=a2, material=other
            (
                {"source": Includes({"a2"}), "material": Excludes({"m", "n"})},
                (EdgeKey("a^a2", "via^*", "_", "*"), EdgeKey("via^*", "b^_", "_", "*")),
            ),
            # source=other, material=m
            (
                {"source": Excludes({"a1", "a2"}), "material": Includes({"m"})},
                (EdgeKey("a^_", "via^*", "m", "*"), EdgeKey("via^*", "b^m", "m", "*")),
            ),
            # source=other, material=n
            (
                {"source": Excludes({"a1", "a2"}), "material": Includes({"n"})},
                (EdgeKey("a^_", "via^*", "_", "*"), EdgeKey("via^*", "b^n", "_", "*")),
            ),
            # source=other, material=other
            (
                {"source": Excludes({"a1", "a2"}), "material": Excludes({"m", "n"})},
                (EdgeKey("a^_", "via^*", "_", "*"), EdgeKey("via^*", "b^_", "_", "*")),
            ),
        ]
    )
