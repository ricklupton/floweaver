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


def test_quantitative_scale_custom_get_color():
    link1 = SankeyLink('a', 'b', type='red')
    link2 = SankeyLink('a', 'b', type='blue')

    class MyScale(QuantitativeScale):
        def get_color(self, link, value):
            return '{}{}'.format(link.type, value)
    s = MyScale('value')

    assert s(link1, {'value': 1}) == 'red1.0'
    assert s(link2, {'value': 1}) == 'blue1.0'


def test_quantitative_scale_custom_get_palette():
    link1 = SankeyLink('a', 'b', type='Reds_9')
    link2 = SankeyLink('a', 'b', type='Blues_9')

    class MyScale(QuantitativeScale):
        def get_palette(self, link):
            return self.lookup_palette_name(link.type)
    s = MyScale('value')

    assert s(link1, {'value': 1}) == '#67000d'
    assert s(link2, {'value': 1}) == '#08306b'


def test_quantitative_scale_custom_get_value():
    link = SankeyLink('a', 'b')

    class MyScale(QuantitativeScale):
        def get_value(self, link, measures):
            # subtract value from 1, as an example of a transformation
            return 1.0 - measures[self.attr]

    s_reversed = MyScale('value')
    s_normal = QuantitativeScale('value')

    assert s_reversed(link, {'value': 0.2}) == s_normal(link, {'value': 0.8})
