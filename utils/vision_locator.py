import json
import os
from pathlib import Path

import numpy as np
from google import genai
from google.genai import types
from PIL import Image
from utils.gemini_retry import with_gemini_retry


CORNER_PROMPT = """You are labeling a black-and-white chair schematic for CAD dimensioning.

The chair is almost always a right-front 3/4 view:
- Front feet are lower on the image (larger y) than rear feet.
- Image origin is top-left; x right, y down.

Return ONLY JSON. Every point uses normalized coordinates on a 0-1000 scale
(0 = left/top edge of the image, 1000 = right/bottom edge).

Keys (all required; use null only if truly invisible):
{
  "top_backrest": [x, y],
  "seat_top": [x, y],
  "arm_top_left": [x, y],
  "cushion_front_left": [x, y],
  "cushion_front_right": [x, y],
  "cushion_rear_left": [x, y],
  "front_leg_base": [x, y],
  "front_right_base": [x, y],
  "rear_foot_base": [x, y]
}

Definitions (critical):
- top_backrest: highest point of the backrest crown.
- seat_top: TOP sitting surface of the seat/cushion on the LEFT side
  (where a seat-height tick would land). NEVER the bottom of the backrest,
  NEVER the apron/rail under the cushion, NEVER the seat deck under a cushion.
- arm_top_left: TOP of the LEFT armrest (elbow rest) on the left side.
  Floor-to-here is arm height. Use the left arm, not the foreshortened right.
  On a wrap-around barrel, use the top of the arm rail where the elbow sits,
  NOT the backrest crown and NOT the seat. Null if the chair is armless.
- cushion_front_left / cushion_front_right: front corners of the seat TOP face
  (the edge a seat-width line should follow).
- cushion_rear_left: rear-left corner of the seat TOP at the seat/back junction.
- front_leg_base / front_right_base / rear_foot_base: foot centers on the floor.
"""


def _as_pil(image_path):
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


def _norm1000_to_px(pt, width, height):
    if pt is None:
        return None
    x, y = pt
    # Prompt asks for 0-1000; if anything exceeds 1000, treat as pixels.
    if x > 1000 or y > 1000:
        return (x, y)
    return (x / 1000.0 * (width - 1), y / 1000.0 * (height - 1))


def snap_to_ink(gray_arr, point, radius=18):
    """Move a rough point to the nearest dark ink pixel within radius."""
    if point is None:
        return None
    h, w = gray_arr.shape
    x0, y0 = int(round(point[0])), int(round(point[1]))
    if not (0 <= x0 < w and 0 <= y0 < h):
        x0 = min(max(x0, 0), w - 1)
        y0 = min(max(y0, 0), h - 1)

    if gray_arr[y0, x0] < 200:
        return (x0, y0)

    y_lo = max(0, y0 - radius)
    y_hi = min(h, y0 + radius + 1)
    x_lo = max(0, x0 - radius)
    x_hi = min(w, x0 + radius + 1)
    patch = gray_arr[y_lo:y_hi, x_lo:x_hi]
    ink = np.where(patch < 200)
    if len(ink[0]) == 0:
        return (x0, y0)

    ys = ink[0] + y_lo
    xs = ink[1] + x_lo
    dist2 = (xs - x0) ** 2 + (ys - y0) ** 2
    i = int(np.argmin(dist2))
    return (int(xs[i]), int(ys[i]))


def get_schematic_corners(image_path) -> dict:
    """
    Ask Gemini for chair corner points, convert to pixels, snap to ink.

    Returns pixel (x, y) ints for known keys; missing keys omitted.
    """
    image = _as_pil(image_path)
    width, height = image.size
    gray = np.array(image.convert("L"))

    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    response = with_gemini_retry(
        lambda: client.models.generate_content(
            model="gemini-flash-latest",
            contents=[CORNER_PROMPT, image],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        ),
        label="vision_corners",
    )

    data = json.loads(response.text)
    keys = (
        "top_backrest",
        "seat_top",
        "arm_top_left",
        "cushion_front_left",
        "cushion_front_right",
        "cushion_rear_left",
        "front_leg_base",
        "front_right_base",
        "rear_foot_base",
    )

    out = {}
    for key in keys:
        pt = _normalize_point(data.get(key))
        px = _norm1000_to_px(pt, width, height)
        snapped = snap_to_ink(gray, px, radius=max(12, int(min(width, height) * 0.02)))
        if snapped is not None:
            out[key] = snapped
    return out


def merge_vision_anchors(pixel_anchors: dict, vision_points: dict) -> dict:
    """Override pixel anchors with snapped vision corners when present."""
    merged = dict(pixel_anchors or {})
    if not vision_points:
        return merged

    if vision_points.get("top_backrest"):
        merged["top_backrest"] = vision_points["top_backrest"]
    if vision_points.get("rear_foot_base"):
        merged["rear_foot_base"] = vision_points["rear_foot_base"]
    if vision_points.get("front_leg_base"):
        merged["front_leg_base"] = vision_points["front_leg_base"]
        merged["floor_base"] = vision_points["front_leg_base"]
    if vision_points.get("front_right_base"):
        merged["front_right_base"] = vision_points["front_right_base"]

    if vision_points.get("seat_top"):
        st = vision_points["seat_top"]
        # Keep seat-H column on rear-left foot x when available.
        rx = (merged.get("rear_foot_base") or st)[0]
        merged["seat_top"] = (rx, st[1])

    if vision_points.get("arm_top_left"):
        at = vision_points["arm_top_left"]
        rx = (merged.get("rear_foot_base") or at)[0]
        merged["arm_top"] = (rx, at[1])

    cfl = vision_points.get("cushion_front_left")
    cfr = vision_points.get("cushion_front_right")
    crl = vision_points.get("cushion_rear_left")
    if cfl:
        merged["cushion_front_left"] = cfl
        merged["seat_left"] = cfl
        merged["seat_front"] = cfl
    if cfr:
        merged["cushion_front_right"] = cfr
        merged["seat_right"] = cfr
    if crl:
        merged["cushion_rear_left"] = crl
        merged["seat_back"] = crl

    return merged
