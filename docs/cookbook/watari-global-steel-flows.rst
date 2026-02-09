Global steel flows using the floweaver compiler
===============================================

Watari et al (2025) used floweaver to generate Sankey diagrams of steel flows for many countries and years.  Here is an example of using the floweaver compiler to define a :class:`WeaverSpec` representing the diagram structure, which can then be combined with the data for different countries and years later on-demand.

First, adapting `the code`_ for the Sankey Diagram Definition to include only the structure (removing the parts related to the specific data):

.. code-block:: python

    from floweaver import *

    # Define the nodes
    def create_nodes():
        nodes = {
            'Production of iron ore': ProcessGroup(['Production of iron ore'], title='Mine'),
            'Iron ore': ProcessGroup(['Iron ore'], title='Iron ore'),
            'Scrap steel': ProcessGroup(['Scrap steel'], title='Scrap steel'),
            'Imports of ore and scrap': ProcessGroup(['Imports of iron ore', 'Imports of scrap steel'], title='Imports'),
            'Exports of ore and scrap': ProcessGroup(['Exports of iron ore', 'Exports of scrap steel'], title='Exports'),
            'Pig iron': ProcessGroup(['Pig iron'], title='Pig iron'),
            'DRI': ProcessGroup(['DRI'], title='Direct reduced iron'),
            'Imports of pig and DRI': ProcessGroup(['Imports of pig iron', 'Imports of dri'], title='Imports'),
            'Exports of pig and DRI': ProcessGroup(['Exports of pig iron', 'Exports of dri'], title='Exports'),
            'BOF steel': ProcessGroup(['BOF steel'], title='BOF steel'),
            'EAF steel': ProcessGroup(['EAF steel'], title='EAF steel'),
            'Ingots and semis': ProcessGroup(['Ingots and semis'], title='Ingots and semis'),
            'Imports of ingots and semis': ProcessGroup(['Imports of ingots and semis'], title='Imports'),
            'Exports of ingots and semis': ProcessGroup(['Exports of ingots and semis'], title='Exports'),
            'Long products': ProcessGroup(['Long products'], title='Long products'),
            'Flat products': ProcessGroup(['Flat products'], title='Flat products'),
            'Imports of long and flat': ProcessGroup(['Imports of long products', 'Imports of flat products'], title='Imports'),
            'Exports of long and flat': ProcessGroup(['Exports of long products', 'Exports of flat products'], title='Exports'),
            'End-use goods': ProcessGroup(['End-use goods'], title='End-use goods'),
            'Imports of goods': ProcessGroup(['Imports of end-use goods'], title='Imports'),
            'Exports of goods': ProcessGroup(['Exports of end-use goods'], title='Exports'),
            'Stock': ProcessGroup(['Stock'], Partition.Simple('type', []), title='Stock'),
            'Loss': ProcessGroup(['Loss'], title='Loss'),
            'Loss_way1': Waypoint(title='', direction='R'),
            'Loss_way2': Waypoint(title='', direction='R'),
            'Scrap_way1': Waypoint(title='', direction='L'),
            'Scrap_way2': Waypoint(title='', direction='L'),
            'Scrap_way3': Waypoint(title='', direction='L'),
            'Reference flow start': ProcessGroup(['Reference flow start'], title='30 Mt'),
            'Reference flow end': ProcessGroup(['Reference flow end'], title=' ')
        }
        return nodes

    # Define the bundles
    def create_bundles():
        bundles = [
            Bundle('Production of iron ore', 'Iron ore'),
            Bundle('Imports of ore and scrap', 'Iron ore'),
            Bundle('Iron ore', 'Pig iron'),
            Bundle('Iron ore', 'DRI'),
            Bundle('Iron ore', 'Exports of ore and scrap'),
            Bundle('Imports of ore and scrap', 'Scrap steel'),
            Bundle('Scrap steel', 'Exports of ore and scrap'),
            Bundle('Scrap steel', 'BOF steel'),
            Bundle('Scrap steel', 'EAF steel'),
            Bundle('Imports of pig and DRI', 'Pig iron'),
            Bundle('Pig iron', 'Exports of pig and DRI'),
            Bundle('Pig iron', 'BOF steel'),
            Bundle('Pig iron', 'EAF steel'),
            Bundle('Imports of pig and DRI', 'DRI'),
            Bundle('DRI', 'Exports of pig and DRI'),
            Bundle('DRI', 'EAF steel'),
            Bundle('BOF steel', 'Ingots and semis'),
            Bundle('EAF steel', 'Ingots and semis'),
            Bundle('Imports of ingots and semis', 'Ingots and semis'),
            Bundle('Ingots and semis', 'Exports of ingots and semis'),
            Bundle('Ingots and semis', 'Long products'),
            Bundle('Ingots and semis', 'Flat products'),
            Bundle('Imports of long and flat', 'Long products'),
            Bundle('Long products', 'Exports of long and flat'),
            Bundle('Imports of long and flat', 'Flat products'),
            Bundle('Flat products', 'Exports of long and flat'),
            Bundle('Long products', 'End-use goods'),
            Bundle('Flat products', 'End-use goods'),
            Bundle('Imports of goods', 'End-use goods'),
            Bundle('End-use goods', 'Exports of goods'),
            Bundle('End-use goods', 'Stock'),
            Bundle('Scrap steel', 'Loss', waypoints=['Loss_way1', 'Loss_way2']),
            Bundle('Pig iron', 'Loss', waypoints=['Loss_way2']),
            Bundle('DRI', 'Loss', waypoints=['Loss_way2']),
            Bundle('BOF steel', 'Loss'),
            Bundle('EAF steel', 'Loss'),
            Bundle('Long products', 'Scrap steel', waypoints=['Scrap_way1']),
            Bundle('Flat products', 'Scrap steel', waypoints=['Scrap_way1']),
            Bundle('End-use goods', 'Scrap steel', waypoints=['Scrap_way2', 'Scrap_way1']),
            Bundle('Stock', 'Scrap steel', waypoints=['Scrap_way3', 'Scrap_way2', 'Scrap_way1']),
            Bundle('Reference flow start', 'Reference flow end'),
        ]
        return bundles

    # Define the ordering
    def create_ordering():
        ordering = [
        [['Imports of ore and scrap'],['Production of iron ore'], [],[],['Reference flow start']],
        [['Imports of pig and DRI'],['Iron ore', 'Scrap steel'],[],[],['Reference flow end']],
        [[],['Pig iron','DRI'],['Loss_way1'],[],['Exports of ore and scrap']],
        [['Imports of ingots and semis'],['BOF steel','EAF steel'],['Loss_way2'],[],['Exports of pig and DRI']],
        [['Imports of long and flat'],['Ingots and semis'],['Loss'],[],[]],
        [['Imports of goods'],['Long products','Flat products'],[],['Scrap_way1'],['Exports of ingots and semis']],
        [[],['End-use goods'],[],['Scrap_way2'],[ 'Exports of long and flat']],
        [[],['Stock'],[],['Scrap_way3'],['Exports of goods']],
        ]
        return ordering


    TYPES = [
        'Iron ore',
        'Pig iron',
        'DRI',
        'BOF steel',
        'EAF steel',
        'Ingots and semis',
        'Long products',
        'Flat products',
        'End-use goods',
        'Loss',
        'Generated scrap',
        'Scrap steel',
        'Balancing flows',
        'Reference',
    ]

    nodes = create_nodes()
    bundles = create_bundles()
    ordering = create_ordering()

    flow_partition = Partition.Simple("type", TYPES)
    sankey_definition = SankeyDefinition(nodes, bundles, ordering, flow_partition=flow_partition)

