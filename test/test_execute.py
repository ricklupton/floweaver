"""Tests for the execute_weave function.

These tests verify that the spec executor correctly:
- Filters flows using include/exclude filters
- Handles catch-all partition groups (exclude filters)
- Handles Elsewhere flows (source=None or target=None)
- Combines multiple filters (ProcessGroup selections + Bundle flow_selections)
- Aggregates measures correctly (sum, mean)
- Applies color scales (categorical, quantitative)
"""

import pandas as pd

from floweaver.compiler.rules import Rules, Includes
from floweaver.compiler.tree import LeafNode, build_tree
from floweaver.compiler.execute import (
    execute_weave,
    _aggregate,
    _apply_color,
    _interpolate_color,
)
from floweaver.compiler.spec import (
    WeaverSpec,
    NodeSpec,
    GroupSpec,
    EdgeSpec,
    MeasureSpec,
    DisplaySpec,
    CategoricalColorSpec,
    QuantitativeColorSpec,
)


# Helper to create a minimal WeaverSpec
def make_spec(
    nodes=None,
    groups=None,
    bundles=None,
    ordering=None,
    edges=None,
    measures=None,
    display=None,
    routing_tree=None,
):
    if nodes is None:
        nodes = {}
    if groups is None:
        groups = []
    if bundles is None:
        bundles = []
    if ordering is None:
        ordering = [[]]
    if edges is None:
        edges = []
    if measures is None:
        measures = [MeasureSpec(column='value', aggregation='sum')]
    if display is None:
        display = DisplaySpec(
            link_width='value',
            link_color=CategoricalColorSpec(
                attribute='type',
                lookup={'*': '#cccccc'},
                default='#cccccc',
            ),
        )
    if routing_tree is None:
        routing_tree = LeafNode(None)
    return WeaverSpec(
        version='1.0',
        nodes=nodes,
        groups=groups,
        bundles=bundles,
        ordering=ordering,
        edges=edges,
        measures=measures,
        display=display,
        routing_tree=routing_tree,
    )


# Helper to create a minimal EdgeSpec
def make_edge(source, target, type='*', time='*', bundle_ids=None):
    return EdgeSpec(
        source=source,
        target=target,
        type=type,
        time=time,
        bundle_ids=bundle_ids or [],
    )


class TestAggregate:
    """Tests for the _aggregate function."""

    def test_sum_aggregation(self):
        df = pd.DataFrame({
            'value': [1.0, 2.0, 3.0],
        })
        measures = [MeasureSpec(column='value', aggregation='sum')]
        result = _aggregate(df, measures)
        assert result == {'value': 6.0}

    def test_mean_aggregation(self):
        df = pd.DataFrame({
            'value': [1.0, 2.0, 3.0],
        })
        measures = [MeasureSpec(column='value', aggregation='mean')]
        result = _aggregate(df, measures)
        assert result == {'value': 2.0}

    def test_multiple_measures(self):
        df = pd.DataFrame({
            'calories': [100.0, 200.0, 300.0],
            'enjoyment': [1.0, 2.0, 3.0],
        })
        measures = [
            MeasureSpec(column='calories', aggregation='sum'),
            MeasureSpec(column='enjoyment', aggregation='mean'),
        ]
        result = _aggregate(df, measures)
        assert result == {'calories': 600.0, 'enjoyment': 2.0}

    def test_missing_column_returns_zero(self):
        df = pd.DataFrame({
            'other': [1.0, 2.0],
        })
        measures = [MeasureSpec(column='value', aggregation='sum')]
        result = _aggregate(df, measures)
        assert result == {'value': 0.0}


