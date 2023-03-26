import openai 
import yaml 
import openai 
from dotenv import load_dotenv
import os 
import httpx


load_dotenv()

apikey = os.getenv('OPENAI_API_KEY')

async def openaiGeneration(prompt: str, parse: bool = False):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.openai.com/v1/engines/text-davinci-003/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {apikey}",
            },
            json={
                "prompt": prompt,
                "max_tokens": 1000,
                "n": 1,
                "stop": None,
                "temperature": 0.5,
            },
            timeout=20.0
        )
        response_data = response.json()
        text = response_data["choices"][0]["text"].strip()
        if parse:
            return parse_yaml(text)
        else:
            return text

async def openaiChatGeneration(system_prompt: str, user_prompt: str, parse: bool = False):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {apikey}",
            },
            json={
                "model":"gpt-4",
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
            },
            timeout=20.0
        )
        response_data = response.json()
        content = response_data["choices"][0]["message"]["content"].strip()
        print(content)
        if parse:
            return parse_yaml(content)
        else:
            return content


def parse_yaml(yaml_str):
    """
    Parse a YAML string and return a dictionary object.
    """
    data = yaml.safe_load(yaml_str)
    return data