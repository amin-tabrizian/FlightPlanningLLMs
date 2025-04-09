from openai import OpenAI
import anthropic
import logging
import instructor
import json
from utils import save_messages_to_file
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
from utils import convert_coordinates_to_airspace_auto  

def response_generator(output, model, memory, float_coordinates):
    system_msg = output[0]
    user_msg = output[1]
    if model == "o3-mini":
        model = "o3-mini-2025-01-31"
    elif model == "claude-3-7":
        model = "claude-3-7-sonnet-20250219"
    elif model == "claude-3-5":
        model = "claude-3-5-haiku-20241022"
    if memory == True:
        with open('memory.json', 'r') as json_file:
            data = json.load(json_file)
        memory_prompt = "Here are some examples of previous \
                        Flight plannings with evaluations: \n" + json.dumps(data)
    else:
        memory_prompt = ""
        logging.info("Memory is deactivated.")
    if model == "gpt-4o" or model == "o3-mini-2025-01-31" or model == "gpt-4o-mini":
        client = OpenAI()
        logging.info("Requesting flight plan from OpenAI API.")
        messages = [
                {"role": "system", "content": system_msg + memory_prompt},
                {"role": "user", "content":  user_msg},
            ]
        completion = client.beta.chat.completions.parse(
            model=model,
            messages=messages,
            response_format=FlightPlan,
        )
        response = completion.choices[0].message.parsed

    elif model == "claude-3-7-sonnet-20250219" or model == "claude-3-5-haiku-20241022":
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

def genAStar(start: int, goal: int, airspace: dict, ovs, speed_bounds, n_iter=10000, dist=15000, show_plots=True):
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