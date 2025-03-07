import xml.etree.ElementTree as ET
import simplekml
import math
from pydantic import BaseModel




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

def convert_to_float_dict(coord_dict):
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
        float_coords = [
            [float(number) for number in coord.split(',')]
            for coord in coord_strings
        ]
        float_dict[key] = float_coords
    return float_dict

def prompt_generator(kml_path, placemarks):
    """
    Generates a prompt for the flight planner based on KML file and placemark names.

    Parameters:
        kml_path (str): Path to the KML file.
        placemarks (list): List of placemark names to include in the prompt.

    Returns:
        str: The generated prompt for the flight planner.
    """
    coordinates_dict = get_coordinates_from_kml(kml_path, placemarks)
    user_msg = 'Now you have to generate a flight plan avoiding the wind polygons for the following problem: \n'
    system_msg= '''You are a flight planner for an eVTOL aircraft. 
      The user will give you a bunch of wind hazard polygons' information
       and asks you to generate a flight plan from a start to an end point. 
      You have to generate a flight plan which is basically a bunch of 
      way points starting from the start coordinate and 
      ending in the end coordinate while avoiding the wind polygons 
      (first you have to draw the draw the polygons in your brain and 
      try to generate a flight plan that avoids them). 
      Always include the start and end point in your response. 
      You can generate as many waypoints as you want in order to avoid the polygons.
      You have to stay in the fly zone. Try to find the shortest path. Note: The 
      shortest path is usually a straight line between the origin and the destination.
      Here you probably need to find the closest line to this line while avoiding
      wind hazardous areas. You may need to add more waypoints to find the shortest
      path. \n'''
    if coordinates_dict:
        for name, coords in coordinates_dict.items():
            user_msg += (f"Coordinates for '{name}':\n{coords}\n")
    else:
        print("No matching placemarks found in the KML file.")
    return [system_msg, user_msg]

def convert_waypoints(waypoints):
    return [[wp.longitude, wp.latitude, wp.altitude] for wp in waypoints]

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
    altitude: float

class FlightPlan(BaseModel):
    waypoints: list[Waypoint]
    explanation: str

class Evaluation(BaseModel):
    valid: bool
    evaluation: str
    reasoning: str

# [Waypoint(latitude=32.55, longitude=-96.3, altitude=150.0),
#  Waypoint(latitude=32.55, longitude=-97.6, altitude=150.0),
#  Waypoint(latitude=33.0, longitude=-97.6, altitude=150.0),]


# response
# response.waypoints =  [Waypoint(latitude=32.55, longitude=-96.3, altitude=150.0),
#  Waypoint(latitude=32.55, longitude=-97.6, altitude=150.0),
#  Waypoint(latitude=33.0, longitude=-97.6, altitude=150.0),]
# response.explanation = "A star method"