We also extract the colour scheme from the original code as a separate data file:

.. code-block:: json
   :caption: Colour scheme, saved to `palette.json`

    {
        "Iron ore": "#525252",
        "Pig iron": "#0868ac",
        "DRI": "#4eb3d3",
        "BOF steel": "#2b8cbe",
        "EAF steel": "#7bccc4",
        "Ingots and semis": "#a8ddb5",
        "Long products": "#ccebc5",
        "Flat products": "#e0f3db",
        "End-use goods": "#dfc27d",
        "Loss": "#f0f0f0",
        "Generated scrap": "#d9d9d9",
        "Scrap steel": "#d9d9d9",
        "Balancing flows": "#fb6a4a",
        "Reference": "#d9d9d9"
    }

This is then compiled to a spec file::

  python -m floweaver.compiler sdd.py --color-mapping palette.json -o spec.json.gz

(you can omit the ``.gz`` to get a plain uncompressed JSON file for easier inspection, but compression is recommended for actual use)

To test it, extract the data from one of the prepared data files (e.g. `this one`_) and save as a CSV, or use the ones linked here: :download:`watari-spec.json.gz` and :download:`watari-transformed-data-Japan-2019.csv`.  Then upload to the `executor demo`_ to see the rendered Sankey diagram.

.. _the code: https://github.com/takumawatari/steel-flows-sankey/blob/main/code/sankey_drawing.py

.. _this one: https://github.com/takumawatari/steel-flows-sankey/blob/main/data/transformed_data_2019.xlsx

.. _executor demo: ../execute-spec-demo/

References
----------

Watari, T. et al. (2025) Global stagnation and regional variations in steel recycling, Resources, Conservation and Recycling, 220, 108363, https://doi.org/10.1016/j.resconrec.2025.108363
