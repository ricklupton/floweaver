# Module containing all the functions for Floweaver SDD optimisation
from mip import *
from functools import cmp_to_key
from attr import evolve
from ipysankeywidget import SankeyWidget
from ipywidgets import Layout, Output
from .sankey_data import SankeyLayout

# Function that returns the inputs required for the optimisation model to function
def model_inputs(sankey_data, group_nodes = False):

    ## Create the node band/layer sets for the model and a dictionary of node:{layer,band}
    order = sankey_data.ordering.layers
    node_layer_set = [ [] for i in range(len(order))]
    node_band_set = [ [ [] for i in range(len(order)) ] for i in range(len(order[0])) ]
    node_dict = {}
    for i in range(len(order)):
        for j in range(len(order[i])):
            for k in order[i][j]:
                # Append in correct locations 
                node_layer_set[i].append(k)
                node_band_set[j][i].append(k)
                # Add to the node_dict in correct location
                node_dict[k] = {'layer':i, 'band':j}
                
    ## Now need to create all the edge sets (main, exit, return)
    flows = sankey_data.links
    nodes = sankey_data.nodes
    edges = [ [] for i in range(len(order))] # Set of main edges by layer
    exit_edges = [ [] for i in range(len(order))] #  Set of exit edges by layer
    return_edges = [ [] for i in range(len(order))] # Set of main edges by layer
    edge_weight = {} # Empty dict for edge weights
    
    # Create a node_dir dictionary containing the node directions
    node_dir = {}
    for node in nodes:
        node_dir[node.id] = node.direction
    
    for flow in flows:
        
        sl = node_dict[flow.source]['layer'] # save source layer to variable
        tl = node_dict[flow.target]['layer'] # save target layer to variable
        
        # FIRST CONDITION: If the nodes are in the same layer then exit or return edge
        if sl == tl:
            
            # If the source node has a direction of 'L' then it will be a return node
            if node_dir[flow.source] == 'L':
                return_edges[sl].append((flow.source,flow.target))
                edge_weight[(flow.source,flow.target)] = flow.link_width
            # If the source node has a direction of 'R' then it will be an exit node
            else:
                exit_edges[sl].append((flow.source,flow.target))
                edge_weight[(flow.source,flow.target)] = flow.link_width
                
        else: # If not return/exit then just a normal edge to add to edges main
            
            # BUT need to have the lower layer node first so use if statements
            if sl < tl:
                edges[sl].append((flow.source,flow.target))
                edge_weight[(flow.source,flow.target)] = flow.link_width
            else:
                edges[tl].append((flow.target,flow.source))
                edge_weight[(flow.target,flow.source)] = flow.link_width
    
    # Wrap all the lists etc into a model inputs dictionary
    model_inputs = {
        'node_layer_set': node_layer_set,
        'node_band_set': node_band_set,
        'edges': edges,
        'exit_edges': exit_edges,
        'return_edges': return_edges,
        'edge_weight': edge_weight
    }
    
    # If the nodes are being grouped:
    if group_nodes:
        
        # Create the group_ordering list
        group_ordering = [ [] for layer in order ]
        groups = {}
        
        ##### LOOP THROUGH ALL THE LAYERS IN THE ORDER, IF ENDS WITH * THEN NOT A GROUP!
        # IN TURN ADD THE GROUPS TO THE ORDER, AND CONSTRUCT THE GROUPS, BY SPLITTING ON THE CARROT
        # Loop through all the layer indices
        for i in range(len(order)):
            
            # Loop through each band in each layer
            for band in order[i]:
                
                # Loop through each node within the band:
                for node in band:
                    
                    # Create temp variable of the node split 
                    temp = node.split('^')
                    # If the second item in the list is a * then its not part of a group, can ignore
                    if temp[1] != '*':
                        
                        # If the group not already in groups dictionary
                        if temp[0] not in groups.keys():
                            groups[temp[0]] = []
                        
                        # Add the node to the list
                        groups[temp[0]].append(node)
                        
                        # If the group not in the ordering, add it to the ordering
                        if temp[0] not in group_ordering[i]:
                            group_ordering[i].append(temp[0])
        
        # Add the two new model parameters to the model dict
        model_inputs['groups'] = groups
        model_inputs['group_ordering'] = group_ordering
    
    return model_inputs

