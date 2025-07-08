import xml.etree.ElementTree as ET
import simplekml
import math
from pydantic import BaseModel
from quadrilateral_fitter import QuadrilateralFitter
from shapely.geometry import Polygon, Point
from typing import Dict, List
import datetime
import json
from typing import List, Tuple
from shapely.geometry import LineString, Polygon


 



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
        placemark_names = placemark_names + ['FlyZone'] if 'FlyZone' not in placemark_names \
                        else placemark_names
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
            float_coord = [round(float(numbers[0]), 5), round(float(numbers[1]), 5)]
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


def prompt_generator(float_coordinates, placemarks, human_msg, samples = False, system_message = ""):
    """
    Generates a prompt for the flight planner based on KML file and placemark names.

    Parameters:
        kml_path (str): Path to the KML file.
        placemarks (list): List of placemark names to include in the prompt.

    Returns:
        str: The generated prompt for the flight planner.
    """
    human_msg = "Human preference: \n" + human_msg + human_msg + human_msg + " \n" if human_msg else ""
    coordinates_dict = float_coordinates
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
    #     "You have to stay in the flyzone. You can't fly outside of the flyzone. "
    #     "Try to find the shortest path. "
    #     "Note: The shortest path is a straight line between the origin and the destination. "
    #     "Here, you probably need to find the closest line to this line "
    #     "while avoiding wind hazardous areas. "
    #     "You may need to add more waypoints to find the shortest path.\n"
    # )
    # system_msg = (
    #     "You are a flight planner for an eVTOL aircraft. "
    #     "The user will give you a few wind hazard polygons' information "
    #     "and asks you to generate a flight plan from an origin to a destination. "
    #     "You have to generate a flight plan which is a list of waypoints "
    #     "starting from the origin coordinate and ending in the destination coordinate "
    #     "while avoiding the wind polygons. "
    #     "Always include the origin and destination point in your response. "
    #     "You can generate as many waypoints as you want in order to avoid the polygons. "
    #     "More waypoints will lead to a smoother flight plan. "
    #     "You can't fly outside of the flyzone. "
    #     "Try to find the shortest path "
    #     "while avoiding wind hazardous areas. "
    #     "Note: The shortest path is a straight line between the origin and the destination."
    #     "The best approach to find the optimal solution is following these steps: \n"
    #     "1. Identify the origin and the destination points.\n"
    #     "2. Identify the wind hazard polygons and the flyzone.\n"
    #     "3. IMPORTANT STEP: Generate waypoints that connect origin to the destination while avoiding wind polygons and are in flyzone (they shouldn't be in on the flyzone's border). You may generate more waypoints near the wind polygons to ensure line segments connecting them do not intersect with the polygons. You should generate waypoints that make the flight plan aligned with the human preference.\n" 
    #     "4. The line segments connecting the waypoints should NOT have sharp angles (reommended).\n "
    #     "5. Ensure that the line segments connecting the waypoints do not intersect with the wind hazard polygons.\n "
    #     "6. If any of the line segments intersect with the polygons modify the corrosponding waypoints. "
    #     "Note: If the user gave you a memory, you should do the following: "
    #     "1. Check if the previous solution is VALID and ALIGNED with the human preference. "
    #     "If so, you can use it as a reference to generate a new solution or make it better. "
    #     "2. If the previous solution is not valid, "
    #     "look at the violating segments and the points outside the flyzone of the previous solution "
    #     "and propose new waypoints to replace them. Pay attention to the human preference. "
    #     "3. If the previous solution is valid but not aligned with the human preference, "
    #     " check human review in the memory and try to resolve their comments in your new solution."
    # )

    
    if coordinates_dict:
        orig_dest_mssg = ""
        for name, coords in coordinates_dict.items():
            if 'Origin' in name or 'Dest' in name:
                orig_dest_mssg += (f"Coordinates for '{name}': {coords} \n")
                continue
            user_msg += (f"Coordinates for '{name}': {coords} \n")
    else:
        print("No matching placemarks found in the KML file.")
    user_msg += orig_dest_mssg
    user_msg += human_msg
    system_msg = load_system_message(system_message)
    # user_msg += "Human preference: \n" + human_msg + " \n" if human_msg else ""
    return [system_msg, user_msg]
