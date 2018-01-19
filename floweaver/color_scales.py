"""Color scales for Sankey diagrams.

author: Rick Lupton
created: 2018-01-19
"""

import numpy as np
from palettable.colorbrewer import qualitative, sequential

# From matplotlib.colours
def rgb2hex(rgb):
    'Given an rgb or rgba sequence of 0-1 floats, return the hex string'
    return '#%02x%02x%02x' % tuple([int(np.round(val * 255)) for val in rgb[:3]])


class CategoricalScale:
    def __init__(self, attr, palette=None):
        self.attr = attr
        self.palette, self.lookup = prep_qualitative_palette(palette)
        self._next = 0

    def set_domain(self, domain):
        self.lookup = {}
        self._next = 0
        for d in domain:
            self.lookup[d] = self.palette[self._next]
            self._next = (self._next + 1) % len(self.palette)

    def __call__(self, link, measures):
        palette = self.get_palette()
        value = self.get_value(link, measures)
        if value in self.lookup:
            return self.lookup[value]
        else:
            color = self.palette[self._next]
            self._next = (self._next + 1) % len(self.palette)
            self.lookup[value] = color
            return color

    def get_value(self, link, measures):
        if self.attr in ('source', 'target', 'type', 'time'):
            return getattr(link, self.attr)
        else:
            return measures[self.attr]

    def get_palette(self):
        return self.palette


def prep_qualitative_palette(palette):
    # qualitative colours based on material
    if palette is None:
        palette = 'Pastel1_8'

    if isinstance(palette, str):
        try:
            palette = getattr(qualitative, palette).hex_colors
        except AttributeError:
            raise ValueError('No qualitative palette called {}'.format(palette)) from None

    if isinstance(palette, dict):
        return palette.values(), palette
    else:
        return palette, {}

    # if not isinstance(palette, dict):
    #     materials = sorted(set([m for v, w, (m, t) in G.edges(keys=True)]))
    #     palette = {m: v
    #                 for m, v in zip(materials, itertools.cycle(palette))}


class QuantitativeScale:
    def __init__(self, attr, palette=None, intensity=None, domain=None):
        self.attr = attr
        self.palette = self._prep_palette(palette)
        self.domain = domain
        self.intensity = intensity

    def set_domain_from(self, data):
        values = np.array([
            # XXX need link here
            self.get_value(None, measures) for measures in data
        ])
        self.set_domain((values.min(), values.max()))

    def set_domain(self, domain):
        assert len(domain) == 2
        self.domain = domain

    def get_domain(self):
        return self.domain

    def _prep_palette(self, palette):
        if palette is None:
            palette = 'Reds_9'

        if isinstance(palette, str):
            try:
                palette = getattr(sequential, palette).mpl_colormap
            except AttributeError:
                raise ValueError('No sequential palette called {}'.format(palette)) from None

        return palette

    def get_palette(self):
        return self.palette

    def get_value(self, link, measures):
        return measures[self.attr]

    def __call__(self, link, measures):
        value = self.get_value(link, measures)
        if self.intensity is not None:
            value /= measures[self.intensity]
        if self.domain is not None:
            vmin, vmax = self.domain
            normed = (value - vmin) / (vmax - vmin)
        else:
            normed = value
        palette = self.get_palette()
        color = rgb2hex(palette(normed))
        return color
