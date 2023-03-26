import openai 
import yaml 
import openai 
from dotenv import load_dotenv
import os 

load_dotenv()

openai.api_key = os.getenv('OPENAI_API_KEY')

async def openaiGeneration(prompt: str, parse: bool = False):
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=1000,
        n=1,
        stop=None,
        temperature=0.5,
    )
    print(response.choices[0].text.strip())
    if parse: 
        return parse_yaml(response.choices[0].text.strip())
    else:
        return response.choices[0].text.strip()

def parse_yaml(yaml_str):
    """
    Parse a YAML string and return a dictionary object.
    """
    data = yaml.safe_load(yaml_str)
    return data