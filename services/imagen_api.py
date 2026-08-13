import os
from io import BytesIO
from PIL import Image
from google import genai
from google.genai.types import GenerateContentConfig, Modality
from utils.gemini_retry import with_gemini_retry

def generate_clean_schematic(input_photo_pil):
    """
    Converts an uploaded product photograph into a clean 2D schematic.
    Strictly matches the input geometry and perspective using Multimodal input.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    
    schematic_prompt = """
    Analyze the uploaded photograph of the product. 
    Convert this product into a clean, highly detailed 2D black-and-white technical line drawing.
    It must strictly match the geometry, proportions, and perspective of the object in the photo. 

    CRITICAL INSTRUCTION 1 (MATERIALS): Preserve the detailed, dense structural appearance of woven materials (such as cane, rattan, wicker, or rope). Do not oversimplify these elements into sparse wireframes; maintain their natural fiber look.
    
    CRITICAL INSTRUCTION 2 (LEG TERMINATIONS): Every chair leg must terminate in a flat, clean cut flush with the floor. ABSOLUTELY NO floor glides, feet, caps, pads, hardware, or stubs at the bottom of the legs. Do not draw anything beneath the wood legs.

    Render against a pure white background. Remove superficial surface textures only (NO wood grain, NO fabric micro-textures, NO colors, NO shadows). 
    NO text, no dimensions, no annotations. ONLY the clean structural drawing.
    """

    # Pass the text and PIL Image directly in a list to bypass Part validation errors
    response = with_gemini_retry(
        lambda: client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=[schematic_prompt, input_photo_pil],
            config=GenerateContentConfig(
                response_modalities=[Modality.IMAGE],
            ),
        ),
        label="schematic",
    )
    
    for part in response.candidates[0].content.parts:
        if part.inline_data:
            image = Image.open(BytesIO(part.inline_data.data))
            return image
            
    raise ValueError("No image data returned from the API.")
