"""View flow data as Sankey diagrams."""

__version__ = '2.1.0-dev'

from .dataset import Dataset
from .partition import Partition, Group
from .sankey_definition import SankeyDefinition, ProcessGroup, Waypoint, Bundle, Elsewhere
from .view_graph import view_graph
from .results_graph import results_graph
from .augment_view_graph import elsewhere_bundles, augment
from .hierarchy import Hierarchy
from .sankey_data import SankeyData, SankeyLink, SankeyNode
from .color_scales import CategoricalScale, QuantitativeScale
from .weave import weave, weave_compiled
from .compiler import compile_sankey_definition, execute_weave
from .compiler import spec

__all__ = ['Dataset', 'Partition', 'Group', 'SankeyDefinition', 'ProcessGroup',
           'Waypoint', 'Bundle', 'Elsewhere', 'view_graph', 'results_graph',
           'elsewhere_bundles', 'augment', 'Hierarchy', 'weave', 'weave_compiled',
           'compile_sankey_definition', 'execute_weave', 'SankeyData', 'SankeyLink', 'SankeyNode',
           'CategoricalScale', 'QuantitativeScale']