class TestApplyColor:
    """Tests for the _apply_color function."""

    def test_categorical_by_type(self):
        edge = make_edge('a', 'b', type='m')
        data = {'value': 10.0}
        display = DisplaySpec(
            link_width='value',
            link_color=CategoricalColorSpec(
                attribute='type',
                lookup={'m': '#ff0000', 'n': '#00ff00'},
                default='#cccccc',
            ),
        )
        color = _apply_color(edge, data, display)
        assert color == '#ff0000'

    def test_categorical_default_for_unknown(self):
        edge = make_edge('a', 'b', type='unknown')
        data = {'value': 10.0}
        display = DisplaySpec(
            link_width='value',
            link_color=CategoricalColorSpec(
                attribute='type',
                lookup={'m': '#ff0000'},
                default='#cccccc',
            ),
        )
        color = _apply_color(edge, data, display)
        assert color == '#cccccc'

    def test_categorical_by_source(self):
        edge = make_edge('node_a', 'node_b', type='*')
        data = {'value': 10.0}
        display = DisplaySpec(
            link_width='value',
            link_color=CategoricalColorSpec(
                attribute='source',
                lookup={'node_a': '#ff0000'},
                default='#cccccc',
            ),
        )
        color = _apply_color(edge, data, display)
        assert color == '#ff0000'

    def test_categorical_by_measure(self):
        edge = make_edge('a', 'b', type='*')
        data = {'value': 10.0, 'category': 'high'}
        display = DisplaySpec(
            link_width='value',
            link_color=CategoricalColorSpec(
                attribute='category',
                lookup={'high': '#ff0000', 'low': '#00ff00'},
                default='#cccccc',
            ),
        )
        color = _apply_color(edge, data, display)
        assert color == '#ff0000'

    def test_quantitative_color(self):
        edge = make_edge('a', 'b', type='*')
        data = {'value': 50.0}
        display = DisplaySpec(
            link_width='value',
            link_color=QuantitativeColorSpec(
                attribute='value',
                palette=['#ffffff', '#000000'],
                domain=(0.0, 100.0),
            ),
        )
        color = _apply_color(edge, data, display)
        # 50% between white and black should be gray
        assert color == '#7f7f7f' or color == '#808080'

    def test_quantitative_with_intensity(self):
        edge = make_edge('a', 'b', type='*')
        data = {'value': 50.0, 'total': 100.0}
        display = DisplaySpec(
            link_width='value',
            link_color=QuantitativeColorSpec(
                attribute='value',
                palette=['#ffffff', '#000000'],
                domain=(0.0, 1.0),
                intensity='total',
            ),
        )
        color = _apply_color(edge, data, display)
        # value/intensity = 50/100 = 0.5, domain is [0, 1], so 50% gray
        assert color == '#7f7f7f' or color == '#808080'


class TestInterpolateColor:
    """Tests for the _interpolate_color function."""

    def test_at_start(self):
        palette = ['#ff0000', '#00ff00', '#0000ff']
        color = _interpolate_color(palette, 0.0)
        assert color == '#ff0000'

    def test_at_end(self):
        palette = ['#ff0000', '#00ff00', '#0000ff']
        color = _interpolate_color(palette, 1.0)
        assert color == '#0000ff'

    def test_at_midpoint(self):
        palette = ['#ff0000', '#00ff00', '#0000ff']
        color = _interpolate_color(palette, 0.5)
        assert color == '#00ff00'

    def test_interpolation_between(self):
        palette = ['#000000', '#ffffff']
        color = _interpolate_color(palette, 0.5)
        # Should be approximately gray
        assert color in ['#7f7f7f', '#808080']


class TestExecuteWeave:
    """Tests for the main execute_weave function."""

    def test_basic_execution(self):
        """Test basic execution with two nodes and one edge."""
        nodes = {
            'a^*': NodeSpec(title='a', type='process', group='a', style='process', direction='R'),
            'b^*': NodeSpec(title='b', type='process', group='b', style='process', direction='R'),
        }
        groups = [
            GroupSpec(id='a', title='', nodes=['a^*']),
            GroupSpec(id='b', title='', nodes=['b^*']),
        ]
        edges = [
            make_edge('a^*', 'b^*') #, include={'source': ['a1'], 'target': ['b1']}),
        ]
        rules = Rules([
            ({"source": Includes({"a1"}), "target": Includes({"b1"})}, (0,)),
        ])
        tree = build_tree(rules, default_value=())
        spec = make_spec(
            nodes=nodes,
            groups=groups,
            ordering=[[['a^*']], [['b^*']]],
            edges=edges,
            routing_tree=tree
        )

        flows = pd.DataFrame({
            'source': ['a1', 'a1', 'x1'],
            'target': ['b1', 'b2', 'b1'],
            'value': [3.0, 2.0, 1.0],
        })

        result = execute_weave(spec, flows)

        assert len(result.links) == 1
        assert result.links[0].source == 'a^*'
        assert result.links[0].target == 'b^*'
        assert result.links[0].data['value'] == 3.0
        assert result.links[0].original_flows == [0]

