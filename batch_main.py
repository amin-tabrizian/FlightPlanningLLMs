import logging
from utils import *
from solver import batch_response_generator
from update_memory import update_memory, sample_from_memory
from coach import llm_evaluation, interesection_list, rule_based_evaluation
from img_generator import generate_img
import csv
import os
import argparse
import time

"""
Generates a dictionary of coordinates for the given KML file and placemark names.

Parameters:
    kml_path (str): Path to the KML file.
    placemarks (list): List of placemark names to extract coordinates for.

Returns:
"""

# Setup command line argument parser
parser = argparse.ArgumentParser(description="Process KML file and extract place marks.")
parser.add_argument("kml_path", type=str, help="Path to the input KML file")
parser.add_argument("--log", action="store_true", help="Enable logging output")
# parser.add_argument("--coach", action="store_true", help="use coach agent to evaluate the planning")

args = parser.parse_args()

# Configure logging: INFO messages are shown if --log is provided; otherwise only warnings and above
logging.basicConfig(
    level=logging.INFO if args.log else logging.WARNING,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logging.info("Starting coordinate extraction.")
kml_path = args.kml_path
placemarks_list = [
    ['poly1', 'Origin1', 'Destination1'],
    ['poly2', 'Origin3', 'Destination1'],
    ['poly3', 'Origin1', 'Destination5'],
    ['poly4', 'Origin2', 'Destination2'],
    ['poly5', 'Origin1', 'Destination3'],
    ['poly6', 'Origin1', 'Destination4'],
    ['poly7', 'Origin5', 'Destination1'],
    ['poly8', 'Origin1', 'Destination5'],
    ['poly9', 'Origin3', 'Destination3']
]
system_messages = ["sys_msg_zero_shot_ours", "sys_msg_zero_shot", "sys_msg_raw", "sys_msg_one_shot_hard", "sys_msg_one_shot_easy"]
human_preferences = ["Find the SHORTEST path possible.", "Find the path with as FEW WAYPOINTS as possible."]
# Extract and convert coordinates
for i, placemarks in enumerate(placemarks_list):
    for system_message in system_messages:
        for human_preference in human_preferences:

            coordinates_dict = get_coordinates_from_kml(kml_path, placemarks)
            float_coordinates = convert_to_float_dict(coordinates_dict, approx=False)
            logging.info("Coordinates extracted and converted to float format.")

            # Generate prompt for flight planning
            # human_msg = "I believe the best path will between the wind polygon 5-3 and 5-1."
            human_msg = human_preference
            prompt = prompt_generator(kml_path, placemarks, human_msg, samples=False, system_message = system_message)
            logging.info("Generated prompt for flight planning.")
            if "SHORTEST" in human_msg:
                human_msg_number = 1
            elif "WAYPOINTS" in human_msg:
                human_msg_number = 2
            else:
                human_msg_number = 0

            logging.info("Received flight plan response from API.")

            add_batch_entry(prompt[0], prompt[1], f"request-{i}-{placemarks[0][-1]}-{placemarks[1][-1]}-{placemarks[2][-1]}-{human_msg_number}-{system_message}")
start_time = time.time()
# batch = batch_response_generator()
# print(batch)
# end_time = time.time()
