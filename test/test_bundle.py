from sankeyview.view_definition import ProcessGroup, Bundle, Elsewhere


def test_bundle_elsewhere():
    assert Bundle('a', 'b').to_elsewhere == False
    assert Bundle('a', 'b').from_elsewhere == False

    assert Bundle(Elsewhere, 'b').to_elsewhere == False
    assert Bundle(Elsewhere, 'b').from_elsewhere == True

    assert Bundle('a', Elsewhere).to_elsewhere == True
    assert Bundle('a', Elsewhere).from_elsewhere == False


def test_bundle_hashable():
    assert hash(Bundle('a', 'b'))
