import math
from PIL import ImageDraw, ImageFont

def add_deterministic_dimension(img, text, coord1, coord2, offset=50):
    """
    Draws CAD-style dimension lines with offset leaders and masked text.
    """
    output_img = img.copy().convert("RGB")
    draw = ImageDraw.Draw(output_img)
    
    line_color = (0, 0, 0)
    text_color = (0, 0, 0)
    bg_color = (255, 255, 255)
    line_width = 2
    
    # Load font with fallback size scaling
    try:
        font = ImageFont.truetype("arial.ttf", 36)
    except IOError:
        try:
            font = ImageFont.truetype("Helvetica", 36)
        except IOError:
            font = ImageFont.load_default()

    x1, y1 = coord1
    x2, y2 = coord2

    # Determine primary direction (Vertical vs Horizontal)
    is_vertical = abs(y2 - y1) > abs(x2 - x1)

    if is_vertical:
        # Shift line to the left of the leftmost click
        offset_x = min(x1, x2) - offset
        p1_line = (offset_x, y1)
        p2_line = (offset_x, y2)
        
        # Leader lines connecting clicks to dimension line
        draw.line([(x1, y1), (offset_x - 10, y1)], fill=line_color, width=line_width)
        draw.line([(x2, y2), (offset_x - 10, y2)], fill=line_color, width=line_width)
    else:
        # Shift line above the topmost click
        offset_y = min(y1, y2) - offset
        p1_line = (x1, offset_y)
        p2_line = (x2, offset_y)
        
        # Leader lines
        draw.line([(x1, y1), (x1, offset_y - 10)], fill=line_color, width=line_width)
        draw.line([(x2, y2), (x2, offset_y - 10)], fill=line_color, width=line_width)

    # Draw main dimension line
    draw.line([p1_line, p2_line], fill=line_color, width=line_width)

    # Midpoint for label placement
    cx = (p1_line[0] + p2_line[0]) / 2
    cy = (p1_line[1] + p2_line[1]) / 2

    # Calculate text bounding box to render background mask
    bbox = draw.textbbox((cx, cy), text, font=font, anchor="mm")
    padded_bbox = (bbox[0] - 6, bbox[1] - 4, bbox[2] + 6, bbox[3] + 4)

    # Draw white background rectangle to break the line behind text
    draw.rectangle(padded_bbox, fill=bg_color)

    # Render text
    draw.text((cx, cy), text, fill=text_color, font=font, anchor="mm")

    return output_img
