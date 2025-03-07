import base64
from openai import OpenAI
import anthropic
import instructor

import logging
from utils import Evaluation
client = OpenAI()
# client = anthropic.Anthropic()

# Function to encode the image
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")
def evaluate_path_planning(image_path):
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
                        3- It should stay in red flyzone.
                        Your output should be weather the path planning is valid or unvalid, 
                        how optimal it is if it was a valid path (evaluation in a few sentences) 
                        other wise just write INVALID and the reasoning.
                        For optimality, think about how indirect the path is. 
                        Is there a more direct path that could have been taken? 
                        The planned path is in black line. You may
                        first run an edge detetection algorithm to filter the image
                        and then evaluate the path. first three images are some examples.
                        Here is the evaluation of the images:
                        
                        example 1:
                        valid: true
                        evaluation: the path satisfies all of the mentioned conditions. it is also very close to the straight line between origin and destination.
                        reasoning: the path starts from origin and ends in the destination. it stays in the flyzone and avoids the yellow wind polygons.




                        example 2:
                        valid: false
                        evaluation: INVALID
                        reasoning: the path starts from the origin and ends in the destination but it intersects with one of the wind polygons. 


                        example 3:
                        valid: true
                        evaluation: the path satisfies all of the mentioned criteria and is very close to the optimal path.
                        reasoning: the path starts from the origin and ends in the destination. it is inside the fly zone (very close to the border) and also doesn’t intersect with the wind polygons.""",
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{example1}"},
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{example2}"},
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{example3}"},
                    },
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



