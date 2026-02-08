from floweaver.compiler.rules import Rules, Includes, Excludes

def test_rules_equality():
    r1 = Rules([
        ({"x": Includes({"a"})}, "A"),
        ({"x": Includes({"b"})}, "B"),
    ])
    r2 = Rules([
        ({"x": Includes({"b"})}, "B"),
        ({"x": Includes({"a"})}, "A"),
    ])

    assert r1 == r2  # order independent


def test_rules_refine():
    rules = Rules([
        ({"x": Includes({"a", "b"})}, "AB"),
        ({"x": Includes({"b", "c"})}, "BC"),
    ])

    refined = rules.refine()

    assert refined == Rules([
        ({"x": Includes({"a"})}, ("AB",)),
        ({"x": Includes({"b"})}, ("AB", "BC")),
        ({"x": Includes({"c"})}, ("BC",)),
        ({"x": Excludes({"a", "b", "c"})}, ()),
    ])


def test_refine_with_excludes():
    rules = Rules([
        ({"x": Includes({"a"})}, "A"),
        ({"x": Excludes({"b"})}, "NotB"),
    ])

    refined = rules.refine()

    # x=a: both match (a in Includes, a not excluded by Excludes)
    # x=b: neither match (b not in Includes, b is excluded)
    # x=other: only NotB matches

    assert refined == Rules([
        ({"x": Includes({"a"})}, ("A", "NotB")),
        ({"x": Includes({"b"})}, ()),
        ({"x": Excludes({"a", "b"})}, ("NotB",)),
    ])
