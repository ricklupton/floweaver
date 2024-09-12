# Module containing the functions for flow data set manipulation
from .sankey_data import SankeyLayout, SankeyData, SankeyNode, SankeyLink
from .sankey_definition import ProcessGroup, Bundle, Waypoint
## Helper function
def isNaN(num):
    return num != num

## Function that will assemble the nodes dictionary
def generate_nodes(node_def, group_by = 'id', node_uid = 'id', partition_groups = None):
    # Loop through the dictionary and find all distinct node types and add them to the node dictionary
    node_types = []
    nodes = {}
    group_lists = {}
    for node in node_def:
        # If NaN means the group_by field for that node is empty 
        if isNaN(node[group_by]):
            # Add the node_uid as a node since not a part of a group
            nodes[node[node_uid]] = ProcessGroup(node_uid + ' == "' + node[node_uid] + '"')
        
        elif node[group_by] not in node_types:
            nodes[node[group_by]] = ProcessGroup(group_by + ' == "' + node[group_by] + '"')
            
            # Populate the group_lists dictionary
            if partition_groups == 'all':
                group_lists[node[group_by]] = []
                group_lists[node[group_by]].append(node[node_uid])
                
            elif partition_groups and node[group_by] in partition_groups:
                group_lists[node[group_by]] = []
                group_lists[node[group_by]].append(node[node_uid])
                
            node_types.append(node[group_by])  
            
        # If the group_by already visited, need to add to the group_lists regardless
        else: 
            # Populate the group_lists dictionary
            if partition_groups == 'all':
                group_lists[node[group_by]].append(node[node_uid])
                
            elif partition_groups and node[group_by] in partition_groups:
                group_lists[node[group_by]].append(node[node_uid])
                
    # Now loop through group_lists and add all the partitions 
    for group in group_lists:
        nodes[group].partition = Partition.Simple('process', group_lists[group])

    return nodes

## Assemble the ordering array
def generate_ordering(node_def, group_by='id', node_uid='id'):
    # Will first loop through and determine the dimension for the ordering array
    layers = 0
    bands = 0
    for node in node_def:
        layers = max(layers,node['layer'])
        bands = max(bands,node['band'])

    ordering = [ [ [] for i in range(bands + 1) ] for i in range(layers + 1) ]

    # NOTE: This is limited to the assumption that all nodes in a group are in the same layer/band
    visited = []
    for node in node_def:
        
        if isNaN(node[group_by]):
            ordering[node['layer']][node['band']].append(node[node_uid])
        elif node[group_by] not in visited:
            visited.append(node[group_by])
            ordering[node['layer']][node['band']].append(node[group_by])
    
    return ordering

## Function that returns the ordering, nodes and bundles
def generate_waypoints_bundles(node_def, flows, ordering, nodes, group_by = 'id', node_uid = 'id'):
    # Function takes in everything required to make decisions and output updated definition
    
    # Generate a dictionary of nodes:layer pairs to increase code efficiency
    node_layers = {}
    for node in node_def:
        node_layers[node[node_uid]] = node['layer']
        
    # Generate a dictionary of nodes:bands pairs to increase code efficiency
    node_bands = {}
    for node in node_def:
        node_bands[node[node_uid]] = node['band']

    reverse_present = False # Variable declaring whether a reverse waypoint 'band' has been created
    
    bundles = [] #  Empty list for storing the bundles as they are generated
    
    # Generate a dictionary of nodes:group_by pairs to increase code efficiency
    node_group = {}
    for node in node_def:
        if isNaN(node[group_by]):
            node_group[node[node_uid]] = node[node_uid]
        else:
            node_group[node[node_uid]] = node[group_by]

    for flow in flows:
        
        # Create a flow_selection if required
        fs = 'source == "' + node_group[flow['source']] + 'L" and target == "' + node_group[flow['target']] + '"'
        
        # Store the node layers in variables for code clarity
        target = node_layers[flow['target']]
        source = node_layers[flow['source']]
        
        #print(node_group[flow['source']],node_group[flow['target']])
        
        # If the target is in the same or prior layer to the source
        if (target <= source) and (flow['source'] != flow['target']):
             
            #If this is the first reverse flow then add the reverse wp band
            if not reverse_present:
                reverse_present = True
                for layer in ordering:
                    layer.append([]) # Add an empty list, a new layer at the bottom
            
            # Will loop through all layers between the source and target inclusive adding the wps 
            for layer in range(target, source + 1):
                
                # If no reverse waypoint already added then add one for all required layers
                if not ordering[layer][-1]:
                    ordering[layer][-1].append('wp' + str(layer))
                    nodes['wp' + str(layer)] = Waypoint(direction='L', title = '')
            
            # If group is the same but the node is different need to add the flow selection
            if (node_group[flow['source']] == node_group[flow['target']]) and (Bundle(node_group[flow['source']],
                     node_group[flow['target']],
                     flow_selection = fs)) not in bundles:
                bundles.append(Bundle(node_group[flow['source']],
                                  node_group[flow['target']],
                                  flow_selection = fs))
            
            # If in the same layer then only one waypoint required 
            elif target == source and (Bundle(node_group[flow['source']],
                                           node_group[flow['target']],
                                           waypoints=['wp' + str(source)]) not in bundles):
                bundles.append(Bundle(node_group[flow['source']],
                                      node_group[flow['target']],
                                      waypoints=['wp' + str(source)]))
            
            # If the bundle isn't in the bundles list and the layers are not the same
            elif ((Bundle(node_group[flow['source']],
                         node_group[flow['target']],
                         waypoints=['wp' + str(source),'wp' + str(target)]) not in bundles) and
                target != source):
                bundles.append(Bundle(node_group[flow['source']],
                                      node_group[flow['target']],
                                      waypoints=['wp' + str(source),'wp' + str(target)]))
                   
        # If its not a reverse flow, will either be a long/short forward flow
        
        # First provide all the logic for a long flow (ie target-source > 1)
        elif (target - source) > 1:
            
            #Create a temporary waypoint list
            wp_list = []
            
            uid = 0 # Create a uid counter for the waypoint nodes
            # Loop through all the layers in between the source and target exclusive
            for layer in range(source + 1, target):
                
                wp_name = 'fwp' + node_group[flow['source']] + node_group[flow['target']] + str(uid) 
                
                # Check if corresponding waypoint already exists
                if wp_name not in ordering[layer][node_bands[flow['source']]]:
                    ordering[layer][node_bands[flow['source']]].append(wp_name)
                    nodes[wp_name] = Waypoint(direction='R', title = '')
                
                # Add the wp to the wp list for this flow
                wp_list.append(wp_name)
                uid += 1
                
            # Add the bundle with waypoints if not already existing
            if (Bundle(node_group[flow['source']],
                                      node_group[flow['target']],
                                      waypoints=wp_list)) not in bundles:
                bundles.append(Bundle(node_group[flow['source']],
                                      node_group[flow['target']],
                                      waypoints=wp_list))
                
        # For flows from a node to itself: 
        elif (Bundle(node_group[flow['source']],
                     node_group[flow['target']],
                     flow_selection = fs)) not in bundles and (flow['source'] == flow['target']):
            bundles.append(Bundle(node_group[flow['source']],
                                  node_group[flow['target']],
                                  flow_selection = fs))
                       
        # ELSE: if not a reverse or a long flow its going to be a normal short flow. Simple bundle
        elif (flow['source'] != flow['target']) and (Bundle(node_group[flow['source']],
                   node_group[flow['target']]) not in bundles):
            bundles.append(Bundle(node_group[flow['source']],
                                      node_group[flow['target']]))
        
    return ordering, nodes, bundles