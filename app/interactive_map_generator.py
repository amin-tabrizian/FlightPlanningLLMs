import json

def generate_interactive_map(coords, waypoints, name, evaluation, timestamp):
    """
    Generate an interactive Leaflet map with draggable waypoints
    
    Args:
        coords: Dictionary of coordinates (polygons, flyzone, origin, destination)
        waypoints: List of waypoint coordinates [[lat, lon], ...]
        name: Output file name
        evaluation: Evaluation object with validation results
        timestamp: Unique identifier for this flight plan
    
    Returns:
        dict: Map data for frontend rendering
    """
    try:
        # Debug print to understand coordinate format
        if waypoints:
            print(f"DEBUG - Sample waypoint: {waypoints[0]}")
            print(f"DEBUG - Waypoint range - lat: {min(wp[0] for wp in waypoints):.6f} to {max(wp[0] for wp in waypoints):.6f}")
            print(f"DEBUG - Waypoint range - lng: {min(wp[1] for wp in waypoints):.6f} to {max(wp[1] for wp in waypoints):.6f}")
        
        if coords:
            sample_key = list(coords.keys())[0]
            sample_coord = list(coords.values())[0][0]
            print(f"DEBUG - Sample {sample_key}: {sample_coord}")
            
            # Check origin specifically
            for key, pts in coords.items():
                if "Origin" in key:
                    print(f"DEBUG - Origin coordinates: {pts[0]} (should be [lon, lat] format)")
                    break
        # Prepare map data
        map_data = {
            'waypoints': [],
            'polygons': [],
            'flyzone': None,
            'origin': None,
            'destination': None,
            'violating_segments': [],
            'out_points': [],
            'center': None,
            'zoom': 13,
            'timestamp': timestamp
        }
        
        # Process coordinates
        for key, pts in coords.items():
            if key.startswith("poly"):
                # Convert [lon, lat] to [lat, lng] for Leaflet
                converted_coords = [[coord[1], coord[0]] for coord in pts]
                map_data['polygons'].append({
                    'name': key,
                    'coordinates': converted_coords,
                    'type': 'no-fly-zone'
                })
            elif key == "FlyZone":
                # Convert [lon, lat] to [lat, lng] for Leaflet
                converted_coords = [[coord[1], coord[0]] for coord in pts]
                map_data['flyzone'] = {
                    'coordinates': converted_coords,
                    'type': 'flyzone'
                }
            elif "Origin" in key:
                # KML coordinates are [lon, lat], but Leaflet expects [lat, lng]
                coord = pts[0]
                map_data['origin'] = {
                    'coordinates': [coord[1], coord[0]],  # Convert [lon, lat] to [lat, lng]
                    'name': key
                }
            elif "Destination" in key:
                # KML coordinates are [lon, lat], but Leaflet expects [lat, lng]
                coord = pts[0]
                map_data['destination'] = {
                    'coordinates': [coord[1], coord[0]],  # Convert [lon, lat] to [lat, lng]
                    'name': key
                }
            else:
                # Other polygons (not Origin, Destination, or FlyZone)
                if len(pts) > 2:
                    # Convert [lon, lat] to [lat, lng] for Leaflet
                    converted_coords = [[coord[1], coord[0]] for coord in pts]
                    map_data['polygons'].append({
                        'name': key,
                        'coordinates': converted_coords,
                        'type': 'no-fly-zone'
                    })
        
        # Process waypoints - detect if they need coordinate conversion
        # Check if waypoints are in wrong format by comparing with origin coordinates
        waypoints_need_conversion = False
        if waypoints and coords:
            # Find origin coordinates to compare with first waypoint
            origin_coord = None
            for key, pts in coords.items():
                if "Origin" in key:
                    origin_coord = pts[0]  # [lon, lat] from KML
                    break
            
            if origin_coord:
                first_waypoint = waypoints[0]
                # Check if waypoint coordinates make sense when compared to origin
                # If first coord of waypoint is similar to first coord of origin, 
                # then waypoints might be in [lon, lat] format and need conversion
                lat_diff = abs(first_waypoint[0] - origin_coord[1])  # waypoint[0] vs origin_lat
                lon_diff = abs(first_waypoint[1] - origin_coord[0])  # waypoint[1] vs origin_lon
                
                wrong_lat_diff = abs(first_waypoint[0] - origin_coord[0])  # waypoint[0] vs origin_lon
                wrong_lon_diff = abs(first_waypoint[1] - origin_coord[1])  # waypoint[1] vs origin_lat
                
                print(f"DEBUG - Origin [lon, lat]: {origin_coord}")
                print(f"DEBUG - First waypoint: {first_waypoint}")
                print(f"DEBUG - Correct format diff (lat, lon): {lat_diff:.6f}, {lon_diff:.6f}")
                print(f"DEBUG - Wrong format diff (lon, lat): {wrong_lat_diff:.6f}, {wrong_lon_diff:.6f}")
                
                # If the "wrong" format gives smaller differences, waypoints are in [lon, lat] format
                if (wrong_lat_diff + wrong_lon_diff) < (lat_diff + lon_diff):
                    waypoints_need_conversion = True
                    print("DEBUG - Waypoints appear to be in [lon, lat] format, converting...")
                else:
                    print("DEBUG - Waypoints appear to be in [lat, lon] format, no conversion needed")
        
        for i, wp in enumerate(waypoints):
            if waypoints_need_conversion:
                # Convert from [lon, lat] to [lat, lon]
                lat, lng = wp[1], wp[0]
            else:
                # Already in [lat, lon] format
                lat, lng = wp[0], wp[1]
                
            map_data['waypoints'].append({
                'id': i,
                'lat': lat,
                'lng': lng,
                'draggable': True,
                'type': 'intermediate' if 0 < i < len(waypoints) - 1 else ('origin' if i == 0 else 'destination')
            })
        
        # Process violating segments from evaluation
        if hasattr(evaluation, 'segs') and evaluation.segs:
            for line_segments in evaluation.segs:
                for line in line_segments:
                    # Assume segments follow waypoint format - check if they need conversion
                    map_data['violating_segments'].append([
                        [line[0][0], line[0][1]],  # waypoint format
                        [line[1][0], line[1][1]]   # waypoint format
                    ])
        
        # Process out points
        if hasattr(evaluation, 'out_pts') and evaluation.out_pts:
            for wp in evaluation.out_pts:
                # Assume out points follow waypoint format
                map_data['out_points'].append([wp[0], wp[1]])
        
        # Calculate map center and bounds
        if map_data['waypoints']:
            # Calculate center from processed waypoints (already in correct lat/lng format)
            lats = [wp['lat'] for wp in map_data['waypoints']]
            lngs = [wp['lng'] for wp in map_data['waypoints']]
            map_data['center'] = [
                sum(lats) / len(lats),
                sum(lngs) / len(lngs)
            ]
            
            # Calculate zoom level based on bounds
            lat_range = max(lats) - min(lats)
            lng_range = max(lngs) - min(lngs)
            max_range = max(lat_range, lng_range)
            
            # Approximate zoom level calculation
            if max_range > 0.1:
                map_data['zoom'] = 10
            elif max_range > 0.05:
                map_data['zoom'] = 11
            elif max_range > 0.01:
                map_data['zoom'] = 13
            else:
                map_data['zoom'] = 15
        
        return map_data
        
    except Exception as e:
        print(f"Error generating interactive map: {e}")
        return None

def calculate_distance_km(waypoints):
    """
    Calculate total distance of flight path in kilometers
    """
    from utils import compute_total_path_length
    return compute_total_path_length(waypoints)

def validate_flight_path(waypoints, float_coordinates):
    """
    Validate the flight path against no-fly zones and flyzone
    """
    from coach import rule_based_evaluation
    return rule_based_evaluation(waypoints, float_coordinates) 