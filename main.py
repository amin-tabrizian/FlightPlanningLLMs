from utils import get_coordinates_from_kml, convert_to_float_dict, prompt_generator, convert_waypoints
import simplekml

from pydantic import BaseModel
from openai import OpenAI
import argparse
"""
Generates a dictionary of coordinates for the given KML file and placemark names.

Parameters:
    kml_path (str): Path to the KML file.
    placemarks (list): List of placemark names to extract coordinates for.

Returns:
"""
parser = argparse.ArgumentParser(description="Process KML file and extract place marks.")

parser.add_argument("kml_path", type=str, help="Path to the input KML file")
parser.add_argument("place_marks", nargs='+', help="Name of the place marks to extract")
parser.add_argument("output_path", type=str, help="Path to save the output file")

args = parser.parse_args()
kml_path = args.kml_path
placemarks = args.place_marks
coordinates_dict = get_coordinates_from_kml(kml_path, placemarks)
float_coordinates = convert_to_float_dict(coordinates_dict)
output = prompt_generator(kml_path, placemarks)
polygon_kml = simplekml.Kml()

if float_coordinates:
    for name, coords in float_coordinates.items():
        if name == 'Origin':
            polygon_kml.newpoint(name=name, coords=coords)
        elif name == 'Destination':
            polygon_kml.newpoint(name=name, coords=coords)
        elif name == 'FlyZone':
            polygon = polygon_kml.newpolygon(name=name, outerboundaryis=coords)
            polygon.style.polystyle.color = simplekml.Color.changealphaint(51, simplekml.Color.red)
        else:
            polygon_kml.newpolygon(name=name, outerboundaryis=coords)

client = OpenAI()
class Waypoint(BaseModel):
    latitude: float
    longitude: float
    altitude: float
class FlightPlan(BaseModel):
    waypoints: list[Waypoint]
    explanation: str

completion = client.beta.chat.completions.parse(
    model="o3-mini-2025-01-31",
    messages=[
        {"role": "system", "content": "You are a helpful flight planner."},
        {"role": "user", "content": output},
    ],
    response_format=FlightPlan,
)

response = completion.choices[0].message.parsed
line = polygon_kml.newlinestring(name="PolySolution", 
                          coords=convert_waypoints(response.waypoints))
line.style.linestyle.color = simplekml.Color.red
line.style.linestyle.width = 5   

                
print(response.waypoints)
polygon_kml.save(args.output_path)