#     def test_partition_expansion(self):
#         """Test execution with partitioned nodes."""
#         nodes = {
#             'a^*': NodeSpec(title='a', type='process', group='a', style='process', direction='R'),
#             'via^m': NodeSpec(title='m', type='group', group='via', style='group', direction='R'),
#             'via^n': NodeSpec(title='n', type='group', group='via', style='group', direction='R'),
#         }
#         groups = [
#             GroupSpec(id='a', title='', nodes=['a^*']),
#             GroupSpec(id='via', title='', nodes=['via^m', 'via^n']),
#         ]
#         edges = [
#             make_edge('a^*', 'via^m', include={'source': ['a1'], 'material': ['m']}),
#             make_edge('a^*', 'via^n', include={'source': ['a1'], 'material': ['n']}),
#         ]
#         spec = make_spec(
#             nodes=nodes,
#             groups=groups,
#             ordering=[[['a^*']], [['via^m', 'via^n']]],
#             edges=edges,
#         )

#         flows = pd.DataFrame({
#             'source': ['a1', 'a1'],
#             'target': ['b1', 'b1'],
#             'material': ['m', 'n'],
#             'value': [3.0, 2.0],
#         })

#         result = execute_weave(spec, flows)

#         assert len(result.links) == 2
#         links_by_target = {l.target: l for l in result.links}
#         assert links_by_target['via^m'].data['value'] == 3.0
#         assert links_by_target['via^n'].data['value'] == 2.0

#     def test_catch_all_partition_with_exclude(self):
#         """Test catch-all partition groups using exclude filters."""
#         nodes = {
#             'a^*': NodeSpec(title='a', type='process', group='a', style='process', direction='R'),
#             'via^m': NodeSpec(title='m', type='group', group='via', style='group', direction='R'),
#             'via^_': NodeSpec(title='', type='group', group='via', style='group', direction='R', hidden=True),
#         }
#         groups = [
#             GroupSpec(id='a', title='', nodes=['a^*']),
#             GroupSpec(id='via', title='', nodes=['via^m', 'via^_']),
#         ]
#         edges = [
#             # Edge to explicit partition value
#             make_edge('a^*', 'via^m', include={'source': ['a1'], 'material': ['m']}),
#             # Catch-all edge: include source selection, exclude explicit partition values
#             make_edge('a^*', 'via^_', include={'source': ['a1']}, exclude=[{'material': ['m']}]),
#         ]
#         spec = make_spec(
#             nodes=nodes,
#             groups=groups,
#             ordering=[[['a^*']], [['via^m', 'via^_']]],
#             edges=edges,
#         )

#         flows = pd.DataFrame({
#             'source': ['a1', 'a1', 'a1'],
#             'target': ['b1', 'b1', 'b1'],
#             'material': ['m', 'n', 'p'],
#             'value': [3.0, 2.0, 1.0],
#         })

#         result = execute_weave(spec, flows)

#         assert len(result.links) == 2
#         links_by_target = {l.target: l for l in result.links}
#         assert links_by_target['via^m'].data['value'] == 3.0
#         # Catch-all should get 'n' and 'p'
#         assert links_by_target['via^_'].data['value'] == 3.0  # 2 + 1
#         assert sorted(links_by_target['via^_'].original_flows) == [1, 2]

