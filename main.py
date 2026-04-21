import logging
from utils import *
import simplekml
from solver import response_generator
from coach import llm_evaluation, interesection_list, rule_based_evaluation
from img_generator import generate_img
from rag.interact import (
    load_scenario,
    get_origin,
    get_destination,
    get_polygons,
    store_output,
    query_similar_feedback,
)
import csv
import os
import re
import argparse
import time
import json
import fcntl
from datetime import datetime, timezone

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
parser.add_argument("--output_path", type=str, default="output.kml", help="Path to save the output KML file")
parser.add_argument("--image_path", type=str, help="Path to save the image")
parser.add_argument("--log", action="store_true", help="Enable logging output", default=True)
parser.add_argument("--report_file", type=str, default="runs.csv", help="Report file path")
parser.add_argument("--human_preference", type=str, help="Human preference for flight planning", default="..." )
parser.add_argument("--system_message", type=str, help="System message for flight planning", default="sys_msg_zero_shot_ours")
parser.add_argument("--coach", action="store_true", help="use coach agent to evaluate the planning", default=False)
parser.add_argument("--human_review", action="store_true", default=False, help="prompt for a human review of the solution")
parser.add_argument("--rag", type=int, default=0, metavar="N", help="load N no-coach RAG examples (problem-only records)")
parser.add_argument("--rag_coach", type=int, default=0, metavar="N", help="load N coach RAG examples (problem + review records)")
parser.add_argument("--no_store", action="store_true", default=False, help="skip writing this run to the RAG DB (read-only ablation mode)")
parser.add_argument("--prompt_log", type=str, default=None, help="append one JSONL record per run (prompt + response + metrics) to this file")

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

# Resolve scenario entities for RAG (load/retrieve/store happen against the same scenario).
scenario = load_scenario(kml_path)
origin_name = next((k for k in float_coordinates if 'Origin' in k), None)
destination_name = next((k for k in float_coordinates if 'Destination' in k), None)
polygon_names = [
    k.lower() for k in float_coordinates
    if 'Origin' not in k and 'Destination' not in k and 'FlyZone' not in k
]
origin_id = int(re.search(r'\d+', origin_name).group()) if origin_name else None
destination_id = int(re.search(r'\d+', destination_name).group()) if destination_name else None
scenario_origin = get_origin(scenario, origin_id) if origin_id is not None else None
scenario_destination = get_destination(scenario, destination_id) if destination_id is not None else None
scenario_polygons = get_polygons(scenario, polygon_names) if polygon_names else []


def _format_rag_examples(records, include_review, header):
    if not records:
        return ""
    lines = ["\n" + header]
    for i, rec in enumerate(records, 1):
        lines.append(f"Example {i}:")
        lines.append(f"  Human preference: {rec.human_preference or '(none)'}")
        lines.append(f"  Solution waypoints: {rec.solution_waypoints}")
        if include_review:
            lines.append(f"  Valid: {rec.is_valid}")
            lines.append(f"  Waypoints outside flyzone: {rec.waypoints_outside_flyzone}")
            lines.append(f"  Violated polygons: {rec.violated_polygon_names}")
            if rec.vlm_feedback:
                lines.append(f"  VLM review: {rec.vlm_feedback}")
            if rec.human_feedback:
                lines.append(f"  Human review: {rec.human_feedback}")
    return "\n".join(lines) + "\n"


rag_context = ""
if (args.rag or args.rag_coach) and scenario_origin and scenario_destination:
    if args.rag_coach:
        coach_records, _ = query_similar_feedback(
            origin=scenario_origin,
            destination=scenario_destination,
            polygons=scenario_polygons,
            human_preference=human_msg,
            filter_by_has_review=True,
            filter_by_validity=True,
            n=args.rag_coach,
        )
        header = "Previous solutions with coach reviews for similar problems:"
        if not coach_records:
            coach_records, _ = query_similar_feedback(
                origin=scenario_origin,
                destination=scenario_destination,
                polygons=scenario_polygons,
                human_preference=human_msg,
                filter_by_has_review=True,
                n=args.rag_coach,
            )
            header = "Previous solutions with coach reviews (invalid — no valid examples found):"
            logging.info("No valid coach records; falling back to invalid coach records.")
        rag_context += _format_rag_examples(
            coach_records, include_review=True,
            header=header,
        )
    if args.rag:
        plain_records, _ = query_similar_feedback(
            origin=scenario_origin,
            destination=scenario_destination,
            polygons=scenario_polygons,
            human_preference=human_msg,
            filter_by_has_review=False,
            n=args.rag,
        )
        rag_context += _format_rag_examples(
            plain_records, include_review=False,
            header="Previous solutions (no review) for similar problems:"
        )
    if rag_context:
        prompt[1] += rag_context
        logging.info(f"Appended RAG context ({len(rag_context)} chars) to prompt.")

start_time = time.time()
response = response_generator(prompt, args.model_name, False, float_coordinates)
planner_inference_time_s = time.time() - start_time
waypoints_list = convert_waypoints(response.waypoints)
logging.info(f"Planner LLM inference time: {planner_inference_time_s:.2f}s")
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
min_clearance_km = min_polygon_clearance_km(waypoints_list, float_coordinates)
logging.info("Total path length: %.2f km" % total_length)
logging.info(f"Min polygon clearance: {min_clearance_km} km")
logging.info(f"Reasoning: {response.explanation}")


# Evaluate the path planning
evaluation = rule_based_evaluation(waypoints_list, float_coordinates)
simplified_waypoints = None
if evaluation.valid:
    simplified_waypoints = greedy_merge(waypoints_list, float_coordinates)
    generate_img(float_coordinates, simplified_waypoints, 'static/simplified_waypoints.png', evaluation)


