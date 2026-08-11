from PIL import ImageDraw, ImageFont
import math

def add_dimension_line(img, text, coord1, coord2, orientation="vertical", offset=50):
    output_img = img.copy().convert("RGB")
    draw = ImageDraw.Draw(output_img)
    
    line_color = (0, 0, 0)
    text_color = (0, 0, 0)
    bg_color = (255, 255, 255)
    line_width = 2
    
    try:
        font = ImageFont.truetype("arial.ttf", 36)
    except IOError:
        try:
            font = ImageFont.truetype("Helvetica", 36)
        except IOError:
            font = ImageFont.load_default()

    x1, y1 = coord1
    x2, y2 = coord2

    if orientation == "vertical":
        offset_x = min(x1, x2) - offset
        p1_line = (offset_x, y1)
        p2_line = (offset_x, y2)
        draw.line([(x1, y1), (offset_x - 10, y1)], fill=line_color, width=line_width)
        draw.line([(x2, y2), (offset_x - 10, y2)], fill=line_color, width=line_width)
        draw.line([p1_line, p2_line], fill=line_color, width=line_width)
        
    elif orientation == "horizontal":
        # Calculate angle of the object base vector and offset perpendicularly
        dx = x2 - x1
        dy = y2 - y1
        length = math.hypot(dx, dy)
        if length == 0:
            length = 1
        ux, uy = dx / length, dy / length
        # Perpendicular vector pointing outward/downward
        px, py = -uy, ux
        
        p1_line = (x1 + px * offset, y1 + py * offset)
        p2_line = (x2 + px * offset, y2 + py * offset)
        
        draw.line([(x1, y1), p1_line], fill=line_color, width=line_width)
        draw.line([(x2, y2), p2_line], fill=line_color, width=line_width)
        draw.line([p1_line, p2_line], fill=line_color, width=line_width)
        
    elif orientation == "depth":
        # Push completely outside the bounding box along the isometric depth axis
        offset_x = -offset * 1.2
        offset_y = offset * 1.2
        p1_line = (x1 + offset_x, y1 + offset_y)
        p2_line = (x2 + offset_x, y2 + offset_y)
        
        draw.line([(x1, y1), p1_line], fill=line_color, width=line_width)
        draw.line([(x2, y2), p2_line], fill=line_color, width=line_width)
        draw.line([p1_line, p2_line], fill=line_color, width=line_width)

    cx = (p1_line[0] + p2_line[0]) / 2
    cy = (p1_line[1] + p2_line[1]) / 2

    bbox = draw.textbbox((cx, cy), text, font=font, anchor="mm")
    padded_bbox = (bbox[0] - 6, bbox[1] - 4, bbox[2] + 6, bbox[3] + 4)
    draw.rectangle(padded_bbox, fill=bg_color)
    draw.text((cx, cy), text, fill=text_color, font=font, anchor="mm")
    
    return output_img