## Function that takes in the inputs and optimises the model 
def optimise_node_order_model(model_inputs, group_nodes = False):

    # Raise an error if the 
    if group_nodes and ('group_ordering' or 'groups') not in model_inputs.keys():
        raise Exception('The provided model input does not contain the key \'node_groups')
    
    ### Define the model
    m = Model("sankey")
    
    # Unpack the model input dictionary
    node_layer_set = model_inputs['node_layer_set']
    node_band_set = model_inputs['node_band_set']
    edges = model_inputs['edges']
    exit_edges = model_inputs['exit_edges']
    return_edges = model_inputs['return_edges']
    edge_weight = model_inputs['edge_weight']
    
    # Create a list of all the node pairings in each layer
    pairs_by_layer = [[ (u1,u2) for u1 in layer 
                       for u2 in layer 
                       if u1 != u2 ] 
                      for layer in node_layer_set ]
    
    ### Binary Decision Variables Section

    # Create a dictionary of binary decision variables called 'x' containing the relative positions of the nodes in a layer
    x = { k: m.add_var(var_type=BINARY) for layer in pairs_by_layer for k in layer }
    
    # If utilising group_nodes then execute the following code
    if group_nodes:

        group_ordering = model_inputs['group_ordering']
        groups = model_inputs['groups']

        # Create a list of all the y binary variables (regarding the relative position of nodes to node groups)
        node_group_pairs = [ [] for layer in node_layer_set ]

        # The group_ordering is done by LAYER only - just like node_layer_set.
        for i in range(len(node_layer_set)):
            for U in group_ordering[i]:
                for u2 in node_layer_set[i]:
                    # Only add the pairing IF the node, u2 is not in the group U.
                    if u2 not in groups[U]:
                        node_group_pairs[i].append((U,u2))

        # Now generate all the binary variables 'y' for the relative position of node_groups and nodes 
        y = { k: m.add_var(var_type=BINARY) for layer in node_group_pairs for k in layer }
    
    # Create a dictionary of binary decision variables called 'c' containing whether any two edges cross
    c_main_main = { (u1v1,u2v2): m.add_var(var_type=BINARY) for Ek in edges for u1v1 in Ek for u2v2 in Ek
                   if u1v1 != u2v2 
                  }
    
    # Dictionary for binary decision variables for an 'exit' flow crossing with a 'forward' flow
    c_exit_forward = { (u1v1,u2wp): m.add_var(var_type=BINARY) for Ek in edges for Ee in exit_edges
                    # Check if the edges are in the same layer or not
                      if edges.index(Ek) == exit_edges.index(Ee)
                      for u1v1 in Ek for u2wp in Ee
                      # Ignore edges from the same starting node 'u'
                      if u1v1[0] != u2wp[0]
                     }
    
    # Dictionary of binary decision variables for the crossing of two 'exit' flows
    c_exit_exit = { (u1wp1,u2wp2): m.add_var(var_type=BINARY) for Ee in exit_edges for u1wp1 in Ee for u2wp2 in Ee
                   # Do not add variable for a flow crossing itself
                   if u1wp1 != u2wp2
                  }
    
    # Dictionary of binary decision variables for the crossing of return and forward flows
    c_return_forward = { (u1v1,wpv2): m.add_var(var_type=BINARY) for Ek in edges for Er in return_edges
                        # Check if the return flow is one layer in front of the forward flow
                        if edges.index(Ek) + 1 == return_edges.index(Er)
                        for u1v1 in Ek
                        for wpv2 in Er
                        # Ignore edges to the same 'v' node
                        if u1v1[1] != wpv2[1]
                       }
    
    # Dictionary of binary decision variables for the crossing of two 'return' flows
    c_return_return = { (wp1v1,wp2v2): m.add_var(var_type=BINARY) for Er in return_edges for wp1v1 in Er for wp2v2 in Er
                       # Do not add variable for a flow crossing itself
                       if wp1v1 != wp2v2
                      }
    
    # Objective Function

    # This cell contains the objective function in full, will need to latter be modified

    print(edge_weight[u1v1]*edge_weight[u2v2]*c_main_main[u1v1,u2v2] for (u1v1,u2v2) in c_main_main.keys())
    
    m.objective = minimize( # Area of main edge crossings
                           xsum(edge_weight[u1v1]*edge_weight[u2v2]*c_main_main[u1v1,u2v2]
                                for (u1v1,u2v2) in c_main_main.keys()) +
                            # Area of crossings between exit and main edges
                           xsum(edge_weight[u1v1]*edge_weight[u2wp]*c_exit_forward[u1v1,u2wp]
                                for (u1v1,u2wp) in c_exit_forward.keys()) +
                            # Area of crossings between exit edges
                           xsum(edge_weight[u1wp1]*edge_weight[u2wp2]*c_exit_exit[u1wp1,u2wp2]
                                for (u1wp1,u2wp2) in c_exit_exit.keys()) +
                            # Area of crossings between return and main edges
                           xsum(edge_weight[u1v1]*edge_weight[wpv2]*c_return_forward[u1v1,wpv2]
                                for (u1v1,wpv2) in c_return_forward.keys()) +
                            # Area of crossings between return edges
                           xsum(edge_weight[wp1v1]*edge_weight[wp2v2]*c_return_return[wp1v1,wp2v2]
                                for (wp1v1,wp2v2) in c_return_return.keys())
                          )

    ### Constraints section, the following cells will contain all the constraints to be added to the model

    # If grouping nodes generate the required constraints 
    if group_nodes:

        #########################################
        for i in range(len(node_layer_set)):
            for u1 in node_layer_set[i]:

                # First figure out what group u1 is in
                U = ''
                for group in groups:
                    if u1 in groups[group]:
                        U = group

                for u2 in node_layer_set[i]:

                    if U: # Check if U is an empty string, meaning not in a group

                        # Apply the constraint ONLY if u2 not in U
                        if u2 not in groups[U]:

                            # Add the constraint
                            m += (y[U,u2] == x[u1,u2])

    ## Constraints for the ordering variables 'x'
    layer_index = 0
    for layer in node_layer_set:
        for u1 in layer:
            for u2 in layer:
                # Do not refer a node to itself
                if u1 != u2:
                    # x is Binary, either u1 above u2 or u2 above u1 (total of the two 'x' values must be 1)
                    m += (x[u1,u2] + x[u2,u1] == 1)

                    ## Band constraints
                    # return the relative band positions of u1 and u2
                    for band in node_band_set:
                        # Find the band index for u1 and u2
                        if u1 in band[layer_index]:
                            u1_band = node_band_set.index(band)
                        if u2 in band[layer_index]:
                            u2_band = node_band_set.index(band)
                    # Determine 'x' values based off the band indices (note 0 is the highest band)
                    if u1_band < u2_band:
                        m += (x[u1,u2] == 1)
                    elif u1_band > u2_band:
                        m += (x[u1,u2] == 0)
                    # No else constraint necessary

                    ## Transitivity Constraints 
                    for u3 in layer:
                        if u1 != u3 and u2 != u3:
                            m += (x[u3,u1] >= x[u3,u2] + x[u2,u1] - 1)
        # Increment the current layer by 1
        layer_index += 1  

    ## Constraints for c_main_main
    for Ek in edges:
        for (u1,v1) in Ek:
            for (u2,v2) in Ek:
                # Only consider 'c' values for crossings where the edges are not the same and the start/end nodes are different
                if (u1,v1) != (u2,v2) and u1 != u2 and v1 != v2:
                    m += (c_main_main[(u1,v1),(u2,v2)] + x[u2,u1] + x[v1,v2] >= 1)
                    m += (c_main_main[(u1,v1),(u2,v2)] + x[u1,u2] + x[v2,v1] >= 1)
    
    ## Constraits for c_exit_forward
    for Ek in edges:
        for Ee in exit_edges:
            # Only consider the combinations of edges where the edges are in the same layer
            if edges.index(Ek) == exit_edges.index(Ee):
                for (u1,v1) in Ek:
                    for (u2,wp) in Ee:
                        # Only consider 'c' values for the crossings where the starting nodes is NOT the same
                        if u1 != u2:
                            m += (c_exit_forward[(u1,v1),(u2,wp)] + x[u2,u1] + x[u1,wp] >= 1)
                            m += (c_exit_forward[(u1,v1),(u2,wp)] + x[u1,u2] + x[wp,u1] >= 1)
                            
    ## Constraints for c_exit_exit
    for Ee in exit_edges:
        for (u1,wp1) in Ee:
            for (u2,wp2) in Ee:
                # Only consider 'c' values for the crossings where the start and waypoints are not the same
                if u1 != u2 and wp1 != wp2:
                    m += (c_exit_exit[(u1,wp1),(u2,wp2)] + x[u1,u2] + x[u2,wp1] + x[wp1,wp2] >= 1)
                    m += (c_exit_exit[(u1,wp1),(u2,wp2)] + x[u2,u1] + x[wp1,u2] + x[wp2,wp1] >= 1)
                    m += (c_exit_exit[(u1,wp1),(u2,wp2)] + x[u1,wp2] + x[wp2,wp1] + x[wp1,u2] >= 1)
                    m += (c_exit_exit[(u1,wp1),(u2,wp2)] + x[wp2,u1] + x[wp1,wp2] + x[u2,wp1] >= 1)
                    m += (c_exit_exit[(u1,wp1),(u2,wp2)] + x[wp1,u2] + x[u2,u1] + x[u1,wp2] >= 1)
                    m += (c_exit_exit[(u1,wp1),(u2,wp2)] + x[u2,wp1] + x[u1,u2] + x[wp2,u1] >= 1)
                    m += (c_exit_exit[(u1,wp1),(u2,wp2)] + x[wp1,wp2] + x[wp2,u1] + x[u1,u2] >= 1)
                    m += (c_exit_exit[(u1,wp1),(u2,wp2)] + x[wp2,wp1] + x[u1,wp2] + x[u2,u1] >= 1)
                    
    ## Constraints for c_return_forward
    for Ek in edges:
        for Er in return_edges:
            # Only consider 'c' values if the return flow is one layer in front of the forward flow
            if edges.index(Ek) + 1 == return_edges.index(Er):
                for (u1,v1) in Ek:
                    for (wp,v2) in Er:
                        # Only consider values where the final nodes are not the same
                        # AND the final node of the main flow is not the waypoint
                        if v1 != v2 and v1 != wp:
                            m += (c_return_forward[(u1,v1),(wp,v2)] + x[v2,v1] + x[v1,wp] >= 1)
                            m += (c_return_forward[(u1,v1),(wp,v2)] + x[v1,v2] + x[wp,v1] >= 1)

    ## Constraints for c_return_return
    for Er in return_edges:
        for (wp1,v1) in Er:
            for (wp2,v2) in Er:
                # Only consider edges where the waypoint and end nodes are not the same
                if wp1 != wp2 and v1 != v2:
                    m += (c_return_return[(wp1,v1),(wp2,v2)] + x[v1,v2] + x[v2,wp1] + x[wp1,wp2] >= 1)
                    m += (c_return_return[(wp1,v1),(wp2,v2)] + x[v2,v1] + x[wp1,v2] + x[wp2,wp1] >= 1)
                    m += (c_return_return[(wp1,v1),(wp2,v2)] + x[v1,wp2] + x[wp2,wp1] + x[wp1,v2] >= 1)
                    m += (c_return_return[(wp1,v1),(wp2,v2)] + x[wp2,v1] + x[wp1,wp2] + x[v2,wp1] >= 1)
                    m += (c_return_return[(wp1,v1),(wp2,v2)] + x[wp1,v2] + x[v2,v1] + x[v1,wp2] >= 1)
                    m += (c_return_return[(wp1,v1),(wp2,v2)] + x[v2,wp1] + x[v1,v2] + x[wp2,v1] >= 1)
                    m += (c_return_return[(wp1,v1),(wp2,v2)] + x[wp1,wp2] + x[wp2,v1] + x[v1,v2] >= 1)
                    m += (c_return_return[(wp1,v1),(wp2,v2)] + x[wp2,wp1] + x[v1,wp2] + x[v2,v1] >= 1)

    ### Optimise the Model using a ILP Solver
    
    status = m.optimize(max_seconds=5)
    
    ### Define a function that decodes the solution (i.e. compares nodes in a layer)

    def cmp_nodes(u1,u2):
        # If the optmimised x is >= 0.99 then u1 above u2 - thus u1 comes first
        if x[u1,u2].x >= 0.99:
            return -1
        else:
            return 1
        
    ### Return Solution

    # Optimised node order arranged in layers
    sorted_order = [ sorted(layer,key=cmp_to_key(cmp_nodes)) for layer in node_layer_set ]

    # Optimised order arranged in layers and bands
    banded_order = [[] for i in range(len(node_layer_set))]

    for i in range(len(node_layer_set)):
        start_index = 0
        for band in node_band_set:
            end_index = len(band[i]) + start_index
            banded_order[i].append(sorted_order[i][start_index:end_index])
            start_index = end_index
        
    return banded_order