#     def test_from_elsewhere_flow(self):
#         """Test flows from elsewhere (source=None)."""
#         nodes = {
#             'a^*': NodeSpec(title='a', type='process', group='a', style='process', direction='R'),
#         }
#         groups = [
#             GroupSpec(id='a', title='', nodes=['a^*']),
#         ]
#         edges = [
#             # From elsewhere edge: source is None, target is a^*
#             EdgeSpec(
#                 id='from_elsewhere',
#                 source=None,
#                 target='a^*',
#                 type='*',
#                 time='*',
#                 include={'target': ['a1']},
#                 exclude=[{'source': ['b1']}],  # Exclude flows from covered sources
#                 bundles=['elsewhere_to_a'],
#             ),
#         ]
#         spec = make_spec(
#             nodes=nodes,
#             groups=groups,
#             ordering=[[['a^*']]],
#             edges=edges,
#         )

#         flows = pd.DataFrame({
#             'source': ['x1', 'b1'],
#             'target': ['a1', 'a1'],
#             'value': [5.0, 3.0],
#         })

#         result = execute_weave(spec, flows)

#         # No regular links, but node should have from_elsewhere_links
#         assert len(result.links) == 0
#         assert len(result.nodes) == 1
#         node = result.nodes[0]
#         assert node.id == 'a^*'
#         assert len(node.from_elsewhere_links) == 1
#         assert node.from_elsewhere_links[0].data['value'] == 5.0  # Only x1->a1

#     def test_to_elsewhere_flow(self):
#         """Test flows to elsewhere (target=None)."""
#         nodes = {
#             'a^*': NodeSpec(title='a', type='process', group='a', style='process', direction='R'),
#         }
#         groups = [
#             GroupSpec(id='a', title='', nodes=['a^*']),
#         ]
#         edges = [
#             # To elsewhere edge: source is a^*, target is None
#             EdgeSpec(
#                 id='to_elsewhere',
#                 source='a^*',
#                 target=None,
#                 type='*',
#                 time='*',
#                 include={'source': ['a1']},
#                 exclude=[{'target': ['b1']}],  # Exclude flows to covered targets
#                 bundles=['a_to_elsewhere'],
#             ),
#         ]
#         spec = make_spec(
#             nodes=nodes,
#             groups=groups,
#             ordering=[[['a^*']]],
#             edges=edges,
#         )

#         flows = pd.DataFrame({
#             'source': ['a1', 'a1'],
#             'target': ['x1', 'b1'],
#             'value': [5.0, 3.0],
#         })

#         result = execute_weave(spec, flows)

#         # No regular links, but node should have to_elsewhere_links
#         assert len(result.links) == 0
#         assert len(result.nodes) == 1
#         node = result.nodes[0]
#         assert node.id == 'a^*'
#         assert len(node.to_elsewhere_links) == 1
#         assert node.to_elsewhere_links[0].data['value'] == 5.0  # Only a1->x1

#     def test_multiple_include_filters(self):
#         """Test combining ProcessGroup selection with Bundle flow_selection."""
#         nodes = {
#             'a^*': NodeSpec(title='a', type='process', group='a', style='process', direction='R'),
#             'b^*': NodeSpec(title='b', type='process', group='b', style='process', direction='R'),
#         }
#         groups = [
#             GroupSpec(id='a', title='', nodes=['a^*']),
#             GroupSpec(id='b', title='', nodes=['b^*']),
#         ]
#         edges = [
#             # Edge with multiple include filters:
#             # - source selection: source in ['a1', 'a2']
#             # - target selection: target in ['b1', 'b2']
#             # - bundle flow_selection: material = 'm'
#             make_edge(
#                 'a^*', 'b^*',
#                 include={
#                     'source': ['a1', 'a2'],
#                     'target': ['b1', 'b2'],
#                     'material': ['m'],
#                 },
#             ),
#         ]
#         spec = make_spec(
#             nodes=nodes,
#             groups=groups,
#             ordering=[[['a^*']], [['b^*']]],
#             edges=edges,
#         )

