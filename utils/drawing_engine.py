from PIL import ImageDraw, ImageFont
import math

TICK_LEN = 8


def _short_ticks(draw, p1, p2, color, width):
    """Draw small end ticks on the dimension line, not connected to the chair."""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    length = math.hypot(dx, dy) or 1
    # Perpendicular to the dimension line
    tx, ty = (-dy / length) * TICK_LEN, (dx / length) * TICK_LEN
    for px, py in (p1, p2):
        draw.line(
            [(px - tx, py - ty), (px + tx, py + ty)],
            fill=color,
            width=width,
        )


def add_dimension_line(img, text, coord1, coord2, orientation="vertical", offset=50):
    output_img = img.copy().convert("RGB")
    draw = ImageDraw.Draw(output_img)
    
    line_color = (0, 0, 0)
    text_color = (0, 0, 0)
    bg_color = (255, 255, 255)
    line_width = 2
    
    try:
        font = ImageFont.truetype("arial.ttf", 28)
    except IOError:
        try:
            font = ImageFont.truetype("Helvetica", 28)
        except IOError:
            font = ImageFont.load_default()

    x1, y1 = coord1
    x2, y2 = coord2

    if orientation == "vertical":
        offset_x = min(x1, x2) - offset
        p1_line = (offset_x, y1)
        p2_line = (offset_x, y2)
        
    elif orientation == "horizontal":
        # Width: parallel to the front-foot axis, offset in front of the chair (+Y)
        dx = x2 - x1
        dy = y2 - y1
        length = math.hypot(dx, dy) or 1
        px, py = -dy / length, dx / length
        if py < 0:
            px, py = -px, -py
        p1_line = (x1 + px * offset, y1 + py * offset)
        p2_line = (x2 + px * offset, y2 + py * offset)
        
    elif orientation == "depth":
        # Depth: parallel to front-left → rear-left, offset left of the chair (-X)
        dx = x2 - x1
        dy = y2 - y1
        length = math.hypot(dx, dy) or 1
        px, py = -dy / length, dx / length
        if px > 0:
            px, py = -px, -py
        p1_line = (x1 + px * offset, y1 + py * offset)
        p2_line = (x2 + px * offset, y2 + py * offset)

    draw.line([p1_line, p2_line], fill=line_color, width=line_width)
    _short_ticks(draw, p1_line, p2_line, line_color, line_width)

    cx = (p1_line[0] + p2_line[0]) / 2
    cy = (p1_line[1] + p2_line[1]) / 2

    bbox = draw.textbbox((cx, cy), text, font=font, anchor="mm")
    padded_bbox = (bbox[0] - 6, bbox[1] - 4, bbox[2] + 6, bbox[3] + 4)
    draw.rectangle(padded_bbox, fill=bg_color)
    draw.text((cx, cy), text, fill=text_color, font=font, anchor="mm")
    
    return output_img
