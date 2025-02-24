from openai import OpenAI
import anthropic
import logging
import instructor

from utils import FlightPlan
def response_generator(output, model):
    if model == "gpt-4o" or model == "o3-mini-2025-01-31":
        client = OpenAI()
        logging.info("Requesting flight plan from OpenAI API.")
        completion = client.beta.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful flight planner."},
                {"role": "user", "content": output},
            ],
            response_format=FlightPlan,
        )
        response = completion.choices[0].message.parsed

    elif model == "claude-3-5-sonnet-20241022":
        client = instructor.from_anthropic(
        anthropic.Anthropic(),
        )
        logging.info("Requesting flight plan from Anthropic API.")
        response = client.chat.completions.create(
            max_tokens=1024,
            model=model,
            messages=[
                {"role": "user", "content": output + 
                 """Your output should be in the structure of a list of waypoints, 
                    where each waypoint is a list of three elements: latitude, longitude, and altitude. 
                    For example:
                        [Waypoint(latitude=32.55, longitude=-96.3, altitude=150.0), 
                        Waypoint(latitude=32.55, longitude=-97.6, altitude=150.0), 
                        Waypoint(latitude=33.0, longitude=-97.6, altitude=150.0), 
                        Waypoint(latitude=33.2, longitude=-98.0, altitude=200.0), 
                        Waypoint(latitude=33.0, longitude=-98, altitude=274)].
                        NOTE: THE OUT PUT SHOULD BE IN THE ABOVE FORMAT AND NOTHING ELSE SHOULD BE PRINTED."""}],
            response_model=FlightPlan
        )


    return response