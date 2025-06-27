import json
import os
import logging
from utils import Evaluation, convert_waypoints

def update_memory(coords, waypoints, evaluation: Evaluation, human_msg):
    """
    Updates the JSON file 'memory_database.json' with a new evaluation entry or updates an existing one.
    
    Parameters:
      coords (dict): Dictionary containing the coordinates. Expected keys:
                     - "polygons": a dict of polygon names to coordinate lists.
                     - "origin": a list representing the origin coordinates.
                     - "destination": a list representing the destination coordinates.
      waypoints (list): List of waypoint dictionaries. Each waypoint should include:
                        "latitude", "longitude", and "altitude".
      evaluation (dict): Dictionary containing evaluation details. Expected keys:
                         - "valid": Boolean indicating if the path is valid.
                         - "evaluation": A string (e.g., "INVALID") describing the evaluation.
                         - "reasoning": A string with the reasoning behind the evaluation.
      idx (int): The evaluation number to update or add.
               This is used as the key in the JSON file.
               
    The JSON file is structured as a dictionary keyed by evaluation numbers (as strings).
    If the file doesn't exist or is empty, a new file is created.
    """
    file_path = "memory_database.json"
    
    # Load existing data if available, otherwise start with an empty dictionary.
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            data = {}
    else:
        data = {}
    keys = list(data.keys())
    keys = [int(key.split('evaluation_number')[-1]) for key in keys]
    keys.sort()
    
    if len(keys) > 0:
        last_element = keys[-1]
        idx = last_element + 1
    else:
        idx = 1
    
    # Create or update the evaluation entry with the provided idx.
    place_marks = coords.keys()
    
    dict_update = {
        "evaluation_number" + str(idx):
        {"polygons": '',
        # "origin": 0,
        # "destination": 0,
        # "flyzone": 0,
        "solution_waypoints": str(convert_waypoints(waypoints)),
        "valid": evaluation.valid,
        "violated_polygons": evaluation.polys,
        "violating_segments": evaluation.segs,
        "in_origin_dest": evaluation.orig_dest_ok,
        "waypoints_outside_flyzone": evaluation.out_pts,
        "human_review": evaluation.human_review,
        "human_msg": human_msg
        # "optimality": evaluation.optimality
        }
    }
    polygon_added = False
    for place_mark in place_marks:
        if 'poly' in place_mark and not polygon_added:
            dict_update["evaluation_number" + str(idx)]['polygons'] = place_mark[:5]
            polygon_added = True
        # elif 'Origin' in place_mark:
        #     dict_update["evaluation_number" + str(idx)]['origin'] = coords.get(place_mark)
        # elif 'Destination' in place_mark:
            # dict_update["evaluation_number" + str(idx)]['destination'] = coords.get(place_mark)
        # elif 'FlyZone' in place_mark:
        #     dict_update["evaluation_number" + str(idx)]['flyzone'] = coords.get(place_mark)
    
    # Write the updated data back to the JSON file.
    data.update(dict_update)
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)
    


def sample_from_memory(poly_name, memory_path='memory_database.json', n_samples=3):
    try:
        with open(memory_path, "r", encoding="utf-8") as f:
            memory_data = json.load(f)
        logging.info("memory_database.json loaded successfully:")
    except FileNotFoundError:
        memory_data = {}
        logging.info("memory_database.json not found. Using an empty dictionary.")
    except json.JSONDecodeError as err:
        memory_data = {}
        logging.info("Error decoding memory_database.json:", err)
    

    i = 0
    polygon_of_interest = poly_name[0:5]
    key_list = []
    for evaluation_number in sorted(memory_data.keys(), key=lambda k: int(k.split('evaluation_number')[-1]), reverse=True):
        if polygon_of_interest == memory_data[evaluation_number]['polygons']:
            key_list.append(evaluation_number)
            i += 1
        if i == n_samples:
            break
        
    filtered_memory_data = {key: memory_data[key] for key in key_list}
    with open("memory.json", "w") as f:
        json.dump(filtered_memory_data, f, indent=2)


