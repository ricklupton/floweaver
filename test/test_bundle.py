import pytest
from floweaver.sankey_definition import Bundle, Elsewhere


def test_bundle_elsewhere():
    assert Bundle('a', 'b').to_elsewhere is False
    assert Bundle('a', 'b').from_elsewhere is False

    assert Bundle(Elsewhere, 'b').to_elsewhere is False
    assert Bundle(Elsewhere, 'b').from_elsewhere is True

    assert Bundle('a', Elsewhere).to_elsewhere is True
    assert Bundle('a', Elsewhere).from_elsewhere is False


def test_bundle_hashable():
    assert hash(Bundle('a', 'b'))


def test_bundle_to_self_allowed_only_if_flow_selection_specified():
    with pytest.raises(ValueError):
        Bundle('x', 'x')

    assert Bundle('x', 'x', flow_selection='...')
