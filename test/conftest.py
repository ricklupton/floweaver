import pytest


# For testing, disable checks on bundles; allows to have waypoints defining
# structure without getting too many extra to/from bundles
@pytest.fixture
def disable_attr_validators():
    import attr
    attr.set_run_validators(False)
    yield None
    attr.set_run_validators(True)
