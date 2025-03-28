import logging
from utils import *
import simplekml
from solver import response_generator
from update_memory import update_memory, sample_from_memory
from coach import evaluate_path_planning
from img_generator import generate_img

import argparse

"""
Generates a dictionary of coordinates for the given KML file and placemark names.

Parameters:
    kml_path (str): Path to the KML file.
    placemarks (list): List of placemark names to extract coordinates for.

Returns:
"""

# Setup command line argument parser
parser = argparse.ArgumentParser(description="Process KML file and extract place marks.")
parser.add_argument("model_name", type=str, help="Path to the input KML file")
parser.add_argument("kml_path", type=str, help="Path to the input KML file")
parser.add_argument("place_marks", nargs='+', help="Name of the place marks to extract")
parser.add_argument("output_path", type=str, help="Path to save the output file")
parser.add_argument("--image_path", type=str, help="Path to save the image")
parser.add_argument("--log", action="store_true", help="Enable logging output")
parser.add_argument("--memory", action="store_true", help="Enable memory")

args = parser.parse_args()

# Configure logging: INFO messages are shown if --log is provided; otherwise only warnings and above
logging.basicConfig(
    level=logging.INFO if args.log else logging.WARNING,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logging.info("Starting coordinate extraction.")
kml_path = args.kml_path
placemarks = args.place_marks

# Extract and convert coordinates
coordinates_dict = get_coordinates_from_kml(kml_path, placemarks)
float_coordinates = convert_to_float_dict(coordinates_dict, approx=False)
logging.info("Coordinates extracted and converted to float format.")

# Generate prompt for flight planning
# human_msg = "I believe the best path will between the wind polygon 5-3 and 5-1."
human_msg = ""
output = prompt_generator(kml_path, placemarks, human_msg, samples=False)
logging.info("Generated prompt for flight planning.")

# Set up the OpenAI client and define data models for the flight plan


logging.info("Received flight plan response from API.")

# Create a new KML object and add points/polygons based on placemark names
polygon_kml = simplekml.Kml()
if float_coordinates:
    for name, coords in float_coordinates.items():
        if 'Origin' in name:
            polygon_kml.newpoint(name=name, coords=coords)
            logging.info(f"Added point for {name}.")
        elif 'Destination' in name:
            polygon_kml.newpoint(name=name, coords=coords)
            logging.info(f"Added point for {name}.")
        elif name == 'FlyZone':
            polygon = polygon_kml.newpolygon(name=name, outerboundaryis=coords)
            polygon.style.polystyle.color = simplekml.Color.changealphaint(51, simplekml.Color.red)
            logging.info(f"Added polygon for {name} with special style.")
        else:
            polygon_kml.newpolygon(name=name, outerboundaryis=coords)
            logging.info(f"Added polygon for {name}.")
else:
    logging.warning("No float coordinates found from KML file.")
# Add the flight plan as a linestring to the KML
if args.memory:
    sample_from_memory(args.place_marks[0],memory_path='memory_database.json', n_samples=5)
response = response_generator(output, args.model_name, args.memory)
line = polygon_kml.newlinestring(name="PolySolution", 
                                 coords=convert_waypoints(response.waypoints))
line.style.linestyle.color = simplekml.Color.green
line.style.linestyle.width = 5
logging.info("Added polyline for flight plan.")

# Output the flight plan waypoints and save the KML file
logging.info(f"Flight plan waypoints: {response.waypoints}")
polygon_kml.save(args.output_path)
logging.info(f"KML file saved to {args.output_path}.")
logging.info("Total path length: %.2f km" % compute_total_path_length(response.waypoints))


# Evaluate the path planning
generate_img(float_coordinates, convert_waypoints(response.waypoints), args.image_path)
evaluation = evaluate_path_planning(args.image_path)
logging.info("Path planning evaluation completed.")
logging.info(f"Evaluation: {evaluation.valid}")
logging.info(f"Evaluation: {evaluation.reasoning}")
logging.info(f"Evaluation: {evaluation.evaluation}")
logging.info(f"Evaluation: Is the evaluation valid? (Y/N)")
user_input = input()
if user_input == "Y":
    update_memory(float_coordinates, response.waypoints, evaluation)
    logging.info("Memory updated with evaluation results.")
    
if user_input == "N":
    logging.info("Do you want to chagent the evaluation?")
    user_input = input()
    if user_input == "Y":
        logging.info("Please provide the new evaluation (valid).")
        evaluation.valid = input()
        logging.info("Please provide the new evaluation (reasoning).")
        evaluation.reasoning = input()
        logging.info("Please provide the new evaluation (evaluation).")
        evaluation.evaluation = input()
        logging.info("Memory updated with evaluation results.")
        update_memory(float_coordinates, response.waypoints, evaluation)
    if user_input == "N":
        logging.info("Memory not updated.")


logging.info("Process completed.")
