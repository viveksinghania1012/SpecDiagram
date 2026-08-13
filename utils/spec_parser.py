import os
import json
from google import genai
from google.genai import types
from utils.gemini_retry import with_gemini_retry

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
      "arm": {{"h": "..."}},
      "back": {{"h": "...", "w": "...", "d": "..."}}
    }}
    arm.h is floor-to-top-of-armrest. Map any of these to arm.h:
    "Arm Height 26\"", "Armrest Height 26\"", "Arms 26'' H", "Arms 26\"".
    If the chair is armless or that dim is missing, set arm.h to null.
    If a specific dimension is missing from the text, set its value to null. Do not include extra keys.
    
    Raw Text:
    {raw_text}
    """
    
    response = with_gemini_retry(
        lambda: client.models.generate_content(
            model="gemini-flash-latest",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            ),
        ),
        label="spec_parser",
    )
    
    return json.loads(response.text)
