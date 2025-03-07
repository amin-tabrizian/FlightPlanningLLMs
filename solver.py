from openai import OpenAI
import anthropic
import logging
import instructor
import json

from utils import FlightPlan
def response_generator(output, model, memory):
    system_msg = output[0]
    user_msg = output[1]

    if memory == True:
        with open('memory.json', 'r') as json_file:
            data = json.load(json_file)
        memory_prompt = "Here are some examples of previous \
                        Flight planning with evaluations: \n" + json.dumps(data)
    else:
        memory_prompt = ""
        logging.info("Memory is deactivated.")
    if model == "gpt-4o" or model == "o3-mini-2025-01-31":
        client = OpenAI()
        logging.info("Requesting flight plan from OpenAI API.")
        messages = [
                {"role": "system", "content": system_msg + memory_prompt},
                {"role": "user", "content":  user_msg},
            ],
        completion = client.beta.chat.completions.parse(
            model=model,
            messages=messages,
            response_format=FlightPlan,
        )
        response = completion.choices[0].message.parsed

    elif model == "claude-3-5-sonnet-20241022":
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
    

    with open("Output.txt", "w") as text_file:
        text_file.write(str(messages))


    return response