#         flows = pd.DataFrame({
#             'source': ['a1', 'a1', 'a1', 'x1'],
#             'target': ['b1', 'b1', 'b3', 'b1'],
#             'material': ['m', 'n', 'm', 'm'],
#             'value': [3.0, 2.0, 1.0, 4.0],
#         })

#         result = execute_weave(spec, flows)

#         assert len(result.links) == 1
#         # Only the first row matches all filters
#         assert result.links[0].data['value'] == 3.0
#         assert result.links[0].original_flows == [0]

#     def test_no_matching_flows(self):
#         """Test that edges with no matching flows don't produce links."""
#         nodes = {
#             'a^*': NodeSpec(title='a', type='process', group='a', style='process', direction='R'),
#             'b^*': NodeSpec(title='b', type='process', group='b', style='process', direction='R'),
#         }
#         groups = [
#             GroupSpec(id='a', title='', nodes=['a^*']),
#             GroupSpec(id='b', title='', nodes=['b^*']),
#         ]
#         edges = [
#             make_edge('a^*', 'b^*', include={'source': ['nonexistent']}),
#         ]
#         spec = make_spec(
#             nodes=nodes,
#             groups=groups,
#             ordering=[[['a^*']], [['b^*']]],
#             edges=edges,
#         )

#         flows = pd.DataFrame({
#             'source': ['a1'],
#             'target': ['b1'],
#             'value': [3.0],
#         })

#         result = execute_weave(spec, flows)

#         assert len(result.links) == 0
#         assert len(result.nodes) == 0  # Unused nodes are filtered out

#     def test_unused_nodes_filtered_from_ordering(self):
#         """Test that unused nodes are filtered from the ordering."""
#         nodes = {
#             'a^*': NodeSpec(title='a', type='process', group='a', style='process', direction='R'),
#             'b^*': NodeSpec(title='b', type='process', group='b', style='process', direction='R'),
#             'c^*': NodeSpec(title='c', type='process', group='c', style='process', direction='R'),
#         }
#         groups = [
#             GroupSpec(id='a', title='', nodes=['a^*']),
#             GroupSpec(id='b', title='', nodes=['b^*']),
#             GroupSpec(id='c', title='', nodes=['c^*']),
#         ]
#         edges = [
#             make_edge('a^*', 'b^*', include={'source': ['a1'], 'target': ['b1']}),
#             # No edge to c^*
#         ]
#         spec = make_spec(
#             nodes=nodes,
#             groups=groups,
#             ordering=[[['a^*']], [['b^*']], [['c^*']]],
#             edges=edges,
#         )

#         flows = pd.DataFrame({
#             'source': ['a1'],
#             'target': ['b1'],
#             'value': [3.0],
#         })

#         result = execute_weave(spec, flows)

#         # c^* should be filtered out
#         assert result.ordering == Ordering([[['a^*']], [['b^*']]])

#     def test_mean_aggregation(self):
#         """Test mean aggregation for measures."""
#         nodes = {
#             'a^*': NodeSpec(title='a', type='process', group='a', style='process', direction='R'),
#             'b^*': NodeSpec(title='b', type='process', group='b', style='process', direction='R'),
#         }
#         groups = [
#             GroupSpec(id='a', title='', nodes=['a^*']),
#             GroupSpec(id='b', title='', nodes=['b^*']),
#         ]
#         edges = [
#             make_edge('a^*', 'b^*', include={'source': ['a1']}),
#         ]
#         spec = make_spec(
#             nodes=nodes,
#             groups=groups,
#             ordering=[[['a^*']], [['b^*']]],
#             edges=edges,
#             measures=[
#                 MeasureSpec(column='calories', aggregation='sum'),
#                 MeasureSpec(column='enjoyment', aggregation='mean'),
#             ],
#             display=DisplaySpec(
#                 link_width='calories',
#                 link_color=CategoricalColorSpec(
#                     attribute='type',
#                     lookup={'*': '#cccccc'},
#                     default='#cccccc',
#                 ),
#             ),
#         )

