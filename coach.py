import base64
import os
from openai import OpenAI
import anthropic
import instructor
import shapely
from pydantic import BaseModel
from utils import convert_waypoints
import logging
from utils import Evaluation, haversine_distance


class LLMReview(BaseModel):
    aligned: bool
    evaluation: str
    reasoning: str

_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
client = OpenAI()
# client = anthropic.Anthropic()



def find_waypoints_outside_flyzone(waypoints, float_coordinates):
    path_coordinates = waypoints
    flyzone = shapely.Polygon(float_coordinates['FlyZone'])
    out_waypoints = []
    for point in path_coordinates:
        point = shapely.Point(point)
        if not flyzone.contains(point):
            out_waypoints.append([point.x, point.y])
    return out_waypoints

def origin_dest_verifyer(waypoints, float_coordinates):
    path_coordinates = waypoints
    path_origin = path_coordinates[0]
    path_destination = path_coordinates[-1]
    errors = [True, True]
    for name in float_coordinates:
        if 'Origin' in name:
            real_origin = name
        if 'Destination' in name:
            real_destination = name
    origin = float_coordinates[real_origin][0]
    destination = float_coordinates[real_destination][0]
    origin_error = haversine_distance(path_origin, origin)
    destination_error = haversine_distance(path_destination, destination)
    if origin_error > 1e-2:
        errors[0] = False
    if destination_error > 1e-2:
        errors[1] = False 
    return errors

# Function to see if a path intersects with a polygon
def interesection_list(waypoints, float_coordinates):
    # Convert the path to a shapely LineString
    path_coordinates = waypoints
    i = 0
    intersects = dict()
    while i < len(path_coordinates) - 1:
        path_line = shapely.LineString(waypoints[i:i+2])
        for place_mark, polygon_coordinates in float_coordinates.items():
        #     if 'poly' in place_mark:
        #         polygon = shapely.Polygon(polygon_coordinates)
        #         if path_line.intersects(polygon):
        #             viol_line_seg = (path_coordinates[i], path_coordinates[i + 1])
        #             if place_mark not in intersects.keys():
        #                 intersects[place_mark] = [viol_line_seg]
        #             else:
        #                 intersects[place_mark].append(viol_line_seg)
        # i += 1
            if 'Origin' not in place_mark and 'Destination' not in place_mark and 'FlyZone' not in place_mark:
                    polygon = shapely.Polygon(polygon_coordinates)
                    if path_line.intersects(polygon):
                        viol_line_seg = (path_coordinates[i], path_coordinates[i + 1])
                        if place_mark not in intersects.keys():
                            intersects[place_mark] = [viol_line_seg]
                        else:
                            intersects[place_mark].append(viol_line_seg)
        i += 1
    return intersects

def rule_based_evaluation(waypoints, float_coordinates):
    evaluation = Evaluation(valid=True, 
                            polys=[],
                            segs= [],
                            orig_dest_ok=[True, True],
                            out_pts=[],
                            human_review="")
    # Check if the path intersects with any polygon
    intersects = interesection_list(waypoints, float_coordinates)
    in_flyzone = find_waypoints_outside_flyzone(waypoints, float_coordinates)
    in_origin_dest = origin_dest_verifyer(waypoints, float_coordinates)
    evaluation.polys = list((intersects.keys()))
    evaluation.segs = list((intersects.values()))
    evaluation.out_pts = in_flyzone
    evaluation.orig_dest_ok = in_origin_dest
    if len(intersects) > 0 or \
        len(in_flyzone) > 0 or \
        in_origin_dest[0] == False \
        or in_origin_dest[1] == False:
        evaluation.valid = False
    return evaluation

    