def optimise_node_order(sankey_data, group_nodes=False):
    """Optimise node order to avoid flows crossings.

    Returns new version of `sankey_data` with updated `ordering`.
    """

    model = model_inputs(sankey_data, group_nodes=group_nodes)
    opt_order = optimise_node_order_model(model, group_nodes=group_nodes)
    new_sankey_data = evolve(sankey_data, ordering=opt_order)
    return new_sankey_data


# Create a function that creates all the required inputs for the straightness optimisation model 
def straightness_model(sankey_data):
    
    ## Create the node_layer_set
    order = sankey_data.ordering.layers
    node_layer_set = [ [] for i in range(len(order))]
    node_band_set = [ [] for i in range(len(order[0]))]
    node_dict = {}
    
    # loop through and add all the nodes into the node layer set
    for i in range(len(order)):
        for j in range(len(order[i])):
            for k in order[i][j]:
                # Append in correct locations 
                node_layer_set[i].append(k)
                node_band_set[j].append(k)
                # Add to the node_dict in correct location
                node_dict[k] = {'layer':i, 'band':j, 'w_in':0, 'w_out':0}
                
    # Create the flows list
    flows = sankey_data.links
    # Create the empty edges dictionary
    edges = []
    # Create edge weights dictionary
    edge_weight = {}
    
    for flow in flows:
        
        sl = node_dict[flow.source]['layer'] # save source layer to variable
        tl = node_dict[flow.target]['layer'] # save target layer to variable
        
        # Ensure we are only considering the forward/main flows
        if sl < tl:
            edges.append((flow.source,flow.target))
            edge_weight[(flow.source,flow.target)] = flow.link_width
            
    # Determine the 'node weights' by assertaining the maximum of either in or out of each node
    for flow in flows:
        
        # Calculate the maximum possible weight of each node 
        node_dict[flow.source]['w_out'] += flow.link_width
        node_dict[flow.target]['w_in'] += flow.link_width
        
    # Figure out the maximum weight and assign it to a dictionary of node weightings 
    node_weight = {}
    for node in node_dict:
        # Assign value of the max weight!
        node_weight[node] = max(node_dict[node]['w_in'], node_dict[node]['w_out'])
        
    model_inputs  = {
        'node_layer_set': node_layer_set,
        'node_band_set': node_band_set,
        'edges': edges,
        'edge_weight': edge_weight,
        'node_weight': node_weight
    }
    
    return model_inputs