#         flows = pd.DataFrame({
#             'source': ['a1', 'a1', 'a1'],
#             'target': ['b1', 'b1', 'b1'],
#             'calories': [100.0, 200.0, 300.0],
#             'enjoyment': [1.0, 2.0, 3.0],
#         })

#         result = execute_weave(spec, flows)

#         assert len(result.links) == 1
#         assert result.links[0].data['calories'] == 600.0
#         assert result.links[0].data['enjoyment'] == 2.0
#         assert result.links[0].link_width == 600.0

#     def test_groups_only_include_multi_node_groups(self):
#         """Test that groups only appear when they have multiple used nodes."""
#         nodes = {
#             'a^*': NodeSpec(title='a', type='process', group='a', style='process', direction='R'),
#             'via^m': NodeSpec(title='m', type='group', group='via', style='group', direction='R'),
#             'via^n': NodeSpec(title='n', type='group', group='via', style='group', direction='R'),
#         }
#         groups = [
#             GroupSpec(id='a', title='', nodes=['a^*']),
#             GroupSpec(id='via', title='Via', nodes=['via^m', 'via^n']),
#         ]
#         edges = [
#             make_edge('a^*', 'via^m', include={'source': ['a1'], 'material': ['m']}),
#             make_edge('a^*', 'via^n', include={'source': ['a1'], 'material': ['n']}),
#         ]
#         spec = make_spec(
#             nodes=nodes,
#             groups=groups,
#             ordering=[[['a^*']], [['via^m', 'via^n']]],
#             edges=edges,
#         )

#         flows = pd.DataFrame({
#             'source': ['a1', 'a1'],
#             'target': ['b1', 'b1'],
#             'material': ['m', 'n'],
#             'value': [3.0, 2.0],
#         })

#         result = execute_weave(spec, flows)

#         # 'via' group should be in result because it has 2 used nodes
#         # 'a' group should not because it only has 1 node
#         assert len(result.groups) == 1
#         assert result.groups[0]['id'] == 'via'
#         assert result.groups[0]['nodes'] == ['via^m', 'via^n']

#     def test_with_dataset_object(self):
#         """Test execution with a Dataset object (not just DataFrame)."""
#         from floweaver.dataset import Dataset

#         nodes = {
#             'a^*': NodeSpec(title='a', type='process', group='a', style='process', direction='R'),
#             'b^*': NodeSpec(title='b', type='process', group='b', style='process', direction='R'),
#         }
#         groups = [
#             GroupSpec(id='a', title='', nodes=['a^*']),
#             GroupSpec(id='b', title='', nodes=['b^*']),
#         ]
#         edges = [
#             make_edge('a^*', 'b^*', include={'source': ['a1'], 'target': ['b1']}),
#         ]
#         spec = make_spec(
#             nodes=nodes,
#             groups=groups,
#             ordering=[[['a^*']], [['b^*']]],
#             edges=edges,
#         )

#         flows = pd.DataFrame({
#             'source': ['a1'],
#             'target': ['b1'],
#             'value': [3.0],
#         })
#         dataset = Dataset(flows)

#         result = execute_weave(spec, dataset)

#         assert len(result.links) == 1
#         assert result.links[0].data['value'] == 3.0
#         assert result.dataset is dataset

#     def test_multiple_bundles_same_edge(self):
#         """Test that multiple original flows are tracked correctly."""
#         nodes = {
#             'a^*': NodeSpec(title='a', type='process', group='a', style='process', direction='R'),
#             'b^*': NodeSpec(title='b', type='process', group='b', style='process', direction='R'),
#         }
#         groups = [
#             GroupSpec(id='a', title='', nodes=['a^*']),
#             GroupSpec(id='b', title='', nodes=['b^*']),
#         ]
#         edges = [
#             make_edge('a^*', 'b^*', include={'source': ['a1', 'a2'], 'target': ['b1']}),
#         ]
#         spec = make_spec(
#             nodes=nodes,
#             groups=groups,
#             ordering=[[['a^*']], [['b^*']]],
#             edges=edges,
#         )

