from openai import OpenAI
import anthropic
import logging
import instructor
import json
from utils import save_messages_to_file, convert_waypoints
from utils import FlightPlan
from typing import Dict, List
from pathlib import Path
from time import perf_counter
import numpy as np
from shapely.geometry import Polygon, Point
from src.Airspace import Airspace
from src.functions import displayRouteAirspace
from src.RouteBuilding import AStar
from utils import Waypoint  
from utils import convert_coordinates_to_airspace_auto, generate_natural_language_review
from coach import rule_based_evaluation

def batch_response_generator(batch_path='batch.jsonl', description="Test"):
    client = OpenAI()
    batch_input_file = client.files.create(
    file=open(batch_path, "rb"),
    purpose="batch",
    )
    batch_input_file_id = batch_input_file.id
    batch = client.batches.create(
        input_file_id=batch_input_file_id,
        endpoint="/v1/chat/completions",
        completion_window="24h",
        metadata={
            "description": description
        }
    )
    return batch
def response_generator(input, model, memory, float_coordinates):
    system_msg = input[0]
    user_msg = input[1]
    if model == "o3-mini":
        model = "o3-mini-2025-01-31"
    elif model == "o3":
        model = "o3-2025-04-16"
    elif model == "claude-3-7":
        model = "claude-3-7-sonnet-20250219"
    elif model == "claude-3-5":
        model = "claude-3-5-haiku-20241022"
    elif model == "claude-4-sonnet":
        model = "claude-sonnet-4-0"
    elif model == "claude-4-opus":
        model = "claude-opus-4-20250514"
    if memory == True:
        memory_prompt = "Here are previous responses of Flight plannings with evaluations: \n" + generate_natural_language_review('memory.json')
    else:
        memory_prompt = ""
        logging.info("Memory is deactivated.")
    if model == "gpt-4o" or model == "o3-mini-2025-01-31" or model == "gpt-4o-mini" or model == "o4-mini" or model == "o3-2025-04-16":
        client = OpenAI()
        logging.info("Requesting flight plan from OpenAI API.")
        messages = [
                {"role": "system", "content": system_msg},
                {"role": "user", "content":  user_msg + memory_prompt},
            ]
        completion = client.beta.chat.completions.parse(
            model=model,
            messages=messages,
            response_format=FlightPlan,
            # temperature=0.0000001,
            seed=12345,
            # top_p=0.00000001,
        )
        system_fingerprint = getattr(completion, 'system_fingerprint', None)
        logging.info(f"System fingerprint is {system_fingerprint if system_fingerprint else 'not available'}")
        response = completion.choices[0].message.parsed
    elif model == "claude-3-7-sonnet-20250219" or model == "claude-3-5-haiku-20241022" or model == "claude-sonnet-4-0" or model ==  "claude-opus-4-20250514":
        client = instructor.from_anthropic(
        anthropic.Anthropic(),
        )
        logging.info("Requesting flight plan from Anthropic API.")
        messages = [
                {"role": "system", "content": system_msg + memory_prompt},
                {"role": "user", "content":  user_msg},]
        response = client.chat.completions.create(

            max_tokens=1024,
            model=model,
            messages= messages,
            response_model=FlightPlan
        )
    
    elif model == "Astar":
        logging.info("A* has been chosen as the method.")
        response = Astar_Path(
        coordinates= float_coordinates,
        show_plots=True,
        max_workers=20,
        method="AStar",
        ov_mode="spheroid",
        n_ac=100,
        speed_bounds=[17, 21],
    )
        logging.info("A* path planning is done!")
    
    if model !='Astar':

        save_messages_to_file(messages, "messages.txt")
    
    return response

def try_next_attempts(input, previous_output, review, model, float_coordinates, attempt_number= 0, number_of_attempts=3):
    while attempt_number < number_of_attempts:
        system_msg = input[0]
        user_msg = input[1]
        user_msg += (f"This is your previous response which is invalid. \n {previous_output}"
                      f"The reason for the invalidity is: {review} "
                    )
        if model == "o3-mini":
            model = "o3-mini-2025-01-31"
        elif model == "o3":
            model = "o3"
        elif model == "claude-3-7":
            model = "claude-3-7-sonnet-20250219"
        elif model == "claude-3-5":
            model = "claude-3-5-haiku-20241022"
        if model == "gpt-4o" or model == "o3-mini-2025-01-31" or model == "gpt-4o-mini":
            client = OpenAI()
            logging.info("Requesting flight plan from OpenAI API.")
            messages = [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content":  user_msg},
                ]
            completion = client.beta.chat.completions.parse(
                model=model,
                messages=messages,
                response_format=FlightPlan,
                temperature=0,
                seed=12345,
            )
            response = completion.choices[0].message.parsed

        elif model == "claude-3-7-sonnet-20250219" or model == "claude-3-5-haiku-20241022":
            client = instructor.from_anthropic(
            anthropic.Anthropic(),
            )
            logging.info("Requesting flight plan from Anthropic API.")
            messages = [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content":  user_msg},]
            response = client.chat.completions.create(
                max_tokens=1024,
                model=model,
                messages= messages,
                response_model=FlightPlan
            )
        evaluation = rule_based_evaluation(convert_waypoints(response.waypoints), float_coordinates)
        if not evaluation.intesects:
            review = generate_natural_language_review(evaluation)
        else:
            return response
        try_next_attempts(input, response, review, model, float_coordinates, attempt_number + 1, number_of_attempts)
        

    raise Exception("No valid path generated.")

def Astar_Path(
    coordinates: Dict[str, List[List[float]]],
    show_plots: bool = True,
    max_workers: int = 20,
    ov_mode="dryvr",
    n_ac: int = 100,
    method: str = "AStar",
    speed_bounds: List[int] = [23, 28],
) -> List[Waypoint]:
    
    start_time = perf_counter()

    # Convert coordinates dict into standard airspace format
    airspace: dict = convert_coordinates_to_airspace_auto(coordinates)
    ovs = Airspace(airspace["airspace"][0])

    origin = airspace["points"][0]
    destination = airspace["points"][1]

   
    # Generate route using A*
    if method == "AStar":
        route = genAStar(
            start=0,
            goal=1,
            airspace=airspace,
            ovs=ovs,
            speed_bounds=speed_bounds,
            show_plots=show_plots
        )

        
        waypoints= \
        [
            Waypoint(latitude=point.y, longitude=point.x, altitude=100)
            for point in route.route
        ]
        flight_plan = FlightPlan(
        waypoints=waypoints,
        explanation="A star method"
)

        route_np = np.asarray([[point.y, point.x, 100] for point in route.route])

    else:
        raise ValueError(f"{method} is not a valid route generation technique.")

    return flight_plan

def genAStar(start: int, goal: int, airspace: dict, ovs, speed_bounds, n_iter=100000, dist=12000, show_plots=True):
    offset = np.random.poisson(lam=5) * 20

    found = False

    while offset <= 300 and not found:
        astar: AStar = AStar(airspace["airspace"][0], airspace["nfzs"].values(), offset=offset)
        print("OFFSET = :", astar.offset)
        print(start, goal)

        start_pos = (airspace["points"][start].x, airspace["points"][start].y)
        goal_pos = (airspace["points"][goal].x, airspace["points"][goal].y)

        path = astar.find_path(start_pos, goal_pos, ovs, n_iter=n_iter, dist=dist, break_on_found=False)

        if path is None:
            offset += 30
        else:
            found = True

    # Route display
    if show_plots:
       pass

    return astar