# Define a new function for optimising the vertical position
def optimise_position_model(model_inputs, scale, wslb = 1):
    
    ### Define the model
    m = Model("sankey")
    
    # Unpack the model input dictionary
    node_layer_set = model_inputs['node_layer_set']
    node_band_set = model_inputs['node_band_set']
    edges = model_inputs['edges']
    edge_weight = model_inputs['edge_weight']
    node_weight = model_inputs['node_weight']
    
    y = { node: m.add_var(name=f'y[{node}]', var_type=CONTINUOUS) 
         for layer in node_layer_set for node in layer
        }
    
    # Create the white space variables 
    d = {}
    for i in range(len(node_layer_set)):
        
        # Add the base_line to first node variable
        d[('b',node_layer_set[i][0])] = m.add_var(var_type=CONTINUOUS, lb = 0)
        
        # loop through all the pairings
        for j in range(len(node_layer_set[i])):
            if j+1 != len(node_layer_set[i]):
                d[(node_layer_set[i][j],node_layer_set[i][j+1])] = m.add_var(var_type=CONTINUOUS, lb = wslb)
                
    # Create all the deviation variables
    s = {}
    for edge in edges:
        s[edge] = m.add_var(var_type=CONTINUOUS)
        
    # Create a list of all the node pairings in each layer
    pairs_by_layer = [[ (u1,u2) for u1 in layer 
                       for u2 in layer 
                       if u1 != u2 ] 
                      for layer in node_layer_set ]
    
    ### Binary Decision Variables Section
    # Create a dictionary of binary decision variables called 'x' containing the relative positions of the nodes in a layer
    x = { k: m.add_var(var_type=BINARY) for layer in pairs_by_layer for k in layer }

    ### Now go through and create the constraints
    
    ## First create the constraints linking y values to white_spaces and weights
    
    # Create the list of lists containing all the variables for each node y coord to perform xsum!
    node_lists = {}
    for layer in node_layer_set:
        
        # Loop through all the nodes in the layer and do it accordingly
        for i, node in enumerate(layer):
            node_lists[node] = []
            # All nodes require the baseline spacing
            node_lists[node].append(d[('b',layer[0])])
            if i != 0:
                # If not the first node, need to add whitespace for all prior node pairs and prior node weights
                for j in range(i):
                    # If i+1 is in range
                    #if j+1 != len(node_layer_set[i]):
                    if j+1 != len(layer):
                        # For each node up to i add the weight
                        node_lists[node].append(node_weight[layer[j]]*scale)
                        node_lists[node].append(d[(layer[j],layer[j+1])])
            # Now the list has been assembled add the constraint!
            m += (y[node] == xsum(node_lists[node][i] for i in range(len(node_lists[node]))))

    ## Constraints for the ordering variables 'x'
    layer_index = 0
    for layer in node_layer_set:
        for u1 in layer:
            for u2 in layer:
                # Do not refer a node to itself
                if u1 != u2:
                    # x is Binary, either u1 above u2 or u2 above u1 (total of the two 'x' values must be 1)
                    m += (x[u1,u2] + x[u2,u1] == 1)

                    u1_pos = node_layer_set[layer_index].index(u1)
                    u2_pos = node_layer_set[layer_index].index(u2)
                    
                    # Determine 'x' values based off the node position (note 0 is the highest)
                    if u1_pos < u2_pos:
                        m += (x[u1,u2] == 1)
                    elif u1_pos > u2_pos:
                        m += (x[u1,u2] == 0)
                    
                    ## Transitivity Constraints 
                    for u3 in layer:
                        if u1 != u3 and u2 != u3:
                            m += (x[u3,u1] >= x[u3,u2] + x[u2,u1] - 1)
        # Increment the current layer by 1
        layer_index += 1  
    
    ## Create all the straightness constraints
    # Loop through all the edges and add the two required constraints 
    for (u,v) in edges:
        index_v = [i for i, layers in enumerate(node_layer_set) if v in layers]
        index_u = [i for i, layers in enumerate(node_layer_set) if u in layers]
        layer_v = [j for j in node_layer_set[index_v[0]] if (u,j) in edges and j != v]
        layer_u = [j for j in node_layer_set[index_u[0]] if (j,v) in edges and j != u]
        
        if y[u] == y[v]:
            extra = 0
        else:
            extra = 100
        
        m += (s[(u,v)] >= y[u] - y[v] + extra + xsum(edge_weight[(u,w)]*x[w,v] for w in layer_v) - xsum(edge_weight[(w,v)]*x[u,w] for w in layer_u))
        m += (s[(u,v)] >= -(y[u] - y[v] + extra + xsum(edge_weight[(u,w)]*x[w,v] for w in layer_v) - xsum(edge_weight[(w,v)]*x[u,w] for w in layer_u)))
            
    ## Create all the band constraints (ie higher bands above lower bands)

    # Loop through the node_band_set and add all the nodes accordingly 
    # First loop through 
    for i, bandu in enumerate(node_band_set):
        for u in bandu:

            # Now for each 'u' node loop through all the other nodes
            for j, bandv in enumerate(node_band_set):
                for v in bandv:

                    # Only add the constraint if the second band is greater than the first
                    if j > i:
                        m += (y[v] >= y[u] + node_weight[u])

    ### OBJECTIVE FUNCTION: MINIMISE DEVIATION * FLOW WEIGHT
    m.objective = minimize( xsum(s[edge]*edge_weight[edge]**2 for edge in s.keys()) )

    # Run the model and optimise!
    status = m.optimize()

    ### Decode the solution by running through and creating simplified dictionary
    y_coordinates = {}
    for node in y:
        y_coordinates[node] = y[node].x

    return y_coordinates


