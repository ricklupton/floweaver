from floweaver.color_scales import CategoricalScale, QuantitativeScale
from floweaver.sankey_data import SankeyLink


def test_categorical_scale():
    link1 = SankeyLink('a', 'b', type='x')
    link2 = SankeyLink('a', 'b', type='y')

    # Default palette if not specified; same colour used consistently for the
    # same link.
    s = CategoricalScale('type')
    assert s(link1, {}) == '#FBB4AE'
    assert s(link1, {}) == '#FBB4AE'
    assert s(link2, {}) == '#B3CDE3'
    assert s(link1, {}) == '#FBB4AE'

    # If custom palette given, it cycles through the colours given. Same colour
    # is used consistently.
    s = CategoricalScale('type', palette=['Red', 'Green', 'Blue'])
    assert s(link1, {}) == 'Red'
    assert s(link2, {}) == 'Green'
    assert s(link1, {}) == 'Red'

    # If the domain is not specified explicitly, colours are assigned in the
    # order used. So this gives different results to the test above.
    s = CategoricalScale('type', palette=['Red', 'Green', 'Blue'])
    assert s(link2, {}) == 'Red'
    assert s(link1, {}) == 'Green'
    assert s(link2, {}) == 'Red'

    # If setting the domain explicitly, then the order the colours are used
    # doesn't matter.
    s = CategoricalScale('type', palette=['Red', 'Green', 'Blue'])
    s.set_domain(['x', 'y'])
    assert s(link2, {}) == 'Green'
    assert s(link1, {}) == 'Red'
    assert s(link2, {}) == 'Green'

    # Can pass a dict to set domain as well.
    s = CategoricalScale('type', palette={'x': 'Blue', 'y': 'Green', 'z': 'Red'})
    assert s(link2, {}) == 'Green'
    assert s(link1, {}) == 'Blue'
    assert s(link2, {}) == 'Green'


def test_categorical_scale_default():
    link1 = SankeyLink('a', 'b', type='x')
    link2 = SankeyLink('a', 'b', type='y')
    link3 = SankeyLink('a', 'b', type='z')

    # If no default given, cycles through colours given
    s = CategoricalScale('type', palette={'x': 'Red', 'y': 'Green'})
    assert s(link1, {}) == 'Red'
    assert s(link2, {}) == 'Green'
    assert s(link3, {}) == 'Red'

    # If default is given, use that for unspecified colours
    s = CategoricalScale('type', palette={'x': 'Red', 'y': 'Green'}, default='Black')
    assert s(link1, {}) == 'Red'
    assert s(link2, {}) == 'Green'
    assert s(link3, {}) == 'Black'

    # If default is given with a list, don't allow cycling
    s = CategoricalScale('type', palette=['Red'], default='Black')
    assert s(link1, {}) == 'Red'
    assert s(link2, {}) == 'Black'
    assert s(link3, {}) == 'Black'


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
