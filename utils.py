import xml.etree.ElementTree as ET
import simplekml
import math
from pydantic import BaseModel
from quadrilateral_fitter import QuadrilateralFitter
from shapely.geometry import Polygon, Point
from typing import Dict, List
import datetime
import json


 



def get_coordinates_from_kml(kml_file_path: str, placemark_names: list):
    """
    Extracts coordinates from a KML file for multiple specified placemark names.

    :param kml_file_path: Path to the KML file.
    :param placemark_names: List of placemark names to search for.
    :return: Dictionary with placemark names as keys and coordinates as values.
    """
    try:
        # Load and parse the KML file
        tree = ET.parse(kml_file_path)
        root = tree.getroot()

        # Extract the namespace
        namespace = {'kml': 'http://www.opengis.net/kml/2.2'}

        # Dictionary to store results
        placemark_dict = {}
        placemark_names += ['FlyZone']
        # Search for all placemarks in the file
        for elem in root.findall(".//kml:Placemark", namespace):
            name = elem.find("kml:name", namespace)
            coordinates = elem.find(".//kml:coordinates", namespace)

            if name is not None and coordinates is not None:
                # If the name is in the requested list, store it in the dictionary
                is_in_list = any([placemark in name.text for placemark in placemark_names])
                if is_in_list:
                    placemark_dict[name.text] = coordinates.text.strip()

        return placemark_dict  # Return the dictionary of results

    except ET.ParseError:
        print("Error: Unable to parse the KML file. Ensure it is properly formatted.")
    except Exception as e:
        print(f"An error occurred: {e}")

    return {}  # Return an empty dictionary if nothing is found

def convert_to_float_dict(coord_dict, approx=False):
    """
    Converts a dictionary with string coordinates into a dictionary with lists of float lists.
    
    Each value in the input dictionary is a string containing coordinate sets separated by spaces.
    Each coordinate set is a comma-separated string (e.g., "lat,lon,alt").
    
    Parameters:
        coord_dict (dict): Dictionary with keys as identifiers and values as coordinate strings.
        
    Returns:
        dict: A new dictionary where each key maps to a list of coordinate lists (each coordinate as a list of floats).
    """
    float_dict = {}
    for key, value in coord_dict.items():
        # Split the string by whitespace to separate coordinate groups
        coord_strings = value.strip().split()
        # Convert each coordinate group into a list of floats
        float_coords = []
        float_coord = []
        for coord in coord_strings:
            # Split the coordinate string into individual numbers
            numbers = coord.split(',')
            # Convert first two numbers (lon, lat) to float
            float_coord = [float(numbers[0]), float(numbers[1])]
            # Add to the list of coordinates
            float_coords.append(float_coord)

                
        # float_coords = [
        #     [float(number) for number in coord.split(',')]
        #     for coord in coord_strings
        # ]
        float_dict[key] = float_coords
        if approx == True and 'poly' in key:
            # Convert tuple of tuples to list of lists for JSON serialization
            quad_fit = QuadrilateralFitter(polygon=float_coords).fit()
            float_dict[key] = [[float(x), float(y)] for x, y in quad_fit]  # Convert to list of lists with float values
            float_dict[key] += [[float(quad_fit[0][0]), float(quad_fit[0][1])]]

    return float_dict


