import sentinel
import attr


Elsewhere = sentinel.create('Elsewhere')


@attr.s(slots=True)
class Bundle(object):
    source = attr.ib()
    target = attr.ib()
    waypoints = attr.ib(default=attr.Factory(tuple), convert=tuple)
    flow_selection = attr.ib(default=None)
    flow_partition = attr.ib(default=None)
    default_partition = attr.ib(default=None)

    @property
    def to_elsewhere(self):
        return self.target is Elsewhere

    @property
    def from_elsewhere(self):
        return self.source is Elsewhere
