import pytest
from floweaver.partition import Partition, Group


def test_group():
    g1 = Group('g1', [('dim1', ('v1', 'v2'))])
    g2 = Group('g2', [('dim2', ('x', ))])
    g3 = Group('g3', [('dim2', ('y', ))])
    assert g1.label == 'g1'
    assert g2.label == 'g2'
    assert g3.label == 'g3'

    G = Partition([g1, g2])
    assert G.labels == ['g1', 'g2']

    G1 = Partition([g1])
    G2 = Partition([g2, g3])

    Gsum = G1 + G2
    assert Gsum.groups == (g1, g2, g3)

    Gprod = G1 * G2
    assert Gprod.groups == (Group('g1/g2', (('dim1', ('v1', 'v2')),
                                            ('dim2', ('x', )))),
                            Group('g1/g3', (('dim1', ('v1', 'v2')),
                                            ('dim2', ('y', )))), )


def test_simple_partition():
    G = Partition.Simple('dim1', ['x', 'y'])
    assert G.labels == ['x', 'y']
    assert G.groups == (Group('x', [('dim1', ('x', ))]),
                        Group('y', [('dim1', ('y', ))]), )


def test_simple_partition_groups():
    G = Partition.Simple('dim1', ['x', ('group', ['y', 'z'])])
    assert G.labels == ['x', 'group']
    assert G.groups == (Group('x', [('dim1', ('x', ))]),
                        Group('group', [('dim1', ('y', 'z'))]), )


def test_partition_simple_checks_for_duplicates():
    with pytest.raises(ValueError):
        Partition.Simple('dim1', ['a', 'a'])

    with pytest.raises(ValueError):
        Partition.Simple('dim1', [
            ('label1', ['a', 'b']),
            'b'
        ])
