import pytest
from floweaver.compiler.tree import build_tree, LeafNode, BranchNode
from floweaver.compiler.rules import Rules, Includes, Excludes


def test_build_tree_empty():
    """Empty rules produce a leaf with combined empty list."""
    tree = build_tree(Rules([]))
    assert tree == LeafNode(None)


def test_build_tree_single_rule():
    """Single rule produces branch with one value and default."""
    rules = Rules(
        [
            ({"x": Includes({"a"})}, "A"),
        ]
    )
    tree = build_tree(rules)

    assert tree == BranchNode(
        attr="x",
        branches={"a": LeafNode("A")},
        default=LeafNode(None),
    )


def test_build_tree_multiple_values():
    """Multiple values on same attribute."""
    rules = Rules(
        [
            ({"x": Includes({"a"})}, "A"),
            ({"x": Includes({"b"})}, "B"),
        ]
    )
    tree = build_tree(rules)

    assert tree == BranchNode(
        attr="x",
        branches={
            "a": LeafNode("A"),
            "b": LeafNode("B"),
        },
        default=LeafNode(None),
    )


def test_build_tree_multi_value_includes():
    """Includes with multiple values branches to each."""
    rules = Rules(
        [
            ({"x": Includes({"a", "b"})}, "AB"),
        ]
    )
    tree = build_tree(rules)

    assert tree == BranchNode(
        attr="x",
        branches={
            "a": LeafNode("AB"),
            "b": LeafNode("AB"),
        },
        default=LeafNode(None),
    )


def test_build_tree_with_excludes():
    """Excludes goes to default branch only."""
    rules = Rules(
        [
            ({"x": Includes({"a"})}, "A"),
            ({"x": Excludes({"a"})}, "NotA"),
        ]
    )
    tree = build_tree(rules)

    assert tree == BranchNode(
        attr="x",
        branches={"a": LeafNode("A")},
        default=LeafNode("NotA"),
    )


def test_build_tree_with_excludes_and_includes():
    rules = Rules(
        [
            ({"source": Includes({"p01"}), "target": Excludes({"p01"})}, "A"),
        ]
    )
    tree = build_tree(rules)

    assert tree == BranchNode(
        attr="source",
        branches={
            "p01": BranchNode(
                attr="target", branches={"p01": LeafNode(None)}, default=LeafNode("A")
            )
        },
        default=LeafNode(None),
    )


def test_build_tree_by_default_raises_on_multiple_values():
    rules = Rules(
        [
            ({"x": Includes({"a"})}, "A"),
            ({}, "Always"),
        ]
    )

    with pytest.raises(ValueError):
        tree = build_tree(rules)


def test_build_tree_no_constraint():
    """Rules with no constraint on attr go everywhere."""
    rules = Rules(
        [
            ({"x": Includes({"a"})}, "A"),
            ({}, "Always"),
        ]
    )
    tree = build_tree(rules, combine_values=lambda x: list(x))

    assert tree == BranchNode(
        attr="x",
        branches={"a": LeafNode(["A", "Always"])},
        default=LeafNode(["Always"]),
    )


def test_build_tree_two_attributes():
    """Two attributes produce nested branches."""
    rules = Rules(
        [
            ({"x": Includes({"a"}), "y": Includes({"1"})}, "A1"),
        ]
    )
    tree = build_tree(rules)

    # Default attr_order is sorted: ["x", "y"]
    assert tree == BranchNode(
        attr="x",
        branches={
            "a": BranchNode(
                attr="y",
                branches={"1": LeafNode("A1")},
                default=LeafNode(None),
            ),
        },
        default=LeafNode(None),
    )


def test_build_tree_custom_attr_order():
    """Custom attr_order changes nesting."""
    rules = Rules(
        [
            ({"x": Includes({"a"}), "y": Includes({"1"})}, "A1"),
        ]
    )
    tree = build_tree(rules, attr_order=["y", "x"])

    # y first, then x
    assert tree == BranchNode(
        attr="y",
        branches={
            "1": BranchNode(
                attr="x",
                branches={"a": LeafNode("A1")},
                default=LeafNode(None),
            ),
        },
        default=LeafNode(None),
    )


def test_build_tree_combine_values():
    """Custom combine_values transforms leaf contents."""
    rules = Rules(
        [
            ({"x": Includes({"a"})}, 1),
            ({"x": Includes({"a"})}, 2),
        ]
    )
    tree = build_tree(rules, combine_values=sum)

    assert tree == BranchNode(
        attr="x",
        branches={"a": LeafNode(3)},
        default=LeafNode(0),
    )


def test_build_tree_combine_values_first():
    """combine_values taking first element."""
    rules = Rules(
        [
            ({"x": Includes({"a"})}, "A"),
        ]
    )
    tree = build_tree(rules, combine_values=lambda vs: vs[0] if vs else None)

    assert tree == BranchNode(
        attr="x",
        branches={"a": LeafNode("A")},
        default=LeafNode(None),
    )