#         flows = pd.DataFrame({
#             'source': ['a1', 'a2', 'a1'],
#             'target': ['b1', 'b1', 'b2'],
#             'value': [3.0, 2.0, 1.0],
#         })

#         result = execute_weave(spec, flows)

#         assert len(result.links) == 1
#         assert result.links[0].data['value'] == 5.0  # 3 + 2
#         assert sorted(result.links[0].original_flows) == [0, 1]

#     def test_complex_exclude_for_elsewhere(self):
#         """Test complex exclude patterns for elsewhere bundles."""
#         nodes = {
#             'a^*': NodeSpec(title='a', type='process', group='a', style='process', direction='R'),
#             'b^*': NodeSpec(title='b', type='process', group='b', style='process', direction='R'),
#         }
#         groups = [
#             GroupSpec(id='a', title='', nodes=['a^*']),
#             GroupSpec(id='b', title='', nodes=['b^*']),
#         ]
#         edges = [
#             # Regular edge a->b
#             make_edge('a^*', 'b^*', include={'source': ['a1'], 'target': ['b1']}),
#             # From-elsewhere to a: flows targeting a1, excluding sources already covered
#             EdgeSpec(
#                 id='elsewhere_to_a',
#                 source=None,
#                 target='a^*',
#                 type='*',
#                 time='*',
#                 include={'target': ['a1']},
#                 exclude=[{'source': ['b1']}],  # Exclude flows from b1
#                 bundles=['elsewhere_to_a'],
#             ),
#         ]
#         spec = make_spec(
#             nodes=nodes,
#             groups=groups,
#             ordering=[[['a^*']], [['b^*']]],
#             edges=edges,
#         )

#         flows = pd.DataFrame({
#             'source': ['a1', 'x1', 'b1'],
#             'target': ['b1', 'a1', 'a1'],
#             'value': [3.0, 5.0, 7.0],
#         })

#         result = execute_weave(spec, flows)

#         # Check regular link
#         assert len(result.links) == 1
#         assert result.links[0].data['value'] == 3.0

#         # Check from_elsewhere (should exclude b1->a1)
#         a_node = [n for n in result.nodes if n.id == 'a^*'][0]
#         assert len(a_node.from_elsewhere_links) == 1
#         assert a_node.from_elsewhere_links[0].data['value'] == 5.0  # Only x1->a1


# class TestColorScaleIntegration:
#     """Integration tests for color scale application."""

#     def test_categorical_colors_applied(self):
#         """Test that categorical colors are applied correctly."""
#         nodes = {
#             'a^*': NodeSpec(title='a', type='process', group='a', style='process', direction='R'),
#             'via^m': NodeSpec(title='m', type='group', group='via', style='group', direction='R'),
#             'via^n': NodeSpec(title='n', type='group', group='via', style='group', direction='R'),
#         }
#         groups = [
#             GroupSpec(id='a', title='', nodes=['a^*']),
#             GroupSpec(id='via', title='', nodes=['via^m', 'via^n']),
#         ]
#         edges = [
#             make_edge('a^*', 'via^m', type='m', include={'source': ['a1'], 'material': ['m']}),
#             make_edge('a^*', 'via^n', type='n', include={'source': ['a1'], 'material': ['n']}),
#         ]
#         spec = make_spec(
#             nodes=nodes,
#             groups=groups,
#             ordering=[[['a^*']], [['via^m', 'via^n']]],
#             edges=edges,
#             display=DisplaySpec(
#                 link_width='value',
#                 link_color=CategoricalColorSpec(
#                     attribute='type',
#                     lookup={'m': '#ff0000', 'n': '#00ff00'},
#                     default='#cccccc',
#                 ),
#             ),
#         )

#         flows = pd.DataFrame({
#             'source': ['a1', 'a1'],
#             'target': ['b1', 'b1'],
#             'material': ['m', 'n'],
#             'value': [3.0, 2.0],
#         })

#         result = execute_weave(spec, flows)

#         links_by_type = {l.type: l for l in result.links}
#         assert links_by_type['m'].color == '#ff0000'
#         assert links_by_type['n'].color == '#00ff00'
