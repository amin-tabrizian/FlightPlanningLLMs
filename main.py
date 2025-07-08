import logging
from utils import *
import simplekml
from solver import response_generator
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
parser.add_argument("model_name", type=str, help="Path to the input KML file")
parser.add_argument("kml_path", type=str, help="Path to the input KML file")
parser.add_argument("place_marks", nargs='+', help="Name of the place marks to extract")
parser.add_argument("output_path", type=str, help="Path to save the output file")
parser.add_argument("--image_path", type=str, help="Path to save the image")
parser.add_argument("--log", action="store_true", help="Enable logging output")
parser.add_argument("--memory", action="store_true", help="Enable memory")
parser.add_argument("--report_file", type=str, help="Report file path")
parser.add_argument("--human_preference", type=str, help="Human preference for flight planning" )
parser.add_argument("--system_message", type=str, help="System message for flight planning" )
parser.add_argument("--coach", action="store_true", help="use coach agent to evaluate the planning")

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
human_msg = args.human_preference if args.human_preference else ""
prompt = prompt_generator(float_coordinates, placemarks, human_msg, samples=False, system_message = args.system_message)
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
    sample_from_memory(args.place_marks[0],memory_path='memory_database.json', n_samples=2)
start_time = time.time()
response = response_generator(prompt, args.model_name, args.memory, float_coordinates)
waypoints_list = convert_waypoints(response.waypoints)
end_time = time.time()
line = polygon_kml.newlinestring(name="PolySolution", 
                                 coords=waypoints_list)
line.style.linestyle.color = simplekml.Color.green
line.style.linestyle.width = 5
logging.info("Added polyline for flight plan.")

# Output the flight plan waypoints and save the KML file
logging.info(f"Flight plan waypoints: {waypoints_list}")
polygon_kml.save(args.output_path)
logging.info(f"KML file saved to {args.output_path}.")
total_length = compute_total_path_length(convert_waypoints(response.waypoints))
logging.info("Total path length: %.2f km" % total_length)
logging.info(f"Reasoning: {response.explanation}")


# Evaluate the path planning
evaluation = rule_based_evaluation(waypoints_list, float_coordinates)
simplified_waypoints = None
if evaluation.valid:
    simplified_waypoints = greedy_merge(waypoints_list, float_coordinates)
    generate_img(float_coordinates, simplified_waypoints, 'flight_plans/simplified_waypoints.png', evaluation)


generate_img(float_coordinates, waypoints_list, args.image_path, evaluation)
logging.info(f"Polygons that are intersected: {evaluation.polys}")
# evaluation = llm_evaluation(evaluation, args.image_path)
logging.info("Path planning evaluation completed.")
logging.info(f"Valid or not?: {evaluation.valid}")
logging.info(f"Is in flyzone: {evaluation.out_pts}")
logging.info(f"Starts with origin and ends in destination: {evaluation.orig_dest_ok}")



if args.coach:
    logging.info(f"Any comments about the solution?")
    evaluation.human_review = input()
    if simplified_waypoints:
        update_memory(float_coordinates, convert_waypoints_to_dict(simplified_waypoints), evaluation, human_msg)
    else:
        update_memory(float_coordinates, response.waypoints, evaluation, human_msg)
logging.info("Memory updated with evaluation results.")


logging.info("Process completed.")
if evaluation.human_review == "":
    evaluation.human_review = "True"
else:
    evaluation.human_review = "False"
solution = PlannerSolution()
solution.core_metrics["distance_km"] = total_length
solution.core_metrics = {"distance_km": total_length,       
                            "num_waypoints": len(response.waypoints),      
                            "response_time_s": end_time - start_time,   
                            "energy": 0.0,           
                            "is_valid": evaluation.valid,        
                            "orig_dest": evaluation.orig_dest_ok,       
                            "fly_zone": evaluation.out_pts,        
                            "avoid_polygons": evaluation.polys,  
                            "model": args.model_name,
                            "mode": mode_detector(args.place_marks),              
                            "memory": args.memory,
                            "solution_waypoints": response.waypoints, 
                            "polygon_number": args.place_marks[0],   
                           "human_preference": args.human_preference,
                           "orig_dest": [args.place_marks[1], args.place_marks[2]],
                           "aligned_with_human_preference": evaluation.human_review}   
        


if args.report_file:
    # Create the report file path
    report_dir = os.path.dirname(args.report_file)
    if report_dir and not os.path.exists(report_dir):
        os.makedirs(report_dir)
    
    # Check if file exists to determine if we need to write headers
    file_exists = os.path.isfile(args.report_file)
    
    # Write to CSV file
    with open(args.report_file, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=solution.core_metrics.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(solution.core_metrics)
    logging.info(f"Core metrics written to {args.report_file}")