def load_system_message(user_key: str) -> str:
    """
    Load a system message from the 'prompts_no_memory.json' file based on the provided user key.

    Args:
        user_key (str): The key corresponding to the desired system message.

    Returns:
        str: The system message if found, otherwise an empty string.
    """
    import json
    try:
        with open("prompts_no_memory.json", "r") as file:
            messages = json.load(file)
        return messages.get(user_key, "")
    except Exception as e:
        print(f"Error loading system message for key '{user_key}': {e}")
        return ""

def convert_waypoints(waypoints):
    wp = waypoints[0]
    if wp.longitude > 0:
        return [[wp.latitude, wp.longitude] for wp in waypoints]
    else:
        return [[wp.longitude, wp.latitude] for wp in waypoints]
def convert_dict_to_list_waypoints(waypoints):
    if waypoints[0]['longitude'] > 0:
        return [[waypoint['latitude'], waypoint['longitude']] for waypoint in waypoints]
    else:
        return [[waypoint['longitude'], waypoint['latitude']] for waypoint in waypoints]
    
def convert_waypoints_to_dict(waypoints):
    return [Waypoint(latitude=waypoint[0], longitude=waypoint[1]) for waypoint in waypoints]


# Haversine formula: returns the distance (in kilometers) between two points given in degrees.
def haversine_distance(point1, point2):
    lat1 = point1[0]
    lat2 = point2[0]

    lon1 = point1[1]
    lon2 = point2[1]
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
        distance = haversine_distance(wp1, wp2)
        total_distance += distance
    return total_distance

def compute_total_waypoints(waypoints):
    return len(waypoints)




class Waypoint(BaseModel):
    latitude: float
    longitude: float

class FlightPlan(BaseModel):
    waypoints: list[Waypoint]
    explanation: str

class Evaluation(BaseModel):
    valid: bool
    polys: list[str]
    segs: list[str]
    orig_dest_ok: list[bool]
    out_pts: list[str]
    human_review: str

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
                            "polygon_number": 0,
                            "memory": False,
                            "solution_waypoints": [],
                            "human_preference": "",
                            "orig_dest": []}

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
            file.write(f"System messages: \n")
            file.write(f"MSG: {messages[0]['content']} \n")
            file.write(f"User messages: \n")
            file.write(f"MSG: {messages[1]['content']}\n\n")
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
    origin_coord = [origin_coord[0], origin_coord[1]]
    destination_coord = coordinates[destination_key][0]
    destination_coord = [destination_coord[0], destination_coord[1]]
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
        return 'Hard'
    elif poly_number <= 6:
        return 'Medium'
    elif poly_number <= 9: 
        return 'Easy'
    else:
        return 'N/A'
    


def generate_natural_language_review(json_file_path, raw=False):
    with open(json_file_path, 'r') as file:
        data = json.load(file)
    if raw:
        return json.dumps(data, indent=2)
    reviews = []
    for eval_key, eval_data in data.items():
        review = f"Review for {eval_key}:\n"
        review += f"- The solution involves waypoints: {eval_data['solution_waypoints']}.\n"

        if not eval_data['valid']:
            review += "- The path is **invalid** due to the following issues:\n"
            if eval_data.get('violated_polygons'):
                review += f"  - It intersects restricted polygons: {', '.join(eval_data['violated_polygons'])}.\n"
            if eval_data.get('violating_segments'):
                review += f"  - Violating segment(s): {', '.join(str(segment) for segment in eval_data['violating_segments'])}.\n"
        else:
            review += "- The path is valid.\n"

        if eval_data.get('waypoints_outside_flyzone'):
            review += f"- Some waypoints fall outside the flyzone: {eval_data['waypoints_outside_flyzone']}.\n"
        if eval_data.get('human_msg'):
            review += f"- Human message: {eval_data['human_msg']}\n"
        if eval_data.get('human_review'):
            review += f"- Human review: {eval_data['human_review']}\n"
        origin_valid, dest_valid = eval_data['in_origin_dest']
        review += f"- The origin is {'within' if origin_valid else 'outside'} the allowed region.\n"
        review += f"- The destination is {'within' if dest_valid else 'outside'} the allowed region.\n"

        if eval_data.get('optimality'):
            review += f"- Optimality note: {eval_data['optimality']}\n"

        reviews.append(review.strip())

    return "\n\n".join(reviews)

    
    
