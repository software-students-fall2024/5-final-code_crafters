"""
This is a model to generate plan for users.
"""

import os
import json
import google.generativeai as genai
from google.ai.generativelanguage_v1beta.types import content
from dotenv import load_dotenv


load_dotenv()
api_key = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=api_key)

with open('prompt.json', 'r', encoding='utf-8') as file:
    prompt = json.load(file)["prompt"]

mock_user_info = {
    "workout":["pulls up","Weightlifting","Plyometrics","Swimming","Yoga"],
    "user_id": "001",
    "sex": "male",
    "height": 160,
    "weight": 50,
    "goal_weight":40,
    "fat_rate": None,
    "goal_fat_rate": None, 
    "additional_note": "I don't like doing yoga"
}


def input_generate(prompt_data, user_info):
    """
    It's a function to combine user info and prompt.
    """

    user_info_str = str(user_info)
    input_data = prompt_data + user_info_str
    return input_data


def make_plan_request(input_data):
    """
    It's a function to call the API of a LLM to generate plan.
    """

    generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
    "response_schema": content.Schema(
        type = content.Type.OBJECT,
        enum = [],
        required = [
            "Monday", 
            "Tuesday", 
            "Wednesday", 
            "Thursday", 
            "Friday", 
            "Saturday", 
            "Sunday", 
            "Explaining"
        ],
        properties = {
        "Monday": content.Schema(
            type = content.Type.ARRAY,
            items = content.Schema(
            type = content.Type.STRING,
            ),
        ),
        "Tuesday": content.Schema(
            type = content.Type.ARRAY,
            items = content.Schema(
            type = content.Type.STRING,
            ),
        ),
        "Wednesday": content.Schema(
            type = content.Type.ARRAY,
            items = content.Schema(
            type = content.Type.STRING,
            ),
        ),
        "Thursday": content.Schema(
            type = content.Type.ARRAY,
            items = content.Schema(
            type = content.Type.STRING,
            ),
        ),
        "Friday": content.Schema(
            type = content.Type.ARRAY,
            items = content.Schema(
            type = content.Type.STRING,
            ),
        ),
        "Saturday": content.Schema(
            type = content.Type.ARRAY,
            items = content.Schema(
            type = content.Type.STRING,
            ),
        ),
        "Sunday": content.Schema(
            type = content.Type.ARRAY,
            items = content.Schema(
            type = content.Type.STRING,
            ),
        ),
        "Explaining": content.Schema(
            type = content.Type.STRING,
        ),
        },
    ),
    "response_mime_type": "application/json",
    }

    model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
    )

    chat_session = model.start_chat(
    history=[]
    )

    response = chat_session.send_message(input_data)
    return response


def plan_generation(user_info):
    """
    It's a tool function to combine making plan and getting user info.
    """

    try:
        input_data = input_generate(prompt, user_info)
        response = make_plan_request(input_data)
        return response.text
    except TimeoutError as e:
        print(f"Timeout error: {e}")
        return "The request timed out while generating the plan"
    except  FileNotFoundError as e:
        print(f"An error occurred: {e}")
        return "Error generating plan"


# if __name__ == '__main__':
    # response = plan_generation(mock_user_info)
    # print(response)
    # print("\nFinish")
