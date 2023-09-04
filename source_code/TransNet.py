import geopandas as gpd
import pandas as pd
import zipfile
import keplergl as kp

from collections import Counter
from itertools import chain
from shapely.geometry import LineString

# -------------------------------------------------------
# This file select the candidate sites strictly according to the rule 3 in week 5 report.
# Starting from the origin station, the distance between the bus station and the previous node is compared to the distance threshold. 
# If it exceeds the threshold, the bus station is selected as a new node in the transport network.
# -------------------------------------------------------

def BEB_bus_network(gtfs_file, BEB_route, dist_threshold, common_stop_threshold):
    """
    Select the transportation nodes along the BEB bus routes.
    """

    # import the GTFS data into a dictionary of dataframes
    with zipfile.ZipFile(gtfs_file) as myzip:
        routes = pd.read_csv(myzip.open("routes.txt"))
        trips = pd.read_csv(myzip.open("trips.txt"))
        shapes = pd.read_csv(myzip.open("shapes.txt"))
        stops = pd.read_csv(myzip.open("stops.txt"))
        stop_times = pd.read_csv(myzip.open("stop_times.txt"))
    
    # ensure that the route_short_name is a string
    routes["route_short_name"] = routes["route_short_name"].astype(str)

    # create a new route dataframe with only the BEB routes
    selected_routes = routes[routes["route_short_name"].isin(BEB_route)]

    # create a new trips dataframe with only the BEB routes
    selected_trips = trips[trips["route_id"].isin(selected_routes["route_id"])]

    # create a new shapes dataframe with only the BEB routes
    selected_shapes = shapes[shapes["shape_id"].isin(selected_trips["shape_id"])]

    # create a new stop_times dataframe with only the BEB routes
    selected_stop_times = stop_times[stop_times["trip_id"].isin(selected_trips["trip_id"])]

    # selected_trips['route_id'].nunique() == 15 
    # selected_shapes['shape_id'].nunique() == 39 
    # breaks down selected_trips to 15 routes, noted that one route can have multiple shapes
    route_id_list = selected_trips['route_id'].unique()
    route_trips_list = []
    # break down selected_stop_times to 15 routes, noted that one route can have multiple trips
    route_stop_times_list = []
    # calculate the number of unique shapes for each route: the sum should be 39
    route_shapeno_list = []
    # keep the unique shape_id for each route: drop duplicates of shape_id records
    route_shapeid_list = []

    # set up a traveling threshold for selecting the candidate charging stations along the routes
    candidate_stop_id = []
    routes_stop_BEB = []
    routes_shape_BEB = []
    df_stop_times_dir_list_sum = pd.DataFrame()
    for route_id in route_id_list:
        route_trips = selected_trips[selected_trips['route_id'] == route_id]
        route_trips_list.append(route_trips)
        route_stop_times_list.append(selected_stop_times[selected_stop_times['trip_id'].isin(route_trips['trip_id'])])
        route_shapeno_list.append(route_trips['shape_id'].nunique())
        route_shapeid = route_trips.drop_duplicates(subset=['shape_id'], keep='first')
        route_shapeid_list.append(route_shapeid)
        # break down route_shapeid by direction_id, compare the number of stops for each direction and select the one with the most stops
        # for each route, select the charging stations for each direction:
        route_stop_id = []
        # collect all stops for each routes
        route_stops = []
        # collect all trips for each routes
        route_shapes = []
        df_stop_times_dir_list = pd.DataFrame()
        for dir_id in route_shapeid['direction_id'].unique():
            route_shapeid_dir = route_shapeid[route_shapeid['direction_id'] == dir_id]
            if route_shapeid_dir['trip_id'].nunique() > 1:
                sub_stop_times = stop_times[stop_times['trip_id'].isin(route_shapeid_dir['trip_id'].unique())]
                # groub by trip_id and calculate the number of stops for each trip_id
                stop_num = sub_stop_times.groupby('trip_id')['stop_id'].count()
                # find the trip_id with the most stops
                route_shapeid_dir = route_shapeid_dir[route_shapeid_dir['trip_id'] == stop_num.index[stop_num.argmax()]]
            # find the shape_id for each direction:
            route_shapes.append(route_shapeid_dir['shape_id'].values[0])
            # find the representative trip for each direction and create the stop_times dataframe for it
            stop_times_dir = selected_stop_times[selected_stop_times['trip_id'] == route_shapeid_dir['trip_id'].values[0]]
            
            # for each direction, the start and end stops are selected as the candidate charging stations
            orgin_stop_id = stop_times_dir['stop_id'].iloc[0]
            route_stop_id.append(orgin_stop_id)
            terminal_stop_id = stop_times_dir['stop_id'].iloc[-1]
            route_stop_id.append(terminal_stop_id)

            # collect all stops for each direction
            route_stops_dir = stop_times_dir['stop_id'].unique()
            route_stops.extend(route_stops_dir)

            # for each direction, select the charging stations along the route:
            # compare the shape_dist_traveled in stop_times_dir with the threshold, and select the stops with largest shape_dist_traveled that less than the threshold:
            dist_last_site = 0.0
            stop_thresh_dir = []
            for i in range(len(stop_times_dir)):
                if stop_times_dir['shape_dist_traveled'].iloc[i] > dist_last_site + dist_threshold:
                    if stop_times_dir['shape_dist_traveled'].iloc[i] - stop_times_dir['shape_dist_traveled'].iloc[i-1] > dist_threshold:
                        # once the distance between two stops is larger than the threshold, select the next stop as the candidate charging station:
                        stop_thresh_dir.append(stop_times_dir['stop_id'].iloc[i-1])
                        stop_thresh_dir.append(stop_times_dir['stop_id'].iloc[i])
                        dist_last_site = stop_times_dir['shape_dist_traveled'].iloc[i]
                    else: 
                        # record the stop_id with the largest shape_dist_traveled that less than the threshold
                        stop_thresh_dir.append(stop_times_dir['stop_id'].iloc[i-1])
                        dist_last_site = stop_times_dir['shape_dist_traveled'].iloc[i-1]
            # add stop_thresh_dir to route_stop_id
            route_stop_id.extend(stop_thresh_dir)
            df_stop_times_dir = stop_times_dir.copy()
            df_stop_times_dir = df_stop_times_dir[['stop_id', 'shape_dist_traveled']]
            # create a new column for df_stop_times_dir_list: direction_id
            df_stop_times_dir['direction_id'] = dir_id
            # create a new column for df_stop_times_dir_list: route_id
            df_stop_times_dir['route_id'] = route_id
            # create a new column for df_stop_times_dir_list: route_name
            df_stop_times_dir['route_name'] = selected_routes[selected_routes['route_id'] == route_id]['route_short_name'].values[0]
            # collect df_stop_times_dir for each direction:
            df_stop_times_dir_list = pd.concat([df_stop_times_dir_list, df_stop_times_dir], axis=0)
    
        # remove the duplicate stop_id in route_stop_id and route_stops
        route_stop_id = list(set(route_stop_id))
        route_stops = list(set(route_stops))
        # collect all shapes for each routes
        routes_shape_BEB.append(route_shapes)
        # collect all stops for each routes
        candidate_stop_id.append(route_stop_id)
        routes_stop_BEB.append(route_stops)
        # collect all bus stops for each routes:
        df_stop_times_dir_list_sum = pd.concat([df_stop_times_dir_list_sum, df_stop_times_dir_list], axis=0)

    # select the common stop_id among routes_stop_BEB
    all_stops = list(chain(*routes_stop_BEB))
    stop_counts = Counter(all_stops)
    # define a common stop
    common_stops = [stop for stop, count in stop_counts.items() if count > common_stop_threshold]
    candidate_stop_id.append(common_stops)
    # remove duplicate stop_id in candidate_stop_id
    candidate_stop_id = list(set(list(chain(*candidate_stop_id))))


    # create a map to show the candidate charging stations and the routes:
    map_1 = kp.KeplerGl(height = 500)

    # create a dataframe for the candidate charging stations with the stop_id and stop_lon/stop_lat:
    candidate_stops_df = stops[stops['stop_id'].isin(candidate_stop_id)]
    candidate_stops_df = candidate_stops_df[['stop_id','stop_lat','stop_lon']]

    map_1.add_data(data=candidate_stops_df, name='candidates')

    # create a dataframe for the routes with the route_id, shape_id, shape_pt_lat and shape_pt_lon:
    routes_shape_df = selected_shapes[selected_shapes['shape_id'].isin(list(chain(*routes_shape_BEB)))]
    routes_shape_df = routes_shape_df[['shape_id','shape_pt_lat','shape_pt_lon','shape_pt_sequence']]

    # for each route in the routes_shape_BEB, create a dataframe to represent the line segments according to the shape_pt_seq:
    shape_routes_sum = []
    shape_routes_df = pd.DataFrame()
    for route_shape2 in routes_shape_BEB:
        # check if the route_shape2 has two directions:
        if len(route_shape2) == 2:
            # create a dataframe for each direction:
            direction_0_shape = routes_shape_df[routes_shape_df['shape_id'] == route_shape2[0]]
            direction_1_shape = routes_shape_df[routes_shape_df['shape_id'] == route_shape2[1]]
            # remove the first row of direction_1_shape:
            direction_1_shape = direction_1_shape.iloc[1:]
            shape_routes = pd.concat([direction_0_shape, direction_1_shape], axis=0)
        elif len(route_shape2) == 1:
            shape_routes = routes_shape_df[routes_shape_df['shape_id'] == route_shape2[0]]
        else:
            print('Error: there are routes having more than two directions!')
        # for each shape_id, add a column to indicate the corresponding route_id in selected_trips:
        shape_routes['route_id'] = ''
        # for each shape_id, add a column to indicate the corresponding route_short_name in selected_routes:
        shape_routes['route_short_name'] = ''
        for route_idx in selected_trips['route_id'].unique():
            # the shape_id in route_shape2[0] is the shape_id for the direction 0:
            if route_shape2[0] in selected_trips[selected_trips['route_id'] == route_idx]['shape_id'].values:
                shape_routes['route_id'] = route_idx
                shape_routes['route_short_name'] = selected_routes[selected_routes['route_id'] == route_idx]['route_short_name'].values[0]
        df_shape_routes = shape_routes.copy()
        shape_routes_sum.append(df_shape_routes)
        # line segments are created by connecting the shape_pt_seq with the next shape_pt_seq
        shape_routes[['target_lat','target_lon']] = shape_routes[['shape_pt_lat','shape_pt_lon']].copy()
        tgt_vals = shape_routes[['shape_pt_lat','shape_pt_lon']].iloc[1:].reset_index(drop=True).values
        shape_routes = shape_routes.iloc[:-1]
        shape_routes[['target_lat','target_lon']] = tgt_vals
        shape_routes_df = pd.concat([shape_routes_df, shape_routes], axis=0)
        # for each shape_id, add the corresponding shape_routes dataframe to map_1 and named as 'routes_route_short_name'
        map_1.add_data(data = shape_routes, name='routes_' + shape_routes['route_short_name'].values[0])

    # save the candidate charging stations and the routes to a geojson file:
    gdf_candidate_stops = gpd.GeoDataFrame(candidate_stops_df, geometry=gpd.points_from_xy(candidate_stops_df.stop_lon, candidate_stops_df.stop_lat))
    gdf_candidate_stops.to_file('candidate_bus_stops.geojson', driver='GeoJSON')
    # create the coordinates for the line segments:
    routes_coords = [(lon1, lat1, lon2, lat2) for lon1, lat1, lon2, lat2 in zip(shape_routes_df['shape_pt_lon'], shape_routes_df['shape_pt_lat'], shape_routes_df['target_lon'], shape_routes_df['target_lat'])]
    route_lines = [LineString([(x[0], x[1]), (x[2], x[3])]) for x in routes_coords]
    gdf_shape_routes = gpd.GeoDataFrame(shape_routes_df, geometry=route_lines)
    gdf_shape_routes.to_file('all_bus_routes.geojson', driver='GeoJSON')

    # save the current transportation map to html
    map_1.save_to_html(file_name='trans_map.html')

    return candidate_stops_df, shape_routes_df, map_1