generate_img(float_coordinates, waypoints_list, args.image_path, evaluation)
logging.info(f"Polygons that are intersected: {evaluation.polys}")
logging.info("Path planning evaluation completed.")
logging.info(f"Valid or not?: {evaluation.valid}")
logging.info(f"Is in flyzone: {evaluation.out_pts}")
logging.info(f"Starts with origin and ends in destination: {evaluation.orig_dest_ok}")


llm_review = None
# Uncomment this to enable Vlm review
# if args.coach and args.image_path: 
#     llm_review = llm_evaluation(evaluation, args.image_path, human_msg)
#     logging.info(f"LLM review aligned={llm_review.aligned}: {llm_review.evaluation}")
#     logging.info(f"LLM reasoning: {llm_review.reasoning}")

if args.coach and args.human_review:
    logging.info("Any comments about the solution?")
    evaluation.human_review = input()


def _format_vlm_feedback(llm_review):
    if llm_review is None:
        return None
    verdict = "ALIGNED" if llm_review.aligned else "NOT ALIGNED"
    return f"[{verdict}] {llm_review.evaluation}\nReasoning: {llm_review.reasoning}"

stored_waypoints = simplified_waypoints if simplified_waypoints else waypoints_list
violated_polygon_objs = [p for p in scenario_polygons if p.name in evaluation.polys] if args.coach else []
human_feedback_text = evaluation.human_review or None
vlm_feedback_text = _format_vlm_feedback(llm_review)

if scenario_origin and scenario_destination and not args.no_store:
    store_output(
        origin=scenario_origin,
        destination=scenario_destination,
        polygons=scenario_polygons,
        human_preference=human_msg,
        solution_waypoints=stored_waypoints,
        is_valid=evaluation.valid,
        in_origin=evaluation.orig_dest_ok[0],
        in_destination=evaluation.orig_dest_ok[1],
        human_feedback=human_feedback_text,
        vlm_feedback=vlm_feedback_text,
        has_review=args.coach,
        waypoints_outside_flyzone=evaluation.out_pts,
        violated_polygons=violated_polygon_objs,
    )
    logging.info(f"Stored run to RAG (has_review={args.coach}).")
elif args.no_store:
    logging.info("Skipped RAG store (--no_store).")


logging.info("Process completed.")
if args.coach and args.human_review:
    aligned_with_human_preference = "True" if evaluation.human_review == "" else "False"
elif llm_review is not None:
    aligned_with_human_preference = str(llm_review.aligned)
else:
    aligned_with_human_preference = None
solution = PlannerSolution()
solution.core_metrics["distance_km"] = total_length
solution.core_metrics = {"distance_km": total_length,
                            "min_polygon_clearance_km": min_clearance_km,
                            "num_waypoints": len(response.waypoints),
                            "planner_inference_time_s": planner_inference_time_s,
                            "energy": 0.0,
                            "is_valid": evaluation.valid,
                            "orig_dest": evaluation.orig_dest_ok,
                            "fly_zone": evaluation.out_pts,
                            "avoid_polygons": evaluation.polys,
                            "model": args.model_name,
                            "mode": mode_detector(args.place_marks),
                            "rag": args.rag,
                            "rag_coach": args.rag_coach,
                            "solution_waypoints": response.waypoints,
                            "polygon_number": args.place_marks[0],
                           "human_preference": args.human_preference,
                           "orig_dest": [args.place_marks[1], args.place_marks[2]],
                           "aligned_with_human_preference": aligned_with_human_preference,
                           "vlm_aligned": llm_review.aligned if llm_review else None,
                           "vlm_evaluation": llm_review.evaluation if llm_review else None,
                           "vlm_reasoning": llm_review.reasoning if llm_review else None,
                           "human_feedback": human_feedback_text}
        


if args.prompt_log:
    log_dir = os.path.dirname(args.prompt_log)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": args.model_name,
        "scenario": {
            "polygon": args.place_marks[0] if args.place_marks else None,
            "origin": origin_name,
            "destination": destination_name,
            "origin_id": origin_id,
            "destination_id": destination_id,
            "polygon_names": polygon_names,
            "kml_path": args.kml_path,
        },
        "human_preference": human_msg,
        "flags": {
            "rag": args.rag,
            "rag_coach": args.rag_coach,
            "coach": args.coach,
            "human_review": args.human_review,
            "no_store": args.no_store,
            "system_message": args.system_message,
        },
        "rag_context": rag_context,
        "prompt": {
            "system": prompt[0],
            "user": prompt[1],
        },
        "response": {
            "waypoints": [wp.model_dump() if hasattr(wp, "model_dump") else wp for wp in response.waypoints],
            "explanation": getattr(response, "explanation", None),
        },
        "evaluation": {
            "is_valid": evaluation.valid,
            "orig_dest_ok": list(evaluation.orig_dest_ok),
            "waypoints_outside_flyzone": evaluation.out_pts,
            "violated_polygons": evaluation.polys,
            "human_review": evaluation.human_review,
        },
        "vlm_feedback": vlm_feedback_text,
        "metrics": {
            "distance_km": total_length,
            "num_waypoints": len(response.waypoints),
            "min_polygon_clearance_km": min_clearance_km,
            "planner_inference_time_s": planner_inference_time_s,
        },
    }
    with open(args.prompt_log, "a") as _plf:
        fcntl.flock(_plf.fileno(), fcntl.LOCK_EX)
        try:
            _plf.write(json.dumps(record, default=str) + "\n")
            _plf.flush()
        finally:
            fcntl.flock(_plf.fileno(), fcntl.LOCK_UN)
    logging.info(f"Appended prompt/response record to {args.prompt_log}")

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
