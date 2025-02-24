import base64
from openai import OpenAI
from utils import Evaluation
client = OpenAI()

# Function to encode the image
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


# Path to your image
image_path = "2D_Plot.jpg"


# Getting the Base64 string
base64_image = encode_image(image_path)

response = client.beta.chat.completions.parse(
    model="o1-2024-12-17",
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
                    3- It should stay in red flyzone.
                    Your output should be weather the path planning is valid or unvalid and the reasoning.\
                    The planned path is in black dashed line.""",
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
print(response)