def optimise_node_positions(sankey_data,
                            width=None,
                            height=None,
                            margins=None,
                            scale=None,
                            minimum_gap=10):
    """Optimise node positions to maximise straightness.

    Returns new version of `sankey_data` with `node_positions` set.
    """

    # Apply default margins if not specified
    if margins is None:
        margins = {}
    margins = {
        "top": 50,
        "bottom": 15,
        "left": 130,
        "right": 130,
        **margins,
    }

    if scale is None:
        # FIXME can optimise this too, if not specified? Or calculate from
        # `height` and `minimum_gap`, if specified.
        scale = 1

    # Optimise the y-coordinates of the nodes

    model = straightness_model(sankey_data)
    # FIXME this needs to know what scale we want to use?
    ys = optimise_position_model(model, scale, wslb=minimum_gap*scale)
    ys = {k: y + margins['top'] for k, y in ys.items()}

    # Work out appropriate diagram height, if not specified explicitly
    if height is None:
        max_y1 = max(y0 + model['node_weight'][k] for k, y0 in ys.items())
        height = max_y1 + margins['bottom']

    # X-coordinates

    n_layers = len(sankey_data.ordering.layers)

    # Work out appropriate diagram height, if not specified explicitly
    if width is None:
        # FIXME this could be smarter, and consider how much curvature there is:
        # if all flows are thin or relatively straight, the layers can be closer
        # together.
        width = 150 * (n_layers - 1) + margins['left'] + margins['right']

    # Ascertain the max possible space inc margins
    max_w = max(0, width - margins['left'] - margins['right'])
    xs = {
        node_id: margins['left'] + i / (n_layers - 1) * max_w
        for i, layer in enumerate(sankey_data.ordering.layers)
        for band in layer
        for node_id in band
    }

    # Overall layout
    node_positions = {
        node.id: [xs[node.id], ys[node.id]]
        for node in sankey_data.nodes
    }
    layout = SankeyLayout(width=width, height=height, scale=scale, node_positions=node_positions)
    return layout


