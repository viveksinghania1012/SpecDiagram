import json
import os
from pathlib import Path

from google import genai
from google.genai import types
from PIL import Image


ANCHOR_PROMPT = """Analyze this chair schematic. Provide the pixel coordinates (x, y) for the following anchor points:

top_backrest: The highest point of the chair back.

top_seat_cushion: The highest surface point of the seat cushion deck.

rear_foot_base: The lowest contact point of the rear-left leg on the floor.

front_leg_base: The lowest contact point of the front-left leg.
Return ONLY a JSON object: {"top_backrest": [x, y], "top_seat_cushion": [x, y], "rear_foot_base": [x, y], "front_leg_base": [x, y]}"""


def _as_pil(image_path):
    """Accept a filesystem path or an already-loaded PIL Image."""
    if isinstance(image_path, Image.Image):
        return image_path.convert("RGB")
    return Image.open(Path(image_path)).convert("RGB")


def _normalize_point(value):
    if value is None:
        return None
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        try:
            return (float(value[0]), float(value[1]))
        except (TypeError, ValueError):
            return None
    return None


def get_anchor_points(image_path) -> dict:
    """
    Visually audit a chair schematic and return anatomical anchor points.

    Args:
        image_path: Path to an image file, or a PIL Image.

    Returns:
        {
          "top_backrest": (x, y) | None,
          "top_seat_cushion": (x, y) | None,
          "rear_foot_base": (x, y) | None,
          "front_leg_base": (x, y) | None,
        }
    """
    image = _as_pil(image_path)
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=[ANCHOR_PROMPT, image],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )

    data = json.loads(response.text)
    keys = (
        "top_backrest",
        "top_seat_cushion",
        "rear_foot_base",
        "front_leg_base",
    )
    return {key: _normalize_point(data.get(key)) for key in keys}
