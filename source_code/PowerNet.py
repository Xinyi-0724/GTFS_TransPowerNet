import pandas as pd
import keplergl as kp
import math
import networkx as nx
import matplotlib.pyplot as plt

from collections import defaultdict
from math import sqrt


def virtual_power_network(candidate_stops_df, threshold_power_node):
    candidate_stops_df = candidate_stops_df[['stop_id','stop_lat','stop_lon']]
    # create a function to calculate the distance between two points:
    def distance(lat1, lon1, lat2, lon2):
        r = 6371 # radius of the Earth in kilometers
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        return r * c # return the distance in kilometers

    # select the candidate charging stations as the power nodes in the power network:
    selected_stop_power = []
    visited_stop_power = []

    for i in range(len(candidate_stops_df)):
        if candidate_stops_df.iloc[i]['stop_id'] not in visited_stop_power:
            selected_stop_power.append(candidate_stops_df.iloc[i]['stop_id'])
            for j in range(i+1, len(candidate_stops_df)):
                if candidate_stops_df.iloc[j]['stop_id'] not in visited_stop_power:
                    stop_distance = distance(candidate_stops_df.iloc[i]['stop_lat'], candidate_stops_df.iloc[i]['stop_lon'], candidate_stops_df.iloc[j]['stop_lat'], candidate_stops_df.iloc[j]['stop_lon'])
                    if stop_distance < threshold_power_node:
                        visited_stop_power.append(candidate_stops_df.iloc[j]['stop_id'])

    power_nodes_list = list(selected_stop_power)

    # create a dataframe for the power nodes with the stop_id and stop_lon/stop_lat:
    selected_power_nodes = candidate_stops_df[candidate_stops_df["stop_id"].isin(power_nodes_list)]

    # create a map to show the candidate power grid and lines:
    map_2 = kp.KeplerGl(height = 500)
    # create a map to show the candidate charging stations and the routes:
    map_2.add_data(data=selected_power_nodes, name='powernodes')

    # To minimize the total link length between selected_power_nodes in a radial network, we can use the minimum spanning tree (MST) algorithm.
    # To determine which two points are connected together in the MST, we can use any of the standard MST algorithms, such as Kruskal's algorithm or Prim's algorithm.
    # Here we implement Kruskal's algorithm in Python and use the networkx library

    # Create a graph with the power nodes 
    G = nx.complete_graph(len(selected_power_nodes))

    # Set the coordinates of the nodes randomly
    pos = {i: (selected_power_nodes.iloc[i]['stop_lat'], selected_power_nodes.iloc[i]['stop_lon']) for i in range(len(selected_power_nodes))}

    # Calculate the distances between all pairs of nodes
    power_node_dis = {(i, j): distance(pos[i][0],pos[i][1],pos[j][0],pos[j][1]) for i, j in G.edges()}

    # Add the distances as edge weights to the graph
    nx.set_edge_attributes(G, power_node_dis, 'weight')

    # Find the minimum spanning tree using Kruskal's algorithm
    T = nx.minimum_spanning_tree(G)

    # Plot the graph and the minimum spanning tree
    # nx.draw(G, pos=pos, with_labels=False, node_size=10)
    nx.draw(T, pos=pos, with_labels=False, node_size=10, edge_color='r')
    plt.show()

    # create a dataframe for the power links with the source and target lat/lon:
    power_lines = sorted(T.edges(data=False))
    power_line_list = defaultdict(list)
    for link in power_lines:
        row_start = selected_power_nodes.iloc[link[0]]
        row_start.index = ['start_stop_id', 'start_lat', 'start_lon']    
        row_end = selected_power_nodes.iloc[link[1]]
        row_end.index = ['end_stop_id', 'end_lat', 'end_lon']
        for k, v in row_start.items():
            power_line_list[k].append(v)
        for k, v in row_end.items():
            power_line_list[k].append(v)


    power_line_list = pd.DataFrame(power_line_list)
    power_line_list['start_stop_id'] = power_line_list['start_stop_id'].astype(int)
    power_line_list['end_stop_id'] = power_line_list['end_stop_id'].astype(int)
    # import the power line data to map_2:
    map_2.add_data(data = power_line_list, name='powerlines')

    # save the current power map to html
    map_2.save_to_html(file_name='grid_map.html')

    return selected_power_nodes, power_line_list, map_2