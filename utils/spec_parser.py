import os
import json
from google import genai
from google.genai import types

def parse_spec_text(raw_text: str) -> dict:
    """
    Parses raw PDP dimension text into a structured JSON schema 
    for upholstered armchairs with backs.
    """
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    
    prompt = f"""
    You are a technical data parser for furniture specifications. 
    Extract the dimensions from the following raw text and map them strictly into this JSON format:
    {{
      "overall": {{"h": "...", "w": "...", "d": "..."}},
      "seat": {{"h": "...", "w": "...", "d": "..."}},
      "back": {{"h": "...", "w": "...", "d": "..."}}
    }}
    If a specific dimension is missing from the text, set its value to null. Do not include extra keys.
    
    Raw Text:
    {raw_text}
    """
    
    response = client.models.generate_content(
        model="gemini-flash-latest",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        ),
    )
    
    return json.loads(response.text)
