import json
import os

def update_memory(coords, waypoints, evaluation):
    """
    Updates the JSON file 'memory.json' with a new evaluation entry or updates an existing one.
    
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
    file_path = "memory.json"
    
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
    keys.sort()
    if len(keys) > 0:
        idx = int(keys[-1][-1]) + 1
    else:
        idx = 1
    
    # Create or update the evaluation entry with the provided idx.
    place_marks = coords.keys()
    
    dict_update = {
        "evaluation_number" + str(idx):
        {"polygons": {},
        "origin": 0,
        "destination": 0,
        "flyzone": 0,
        "waypoints": str(waypoints),
        "valid": evaluation.valid,
        "evaluation": evaluation.evaluation,
        "reasoning": evaluation.reasoning}
    }

    for place_mark in place_marks:
        if 'poly' in place_mark:
            dict_update["evaluation_number" + str(idx)]['polygons'].update({place_mark: coords.get(place_mark)})
        elif 'Origin' in place_mark:
            dict_update["evaluation_number" + str(idx)]['origin'] = coords.get(place_mark)
        elif 'Destination' in place_mark:
            dict_update["evaluation_number" + str(idx)]['destination'] = coords.get(place_mark)
        elif 'FlyZone' in place_mark:
            dict_update["evaluation_number" + str(idx)]['flyzone'] = coords.get(place_mark)
    
    # Write the updated data back to the JSON file.
    data.update(dict_update)
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)