def add_batch_entry(system_messages: str, user_message: str, custom_id: str = "request-1") -> None:
    """
    Add a new entry to batch.jsonl file with the specified system and user messages.
    
    Args:
        system_messages (str): The system messages to include in the request
        user_message (str): The user message to include in the request
        custom_id (str, optional): The custom ID for the request. Defaults to "request-1".
    """
    entry = {
        "custom_id": custom_id,
        "method": "POST",
        "url": "/v1/chat/completions",
        "body": {
            "model": "o4-mini-2025-04-16",
            "messages": [
                {"role": "system", "content": system_messages},
                {"role": "user", "content": user_message}
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "flight_plan_response",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "waypoints": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "latitude": {"type": "number"},
                                        "longitude": {"type": "number"}
                                    },
                                    "required": ["latitude", "longitude"],
                                    "additionalProperties": False
                                }
                            },
                            "explanation": {"type": "string"}
                        },
                        "required": ["waypoints", "explanation"],
                        "additionalProperties": False
                    }
                }
            }
        }
    }
    
    with open("batch.jsonl", "a") as f:
        f.write(json.dumps(entry, separators=(',', ':')) + "\n")
    


def compute_smoothness(waypoints: List[Tuple[float, float]]) -> float:
    """
    Compute the smoothness of a flight plan, normalized by the angle
    between the origin→destination vector and a horizontal line.

    waypoints: list of (lon, lat) pairs, e.g.
        [[-97.97, 33.36], [-97.97, 33.45], [-96.26, 33.45], [-96.26, 33.42]]

    Returns
    -------
    smoothness = sum(theta_i^2) / theta_base^2

    - theta_i = acos( (v_i · v_{i+1}) / (||v_i|| * ||v_{i+1}||) )
      for each turn between consecutive legs.
    - v_i = vector from waypoint i to i+1.
    - theta_base = acos( x_od / sqrt(x_od^2 + y_od^2) ),
      the angle between the origin→destination vector and the horizontal axis.

    Notes
    -----
    - If fewer than 3 waypoints, returns 0.0 (no turns).
    - If the origin–destination vector is exactly vertical (x_od == 0),
      theta_base = π/2, so the denominator is nonzero.
    - If the origin–destination vector is exactly horizontal (y_od == 0),
      theta_base = 0 and the function returns float('inf').
    """
    n = len(waypoints)
    if n < 3:
        return 1

    # build segment vectors v_i = p_{i+1} - p_i
    vecs = [
        (waypoints[i+1][0] - waypoints[i][0],
         waypoints[i+1][1] - waypoints[i][1])
        for i in range(n-1)
    ]

    # sum of squared turning angles
    sum_sq = 0.0
    for (x1, y1), (x2, y2) in zip(vecs, vecs[1:]):
        norm1 = math.hypot(x1, y1)
        norm2 = math.hypot(x2, y2)
        if norm1 == 0 or norm2 == 0:
            continue
        dot = x1*x2 + y1*y2
        cosang = max(-1.0, min(1.0, dot / (norm1*norm2)))
        theta = math.acos(cosang)
        sum_sq += abs(theta)*abs(theta)

    # origin→destination vector
    x_od = waypoints[-1][0] - waypoints[0][0]
    y_od = waypoints[-1][1] - waypoints[0][1]
    dist_od = math.hypot(x_od, y_od)

    # angle between that vector and horizontal axis
    if dist_od == 0:
        return float('inf')
    # clamp for numerical safety
    cos_base = max(-1.0, min(1.0, x_od / dist_od))
    theta_base = math.acos(cos_base)

    if abs(theta_base) < 1e-12:
        return float('inf')
    if sum_sq == 0:
        return float('inf')
    return (abs(theta_base) * abs(theta_base)) / sum_sq 

def greedy_merge(waypoints, float_coordinates):
    simplified_path = [waypoints[0]]
    obstacles = []
    for place_mark, polygon_coordinates in float_coordinates.items():
        if 'poly' in place_mark:
             obstacles.append(Polygon(polygon_coordinates))
    i = 0
    while i < len(waypoints) - 1:
        # Try to jump as far ahead as possible
        for j in range(len(waypoints)-1, i, -1):
            candidate_line = LineString([waypoints[i], waypoints[j]])
            if not any(candidate_line.intersects(poly) for poly in obstacles):
                simplified_path.append(waypoints[j])
                i = j
                break
    return simplified_path