# Code for running the multi-objective MIP model
def optimise_hybrid_model(straightness_model, 
                          crossing_model, 
                          group_nodes = False, 
                          wslb = 1,
                          wsub = 10,
                          crossing_weight = 0.5,
                          straightness_weight = 0.5):
    
    ### Define the model
    m = Model("sankey")
    
    ##########################################################################################################
    # MINIMISE THE CROSSINGS MODEL
    ##########################################################################################################
    
    # Raise an error if the 
    if group_nodes and ('group_ordering' or 'groups') not in crossing_model.keys():
        raise Exception('The provided model input does not contain the key \'node_groups')
    
    # Unpack the model input dictionary
    node_layer_set = crossing_model['node_layer_set']
    node_band_set = crossing_model['node_band_set']
    edges = crossing_model['edges']
    exit_edges = crossing_model['exit_edges']
    return_edges = crossing_model['return_edges']
    edge_weight = crossing_model['edge_weight']
    
    # Create a list of all the node pairings in each layer
    pairs_by_layer = [[ (u1,u2) for u1 in layer 
                       for u2 in layer 
                       if u1 != u2 ] 
                      for layer in node_layer_set ]
    
    ### Binary Decision Variables Section

    # Create a dictionary of binary decision variables called 'x' containing the relative positions of the nodes in a layer
    x = { k: m.add_var(var_type=BINARY) for layer in pairs_by_layer for k in layer }

    # If utilising group_nodes then execute the following code
    if group_nodes:

        group_ordering = crossing_model['group_ordering']
        groups = crossing_model['groups']

        # Create a list of all the y binary variables (regarding the relative position of nodes to node groups)
        node_group_pairs = [ [] for layer in node_layer_set ]

        # The group_ordering is done by LAYER only - just like node_layer_set.
        for i in range(len(node_layer_set)):
            for U in group_ordering[i]:
                for u2 in node_layer_set[i]:
                    # Only add the pairing IF the node, u2 is not in the group U.
                    if u2 not in groups[U]:
                        node_group_pairs[i].append((U,u2))

        # Now generate all the binary variables 'y' for the relative position of node_groups and nodes 
        g = { k: m.add_var(var_type=BINARY) for layer in node_group_pairs for k in layer }
    
    # Create a dictionary of binary decision variables called 'c' containing whether any two edges cross
    c_main_main = { (u1v1,u2v2): m.add_var(var_type=BINARY) for Ek in edges for u1v1 in Ek for u2v2 in Ek
                   if u1v1 != u2v2 
                  }
    
    # Dictionary for binary decision variables for an 'exit' flow crossing with a 'forward' flow
    c_exit_forward = { (u1v1,u2wp): m.add_var(var_type=BINARY) for Ek in edges for Ee in exit_edges
                    # Check if the edges are in the same layer or not
                      if edges.index(Ek) == exit_edges.index(Ee)
                      for u1v1 in Ek for u2wp in Ee
                      # Ignore edges from the same starting node 'u'
                      if u1v1[0] != u2wp[0]
                     }
    
    # Dictionary of binary decision variables for the crossing of two 'exit' flows
    c_exit_exit = { (u1wp1,u2wp2): m.add_var(var_type=BINARY) for Ee in exit_edges for u1wp1 in Ee for u2wp2 in Ee
                   # Do not add variable for a flow crossing itself
                   if u1wp1 != u2wp2
                  }
    
    # Dictionary of binary decision variables for the crossing of return and forward flows
    c_return_forward = { (u1v1,wpv2): m.add_var(var_type=BINARY) for Ek in edges for Er in return_edges
                        # Check if the return flow is one layer in front of the forward flow
                        if edges.index(Ek) + 1 == return_edges.index(Er)
                        for u1v1 in Ek
                        for wpv2 in Er
                        # Ignore edges to the same 'v' node
                        if u1v1[1] != wpv2[1]
                       }
    
    # Dictionary of binary decision variables for the crossing of two 'return' flows
    c_return_return = { (wp1v1,wp2v2): m.add_var(var_type=BINARY) for Er in return_edges for wp1v1 in Er for wp2v2 in Er
                       # Do not add variable for a flow crossing itself
                       if wp1v1 != wp2v2
                      }
    
    ### Constraints section, the following cells will contain all the constraints to be added to the model

    # If grouping nodes generate the required constraints 
    if group_nodes:

        for i in range(len(node_layer_set)):
            for u1 in node_layer_set[i]:

                # First figure out what group u1 is in
                U = ''
                for group in groups:
                    if u1 in groups[group]:
                        U = group

                for u2 in node_layer_set[i]:

                    if U: # Check if U is an empty string, meaning not in a group

                        # Apply the constraint ONLY if u2 not in U
                        if u2 not in groups[U]:

                            # Add the constraint
                            m += (g[U,u2] == x[u1,u2])

    ## Constraints for the ordering variables 'x'
    layer_index = 0
    for layer in node_layer_set:
        for u1 in layer:
            for u2 in layer:
                # Do not refer a node to itself
                if u1 != u2:
                    # x is Binary, either u1 above u2 or u2 above u1 (total of the two 'x' values must be 1)
                    m += (x[u1,u2] + x[u2,u1] == 1)

                    ## Band constraints
                    # return the relative band positions of u1 and u2
                    for band in node_band_set:
                        # Find the band index for u1 and u2
                        if u1 in band[layer_index]:
                            u1_band = node_band_set.index(band)
                        if u2 in band[layer_index]:
                            u2_band = node_band_set.index(band)
                    # Determine 'x' values based off the band indices (note 0 is the highest band)
                    if u1_band < u2_band:
                        m += (x[u1,u2] == 1)
                    elif u1_band > u2_band:
                        m += (x[u1,u2] == 0)
                    # No else constraint necessary

                    ## Transitivity Constraints 
                    for u3 in layer:
                        if u1 != u3 and u2 != u3:
                            m += (x[u3,u1] >= x[u3,u2] + x[u2,u1] - 1)
        # Increment the current layer by 1
        layer_index += 1  
    
    ## Constraints for c_main_main
    for Ek in edges:
        for (u1,v1) in Ek:
            for (u2,v2) in Ek:
                # Only consider 'c' values for crossings where the edges are not the same and the start/end nodes are different
                if (u1,v1) != (u2,v2) and u1 != u2 and v1 != v2:
                    m += (c_main_main[(u1,v1),(u2,v2)] + x[u2,u1] + x[v1,v2] >= 1)
                    m += (c_main_main[(u1,v1),(u2,v2)] + x[u1,u2] + x[v2,v1] >= 1)
    
    ## Constraits for c_exit_forward
    for Ek in edges:
        for Ee in exit_edges:
            # Only consider the combinations of edges where the edges are in the same layer
            if edges.index(Ek) == exit_edges.index(Ee):
                for (u1,v1) in Ek:
                    for (u2,wp) in Ee:
                        # Only consider 'c' values for the crossings where the starting nodes is NOT the same
                        if u1 != u2:
                            m += (c_exit_forward[(u1,v1),(u2,wp)] + x[u2,u1] + x[u1,wp] >= 1)
                            m += (c_exit_forward[(u1,v1),(u2,wp)] + x[u1,u2] + x[wp,u1] >= 1)
                            
    ## Constraints for c_exit_exit
    for Ee in exit_edges:
        for (u1,wp1) in Ee:
            for (u2,wp2) in Ee:
                # Only consider 'c' values for the crossings where the start and waypoints are not the same
                if u1 != u2 and wp1 != wp2:
                    m += (c_exit_exit[(u1,wp1),(u2,wp2)] + x[u1,u2] + x[u2,wp1] + x[wp1,wp2] >= 1)
                    m += (c_exit_exit[(u1,wp1),(u2,wp2)] + x[u2,u1] + x[wp1,u2] + x[wp2,wp1] >= 1)
                    m += (c_exit_exit[(u1,wp1),(u2,wp2)] + x[u1,wp2] + x[wp2,wp1] + x[wp1,u2] >= 1)
                    m += (c_exit_exit[(u1,wp1),(u2,wp2)] + x[wp2,u1] + x[wp1,wp2] + x[u2,wp1] >= 1)
                    m += (c_exit_exit[(u1,wp1),(u2,wp2)] + x[wp1,u2] + x[u2,u1] + x[u1,wp2] >= 1)
                    m += (c_exit_exit[(u1,wp1),(u2,wp2)] + x[u2,wp1] + x[u1,u2] + x[wp2,u1] >= 1)
                    m += (c_exit_exit[(u1,wp1),(u2,wp2)] + x[wp1,wp2] + x[wp2,u1] + x[u1,u2] >= 1)
                    m += (c_exit_exit[(u1,wp1),(u2,wp2)] + x[wp2,wp1] + x[u1,wp2] + x[u2,u1] >= 1)
                    
    ## Constraints for c_return_forward
    for Ek in edges:
        for Er in return_edges:
            # Only consider 'c' values if the return flow is one layer in front of the forward flow
            if edges.index(Ek) + 1 == return_edges.index(Er):
                for (u1,v1) in Ek:
                    for (wp,v2) in Er:
                        # Only consider values where the final nodes are not the same
                        # AND the final node of the main flow is not the waypoint
                        if v1 != v2 and v1 != wp:
                            m += (c_return_forward[(u1,v1),(wp,v2)] + x[v2,v1] + x[v1,wp] >= 1)
                            m += (c_return_forward[(u1,v1),(wp,v2)] + x[v1,v2] + x[wp,v1] >= 1)

    ## Constraints for c_return_return
    for Er in return_edges:
        for (wp1,v1) in Er:
            for (wp2,v2) in Er:
                # Only consider edges where the waypoint and end nodes are not the same
                if wp1 != wp2 and v1 != v2:
                    m += (c_return_return[(wp1,v1),(wp2,v2)] + x[v1,v2] + x[v2,wp1] + x[wp1,wp2] >= 1)
                    m += (c_return_return[(wp1,v1),(wp2,v2)] + x[v2,v1] + x[wp1,v2] + x[wp2,wp1] >= 1)
                    m += (c_return_return[(wp1,v1),(wp2,v2)] + x[v1,wp2] + x[wp2,wp1] + x[wp1,v2] >= 1)
                    m += (c_return_return[(wp1,v1),(wp2,v2)] + x[wp2,v1] + x[wp1,wp2] + x[v2,wp1] >= 1)
                    m += (c_return_return[(wp1,v1),(wp2,v2)] + x[wp1,v2] + x[v2,v1] + x[v1,wp2] >= 1)
                    m += (c_return_return[(wp1,v1),(wp2,v2)] + x[v2,wp1] + x[v1,v2] + x[wp2,v1] >= 1)
                    m += (c_return_return[(wp1,v1),(wp2,v2)] + x[wp1,wp2] + x[wp2,v1] + x[v1,v2] >= 1)
                    m += (c_return_return[(wp1,v1),(wp2,v2)] + x[wp2,wp1] + x[v1,wp2] + x[v2,v1] >= 1)
                    
    ##########################################################################################################
    # MAXIMISE THE STRAIGHTNESS
    ##########################################################################################################
    
    # Unpack the model input dictionary
    node_layer_set1 = straightness_model['node_layer_set']
    node_band_set1 = straightness_model['node_band_set']
    edges1 = straightness_model['edges']
    edge_weight1 = straightness_model['edge_weight']
    node_weight1 = straightness_model['node_weight']
    
    # Create all the y variables - one for every node
    y = { node: m.add_var(var_type=CONTINUOUS) 
         for layer in node_layer_set1 for node in layer
        }
    
    # Create a list of all the node pairings in each layer
    pairs = [[ (u1,u2) for u1 in layer 
                       for u2 in layer 
                       if u1 != u2 ] 
                      for layer in node_layer_set1 ]

    # Create a dictionary of binary decision variables called 'x' containing the relative positions of the nodes in a layer
    dx = { k: m.add_var(var_type=CONTINUOUS) for layer in pairs for k in layer }
    
    # Create the white space variables 
    d = {}
    for i in range(len(node_layer_set1)):
        
        # Add the base_line to first node variable
        d[f'b{i}'] = m.add_var(var_type=CONTINUOUS, lb = 0)
        
        # loop through all the nodes
        for node in node_layer_set1[i]:
            d[node] = m.add_var(var_type=CONTINUOUS, lb = wslb, ub = wsub)
                
    # Create all the deviation variables
    s = {}
    for edge in edges1:
        s[edge] = m.add_var(var_type=CONTINUOUS)
        
    ### Now go through and create the constraints
    
    ## First create the constraints linking y values to white_spaces and weights

    # Loop through all layers and add the constraint
    for i, layer in enumerate(node_layer_set1):
        
        # Loop through all the nodes in the layer
        for u in layer:
            
            # Loop through and add all the constraints for the dx variable 
            for v in layer:
                if v != u:
                    # Add all the 4 constraints 
                    m += ( dx[v,u] <= wsub * x[v,u] )
                    m += ( dx[v,u] >= wslb * x[v,u] )
                    m += ( dx[v,u] <= d[v] - wslb * (1-x[v,u]) )
                    m += ( dx[v,u] >= d[v] - wsub * (1-x[v,u]) )

            # Add the constraint
            #m += ( d[f'b{i}'] + xsum( (node_weight1[v] + d[v])*x[v,u] for v in layer if v != u ) )
            m += ( d[f'b{i}'] + xsum( (node_weight1[v]*x[v,u] + dx[v,u]) for v in layer if v != u ) == y[u] )
                
    ## Create all the straightness constraints

    # Loop through all the edges and add the two required constraints 
    for (u,v) in edges1:
        m += (s[(u,v)] >= y[u] - y[v])
        m += (s[(u,v)] >= -(y[u] - y[v]))

    ## Create all the band constraints (ie higher bands above lower bands)

    # Loop through the node_band_set and add all the nodes accordingly 
    # First loop through 
    for i, bandu in enumerate(node_band_set1):
        for u in bandu:

            # Now for each 'u' node loop through all the other nodes
            for j, bandv in enumerate(node_band_set1):
                for v in bandv:

                    # Only add the constraint if the second band is greater than the first
                    if j > i:
                        m += (y[v] >= y[u] + node_weight1[u])
    
    #########################################################################################################
    ### Objective Function
    #########################################################################################################

    m.objective = minimize( # Area of main edge crossings
                           crossing_weight * ( 
                           xsum(edge_weight[u1v1]*edge_weight[u2v2]*c_main_main[u1v1,u2v2]
                                for (u1v1,u2v2) in c_main_main.keys()) +
                            # Area of crossings between exit and main edges
                           xsum(edge_weight[u1v1]*edge_weight[u2wp]*c_exit_forward[u1v1,u2wp]
                                for (u1v1,u2wp) in c_exit_forward.keys()) +
                            # Area of crossings between exit edges
                           xsum(edge_weight[u1wp1]*edge_weight[u2wp2]*c_exit_exit[u1wp1,u2wp2]
                                for (u1wp1,u2wp2) in c_exit_exit.keys()) +
                            # Area of crossings between return and main edges
                           xsum(edge_weight[u1v1]*edge_weight[wpv2]*c_return_forward[u1v1,wpv2]
                                for (u1v1,wpv2) in c_return_forward.keys()) +
                            # Area of crossings between return edges
                           xsum(edge_weight[wp1v1]*edge_weight[wp2v2]*c_return_return[wp1v1,wp2v2]
                                for (wp1v1,wp2v2) in c_return_return.keys()) 
                           ) +
                           straightness_weight * (
                           xsum(s[edge]*edge_weight[edge] for edge in s.keys())
                           )
                          )
                          
    # Run the model and optimise!
    status = m.optimize(max_solutions = 500)
    
    #########################################################################################################
    ### Decode Solution
    #########################################################################################################

    ### Decode the solution by running through and creating simplified dictionary
    y_coordinates = {}
    for node in y:
        y_coordinates[node] = y[node].x
        
    ### Define a function that decodes the solution (i.e. compares nodes in a layer)

    def cmp_nodes(u1,u2):
        # If the optmimised x is >= 0.99 then u1 above u2 - thus u1 comes first
        if x[u1,u2].x >= 0.99:
            return -1
        else:
            return 1
        
    ### Return Solution

    # Optimised node order arranged in layers
    sorted_order = [ sorted(layer,key=cmp_to_key(cmp_nodes)) for layer in node_layer_set ]

    # Optimised order arranged in layers and bands
    banded_order = [[] for i in range(len(node_layer_set))]

    for i in range(len(node_layer_set)):
        start_index = 0
        for band in node_band_set:
            end_index = len(band[i]) + start_index
            banded_order[i].append(sorted_order[i][start_index:end_index])
            start_index = end_index
            
    return banded_order, y_coordinates