# Function to encode the image
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")
COACH_PROMPT = """You are a senior flight-operations reviewer evaluating an eVTOL flight plan that was produced by an automated planner.

SCOPE
Validity checks (polygon intersection, flyzone containment, origin/destination endpoints) have already been performed by geometric tools upstream. DO NOT re-evaluate validity. Your ONLY job is to judge how well the flight plan aligns with the flight operator's preference, or - if no preference is given - how optimal the plan looks.

LEGEND (what you will see in the image)
- Green rectangle: the flyzone.
- Yellow polygons (labeled poly1-1, poly1-2, ...): hazardous zones.
- Green dot labeled "Origin": start of the route.
- Blue dot labeled "Destination": end of the route.
- Black line segments: path segments not intersecting any hazardous polygon.
- Red line segments: path segments intersecting a hazardous polygon. (Informational only - ignore for this review.)

GEOMETRIC EVALUATION (ground truth from upstream tools - trust this over the image)
{geometric_summary}

FLIGHT OPERATOR PREFERENCE
\"\"\"{human_preference}\"\"\"

EVALUATION TASK

STEP 0 - Check validity first (from the GEOMETRIC EVALUATION block above):
- If "Valid overall" is False, the path is INVALID. Do NOT judge preference alignment or optimality. Return:
    aligned = False
    evaluation = "Path is invalid - alignment not evaluated."
    reasoning = a short summary of which geometric rule was broken (e.g. "Path intersects hazardous polygons poly1-1 and poly1-7." or "Final waypoint does not reach the destination." or "Waypoint X lies outside the flyzone.").
  Stop here.

STEP 1 - Only if the path is valid, evaluate alignment:
- If a meaningful preference is provided above (non-empty and not "No preference" / "Do whatever looks reasonable"):
    Judge how well the path follows that preference. Be specific about which part of the route satisfies or violates it (e.g. "the path hugs the eastern boundary as requested" or "the detour passes within 2 km of the hospital despite the max-clearance preference"). Set `aligned = True` only if the path clearly follows the preference.
- If no meaningful preference is provided:
    Judge the path on optimality only - is it close to the shortest reasonable route? Are there unnecessary detours, zig-zags, or sharp turns that a shorter path could avoid? Is buffer space used only where it earns safety, not arbitrarily? Set `aligned = True` if the path is near-optimal, False otherwise.

Use the geometric evaluation above as hard facts - you do not need to re-verify which polygons were violated or whether endpoints match. For the alignment judgment, focus on the VISUAL pattern: shape of the detour, which side of polygons the path goes around, spacing of waypoints, distance from hazards. Cite concrete visual evidence (polygon names, direction of detour, which side of the flyzone, where the path turns). Do not speculate about data you cannot see in the image.

OUTPUT
Return the structured LLMReview object:
  - aligned: bool - True if the path clearly follows the preference (or is near-optimal when no preference is given), False otherwise.
  - evaluation: one- or two-sentence verdict on preference alignment (or optimality).
"""

def _format_geometric_summary(evaluation: Evaluation) -> str:
    orig_ok, dest_ok = evaluation.orig_dest_ok if len(evaluation.orig_dest_ok) == 2 else (None, None)
    lines = [
        f"- Valid overall: {evaluation.valid}",
        f"- Starts at origin: {orig_ok}",
        f"- Ends at destination: {dest_ok}",
        f"- Violated hazardous polygons: {evaluation.polys or 'none'}",
        f"- Waypoints outside the flyzone: {evaluation.out_pts or 'none'}",
    ]
    return "\n".join(lines)


def _format_preference(human_preference):
    text = human_preference.strip() if human_preference else ""
    placeholder = {"", "no preference", "no preference.", "do whatever looks reasonable", "do whatever looks reasonable."}
    if text.lower() in placeholder:
        return "(none - evaluate on optimality only)"
    return text


def llm_evaluation(evaluation: Evaluation, image_path, human_preference) -> LLMReview:
    base64_image = encode_image(image_path)
    logging.info(f"evaluating path planning for image {image_path}")

    prompt_text = COACH_PROMPT.format(
        human_preference=_format_preference(human_preference),
        geometric_summary=_format_geometric_summary(evaluation),
    )

    response = client.beta.chat.completions.parse(
        model="gpt-5",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt_text},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                    },
                ],
            }
        ],
        response_format=LLMReview,
    )
    return response.choices[0].message.parsed



# First three images are some examples.
#                         Here is the evaluation of the images:
                        
#                         example 1:
#                         valid: true
#                         evaluation: The path does not intersect with any polygon.
#                         reasoning: the path starts from origin and ends in the destination. it stays in the flyzone and avoids the yellow wind polygons. It is also very close to the optimal path.




#                         example 2:
#                         valid: false
#                         evaluation: INVALID
#                         reasoning: the path starts from the origin and ends in the destination but it intersects with one of the wind polygons. 


#                         example 3:
#                         valid: true
#                         evaluation: the path satisfies all of the mentioned criteria and is very close to the optimal path.
#                         reasoning: the path starts from the origin and ends in the destination. it is inside the fly zone (very close to the border) and also doesn’t intersect with the wind polygons.