def prompt_generator(kml_path, placemarks, human_msg, samples = False):
    """
    Generates a prompt for the flight planner based on KML file and placemark names.

    Parameters:
        kml_path (str): Path to the KML file.
        placemarks (list): List of placemark names to include in the prompt.

    Returns:
        str: The generated prompt for the flight planner.
    """
    coordinates_dict = convert_to_float_dict(get_coordinates_from_kml(kml_path, placemarks))
    user_msg = 'Now you have to generate a flight plan avoiding the wind polygons for the following problem: \n'
    # system_msg = (
    #     "You are a flight planner for an eVTOL aircraft. "
    #     "The user will give you a few  wind hazard polygons' information "
    #     "and asks you to generate a flight plan from a start to an end point. "
    #     "You have to generate a flight plan which is a number of way points "
    #     "starting from the start coordinate and ending in the end coordinate "
    #     "while avoiding the wind polygons (first you have to draw the polygons "
    #     "in your brain and try to generate a flight plan that avoids them)."
    #     "Your flight plan should not intersect with the wind polygons."
    #     "Always include the start and end point in your response. "
    #     "You can generate as many waypoints as you want in order to avoid the polygons. "
    #     "More waypoints will lead to a smoother flight plan. "
    #     "You have to stay in the fly zone. You can't fly outside of the fly zone. "
    #     "Try to find the shortest path. "
    #     "Note: The shortest path is a straight line between the origin and the destination. "
    #     "Here, you probably need to find the closest line to this line "
    #     "while avoiding wind hazardous areas. "
    #     "You may need to add more waypoints to find the shortest path.\n"
    # )
    system_msg = (
        "You are a flight planner for an eVTOL aircraft. "
        "The user will give you a few  wind hazard polygons' information "
        "and asks you to generate a flight plan from a start to an end point. "
        "You have to generate a flight plan which is a list of way points "
        "starting from the origin coordinate and ending in the destination coordinate "
        "while avoiding the wind polygons (first you have to draw the polygons "
        "in your brain and try to generate a flight plan that avoids them)."
        "Your flight plan should not intersect with the wind polygons."
        "Always include the origin and destination point in your response. "
        "You can generate as many waypoints as you want in order to avoid the polygons. "
        "More waypoints will lead to a smoother flight plan. "
        "You have to stay in the fly zone. You can't fly outside of the fly zone. "
        "Try to find the shortest path. "
        "Note: The shortest path is a straight line between the origin and the destination. "
        "while avoiding wind hazardous areas. "
        "The best approach to find the optimal solution is follwing these steps: \n "
        "1. Identify the origin and destination points.\n "
        "2. Identify the wind hazardous areas and the fly zone.\n "
        "3. The angle between waypoints line segments should not be more than 30 degrees (reommended).\n "
        "3. Generate a valid waypoint between the origin and destination points that avoids the wind hazardous areas (shapely.intersects() function can be used).\n "
        "4. Update the origin to the generated waypoint and repeat the process until you reach the destination.\n "
        "5. Ensure that the generated waypoints do not intersect with the wind hazardous areas.\n "
        "6. Ensure that the generated waypoints stay within the fly zone.\n "
        "Note: If the user gave you a memory, you can try to check if the current problem is similar to the previous ones and if so, you can use the previous solutions to generate the current one."
        "Forexample, if the previous problem is valid, you can use the same waypoints to generate the current one. Or make it more efficient. "
        "On the other hand, if the previous problem is invalid, you can keep the previous waypoints that do not intersect with the wind polygons and change the one that intersects with the wind polygons to create a new valid solution."
    )
    if samples:
        system_msg += sample_prompt_generator('samples.kml')
    
    if coordinates_dict:
        for name, coords in coordinates_dict.items():
            user_msg += (f"Coordinates for '{name}':\n{coords}\n")
    else:
        print("No matching placemarks found in the KML file.")
    user_msg += human_msg
    return [system_msg, user_msg]

def convert_waypoints(waypoints):
    return [[wp.longitude, wp.latitude] for wp in waypoints]

