from TransNet import BEB_bus_network
from PowerNet import virtual_power_network

def GTFS_TransPowerNet(gtfs_file, BEB_route, dist_threshold, common_stop_threshold, threshold_power_node):
    # obtain the list of selected stops that are in the transporation network:
    candidate_stops_df, shape_routes_df, map_1 = BEB_bus_network(gtfs_file, BEB_route, dist_threshold, common_stop_threshold)
    # obtain the virtual power network:
    selected_power_nodes, power_line_list, map_2 = virtual_power_network(candidate_stops_df, threshold_power_node)

    # create a map to show the coupled power and transportation networks:
    map_3 = map_1
    map_3.add_data(data=selected_power_nodes, name='powernodes')
    map_3.add_data(data = power_line_list, name='powerlines')
    # save the coupled transportation and power map to html
    map_3.save_to_html(file_name='coupled_map.html')
    
    return map_3