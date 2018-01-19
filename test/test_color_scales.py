from floweaver.color_scales import CategoricalScale, QuantitativeScale
from floweaver.sankey_data import SankeyLink


def test_categorical_scale():
    link1 = SankeyLink('a', 'b', type='x')
    link2 = SankeyLink('a', 'b', type='y')

    s = CategoricalScale('type')
    assert s(link1, {}) == '#FBB4AE'
    assert s(link1, {}) == '#FBB4AE'

    s = CategoricalScale('type', palette=['Red', 'Green', 'Blue'])
    assert s(link1, {}) == 'Red'
    assert s(link2, {}) == 'Green'
    assert s(link1, {}) == 'Red'

    s = CategoricalScale('type', palette=['Red', 'Green', 'Blue'])
    assert s(link2, {}) == 'Red'
    assert s(link1, {}) == 'Green'
    assert s(link2, {}) == 'Red'

    s = CategoricalScale('type', palette=['Red', 'Green', 'Blue'])
    s.set_domain(['x', 'y'])
    assert s(link2, {}) == 'Green'
    assert s(link1, {}) == 'Red'
    assert s(link2, {}) == 'Green'


def test_quantitative_scale():
    link = SankeyLink('a', 'b')

    s = QuantitativeScale('value', palette='Greys_9')
    s.set_domain((0, 10))
    assert s(link, {'value': 0}) == '#ffffff'
    # XXX not sure this is completely accurate scale
    # assert s(link, {'value': 5}) == '#888888'
    assert s(link, {'value': 10}) == '#000000'

    snorm = QuantitativeScale('property', intensity='value', palette='Greys_9')
    snorm.set_domain((0, 1))
    assert snorm(link, {'value': 5.0, 'property': 1.0}) ==  s(link, {'value': 2})
