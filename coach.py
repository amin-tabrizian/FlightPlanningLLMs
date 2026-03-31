import base64
from openai import OpenAI
import anthropic
import instructor
import shapely
from utils import convert_waypoints
import logging
from utils import Evaluation, haversine_distance
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
def llm_evaluation(evaluation: Evaluation, image_path):
    # Getting the Base64 string
    base64_image = encode_image(image_path)
    example1 = encode_image("coach_examples/example1.jpg")
    example2 = encode_image("coach_examples/example2.jpg")
    example3 = encode_image("coach_examples/example3.jpg")
    logging.info(f"evaluating path planning for image {image_path}")
    # client = instructor.from_anthropic(
    #     anthropic.Anthropic(),
    #     )
    # response = client.chat.completions.create(
    #     max_tokens=1024,
    #     model="claude-3-5-sonnet-20241022",
    #     messages=[
    #         { "role": "user",
    #         "content": [
    #             {
    #                 "type": "text",
    #                 "text": """Evaluate this path planning that is done by an llm.
    #                 The path should be evaluated by the following criterias:
    #                 1- It should start and end from origin and destination respectively.
    #                 2- It should not intersect yellow wind polygons.
    #                 3- It should stay in red flyzone.
    #                 Your output should be weather the path planning is valid or unvalid, 
    #                 how optimal it is if it was a valid path (evaluation in a few sentences) 
    #                 other wise just write INVALID and the reasoning.
    #                 For optimality, think about how indirect the path is. \
    #                 Is there a more direct path that could have been taken? \
    #                 The planned path is in black dashed line.""",
    #             },
    #             {
    #                 "type": "image",
    #                 "source": {
    #                     "type": "base64",
    #                     "media_type": "image/jpeg",
    #                     "data": base64_image,}
    #             },
    #         ],}],
    #     response_model=Evaluation
    # )
    
    response = client.beta.chat.completions.parse(
        model="gpt-4o-2024-11-20",
        
        temperature=0.0,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": """Evaluate this path planning that is done by an llm.
                        The path should be evaluated by the following criterias:
                        1- It should start and end from origin and destination respectively.
                        2- It should not intersect yellow wind polygons. 
                        (So, if a path intersects yellow wind polygon, it is invalid)
                        3- It should stay in green flyzone.
                        Your output should be like: 
                        1- Is the path valid? 
                        2- Which waypoints are voilating polygons? (list of 2 elements)
                        3- Does the path start with origin and end in the destination?
                        4- Which points are outside of the flyzone
                        5- How optimal the path is? If the path is invalid, mention the reason of invalidity (e.g., polygon names if they are being intersected or if the path exits the fly zone.).
                        For optimality, think about how indirect the path is.
                        Is there a more direct path that could have been taken while satisfying the conditions? 
                        The planned path is in black line. The voilating parts are in red. The intersection of the path with the yellow wind polygons is given to you.
                        """ + f'''Rule based evaluation: 
                        1- Is the path valid? {evaluation.valid}
                        2- List of polygons being violated: and the corrosponding waypoints: {evaluation.polys}
                        3- List of corrosponding waypoints intersecting the polygons: {evaluation.segs}
                        4- Does the path start with origin and end in the destination? {evaluation.orig_dest_ok}
                        5- List of the points out of flyzone? {evaluation.out_pts}''',
                    },
                    # {
                    #     "type": "image_url",
                    #     "image_url": {"url": f"data:image/jpeg;base64,{example1}"},
                    # },
                    # {
                    #     "type": "image_url",
                    #     "image_url": {"url": f"data:image/jpeg;base64,{example2}"},
                    # },
                    # {
                    #     "type": "image_url",
                    #     "image_url": {"url": f"data:image/jpeg;base64,{example3}"},
                    # },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                    },
                ],
                
            }
        
        ],
            response_format=Evaluation,
    )
    response = response.choices[0].message.parsed
    return response



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