import pytest
from floweaver.sankey_definition import Bundle, Elsewhere


def test_bundle_elsewhere():
    assert Bundle('a', 'b').to_elsewhere == False
    assert Bundle('a', 'b').from_elsewhere == False

    assert Bundle(Elsewhere, 'b').to_elsewhere == False
    assert Bundle(Elsewhere, 'b').from_elsewhere == True

    assert Bundle('a', Elsewhere).to_elsewhere == True
    assert Bundle('a', Elsewhere).from_elsewhere == False


def test_bundle_hashable():
    assert hash(Bundle('a', 'b'))


def test_bundle_to_self_allowed_only_if_flow_selection_specified():
    with pytest.raises(ValueError):
        Bundle('x', 'x')

    assert Bundle('x', 'x', flow_selection='...')