# Haversine formula: returns the distance (in kilometers) between two points given in degrees.
def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Earth's radius in kilometers
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = math.sin(dLat/2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon/2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# Function to compute the total 2D path length given a list of waypoints.
def compute_total_path_length(waypoints):
    total_distance = 0.0
    for i in range(1, len(waypoints)):
        # Assume each waypoint has 'latitude' and 'longitude' attributes.
        wp1 = waypoints[i - 1]
        wp2 = waypoints[i]
        distance = haversine_distance(wp1.latitude, wp1.longitude, wp2.latitude, wp2.longitude)
        total_distance += distance
    return total_distance

def compute_total_waypoints(waypoints):
    return len(waypoints)




class Waypoint(BaseModel):
    latitude: float
    longitude: float

class FlightPlan(BaseModel):
    waypoints: list[Waypoint]
    # explanation: str

class Evaluation(BaseModel):
    valid: bool
    evaluation: str
    reasoning: str

class PlannerSolution():
    def __init__(self):
        self.core_metrics = {"distance_km": 0.0,       # Flight plan distance in kilometers
                            "num_waypoints": 0,       # Number of waypoints
                            "response_time_s": 0.0,   # LLM response time in seconds
                            "energy": 0.0,
                            "is_valid": True,         # Count of valid plans
                            "orig_dest": True,  # Ratio of flight path to shortest possible path
                            "fly_zone": True,
                            "avoid_polygons": True,
                            "model": "",
                            "mode": "",
                            "memory": False,
                            "coach": False}

def sample_prompt_generator(kml_path='samples.kml', n_samples=3):
    prompt = 'Here are some samples of the flight plans for a particular wind hazardous area: \n'
    # sol-e3-origin1-destination3, sol-e1-origin4-destination2, sol-e2-origin5-destination3
    placemarks = [["polye3", "Origin1", "Destination3", "sol-e3-origin1-destination3"],
                  ["polye1", "Origin4", "Destination2", "sol-e1-origin4-destination2"],
                  ["polye2", "Origin5", "Destination3", "sol-e2-origin5-destination3"]]
    coordinates_dict_list = []
    for i in range(n_samples):
        coordinates_dict = convert_to_float_dict(get_coordinates_from_kml(kml_path, placemarks[i]), approx=False)
        coordinates_dict_list.append(coordinates_dict)

    
    for i in range(n_samples):
        prompt += (f"Example {i+1}:\n")
        for name, coords in coordinates_dict_list[i].items():
            if 'sol' in name:
                sol = name
                continue
            prompt += (f"Coordinates for '{name}':\n{coords}\n")
        prompt += (f"The solution for this problem is: {coordinates_dict_list[i][sol]} \n" )
    return prompt

def save_messages_to_file(messages, file_path='messages.txt'):
    """
    Saves user and system messages to a file.
    
    Args:
        user_message (str): The message from the user
        system_message (str): The message from the system
        file_path (str, optional): Path to the file where messages will be saved. Defaults to 'messages.txt'.
    """
    try:
        with open(file_path, 'a') as file:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            file.write(f"=== {timestamp} ===\n")
            file.write(f"MSG: {messages}\n\n")
            file.write("-" * 50 + "\n\n")
        return True
    except Exception as e:
        print(f"Error saving messages to file: {e}")
        return False

def convert_coordinates_to_airspace_auto(
    coordinates: Dict[str, List[List[float]]]
) -> Dict[str, object]:
    """
    Converts a coordinate dictionary into an airspace dictionary.
    Automatically finds:
    - One FlyZone polygon
    - One Origin (key starting with 'Origin')
    - One Destination (key starting with 'Destination')
    - All remaining polygons as No-Fly Zones (NFZs)

    Returns:
        dict with keys: 'airspace', 'points', 'nfzs'
    """

    airspace = {}

    # 1. Fly Zone
    if "FlyZone" not in coordinates:
        raise ValueError("'FlyZone' key not found in coordinates.")
    flyzone_coords = [(coord[0], coord[1]) for coord in coordinates["FlyZone"]]
    airspace["airspace"] = [Polygon(flyzone_coords)]

    # 2. Identify Origin and Destination
    origin_key = next((k for k in coordinates if k.lower().startswith("origin")), None)
    destination_key = next((k for k in coordinates if k.lower().startswith("destination")), None)

    if origin_key is None or destination_key is None:
        raise ValueError("Origin or Destination key not found in coordinates.")

    origin_coord = coordinates[origin_key][0]
    destination_coord = coordinates[destination_key][0]
    airspace["points"] = [
        Point(origin_coord[0], origin_coord[1]),
        Point(destination_coord[0], destination_coord[1]),
    ]

    # 3. NFZs
    nfzs = {}
    for key, coord_list in coordinates.items():
        if key in ["FlyZone", origin_key, destination_key]:
            continue
        # Assume all other keys are NFZs (e.g., poly2-1)
        polygon_coords = [(coord[0], coord[1]) for coord in coord_list]
        nfzs[key] = Polygon(polygon_coords)

    airspace["nfzs"] = nfzs

    return airspace

def mode_detector(place_marks):
    poly_name = place_marks[0]
    poly_number = int(poly_name[4])
    print(poly_number)
    if poly_number <= 3 and poly_number >= 1:
        return 'easy'
    elif poly_number <= 6:
        return 'medium'
    elif poly_number <= 9: 
        return 'hard'
    else:
        return 'N/A'
    

    