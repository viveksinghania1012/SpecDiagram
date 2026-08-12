import math
import re


def _inches(value):
    """Parse a dimension string like 19'', 18.25\", 19 in → float inches."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"null", "none", "n/a"}:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)", text.replace(",", ""))
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _same_dim(a, b, tol=0.15):
    ia, ib = _inches(a), _inches(b)
    if ia is None or ib is None:
        return False
    return abs(ia - ib) <= tol


def calculate_layout(bbox, specs, anchors=None):
    """
    bbox: (min_x, min_y, max_x, max_y) of the chair (fallback / compat)
    specs: JSON output from spec_parser
    anchors: dict from edge_detector.detect_chair_anchors
    """
    anchors = anchors or {}
    layout = []

    min_x, min_y, max_x, max_y = bbox
    top_backrest = anchors.get("top_backrest")
    rear_foot_base = anchors.get("rear_foot_base")
    seat_top = anchors.get("seat_top")
    front_leg_base = anchors.get("front_leg_base")
    front_right_base = anchors.get("front_right_base")
    seat_left = anchors.get("seat_left")
    seat_right = anchors.get("seat_right")
    seat_front = anchors.get("seat_front")
    seat_back = anchors.get("seat_back")
    cushion_top = anchors.get("cushion_top") or seat_top
    cushion_bottom = anchors.get("cushion_bottom")

    overall = specs.get("overall") or {}
    seat = specs.get("seat") or {}
    cushion = specs.get("cushion") or {}

    # Overall Height: backrest crown → rear-foot floor
    if overall.get("h") and top_backrest and rear_foot_base:
        layout.append({
            "type": "overall_h",
            "text": overall["h"],
            "p1": (min_x, top_backrest[1]),
            "p2": (rear_foot_base[0], rear_foot_base[1]),
            "orientation": "vertical",
            "offset": 120,
        })

    # Overall Width: front-left foot → front-right foot
    if overall.get("w") and front_leg_base and front_right_base:
        if abs(front_right_base[0] - front_leg_base[0]) > 20:
            layout.append({
                "type": "overall_w",
                "text": overall["w"],
                "p1": front_leg_base,
                "p2": front_right_base,
                "orientation": "horizontal",
                "offset": 50,
            })

    # Overall Depth: front-left foot → rear-left foot
    if overall.get("d") and front_leg_base and rear_foot_base:
        layout.append({
            "type": "overall_d",
            "text": overall["d"],
            "p1": front_leg_base,
            "p2": rear_foot_base,
            "orientation": "depth",
            "offset": 50,
        })

    # Seat Height: closer to the chair than overall H (inner vertical)
    if seat.get("h") and seat_top and rear_foot_base:
        x_col_seat = rear_foot_base[0]
        layout.append({
            "type": "seat_h",
            "text": seat["h"],
            "p1": (x_col_seat, seat_top[1]),
            "p2": (x_col_seat, rear_foot_base[1]),
            "orientation": "vertical",
            "offset": 55,
        })

    # Seat Width: only when it differs from overall W (e.g. chairs with arms)
    if seat.get("w") and not _same_dim(seat.get("w"), overall.get("w")):
        if seat_left and seat_right and abs(seat_right[0] - seat_left[0]) > 20:
            layout.append({
                "type": "seat_w",
                "text": seat["w"],
                "p1": seat_left,
                "p2": seat_right,
                "orientation": "horizontal",
                "offset": 90,
            })

    # Seat Depth: parallel to overall D (same direction as left seat edge / floor depth)
    if seat.get("d") and not _same_dim(seat.get("d"), overall.get("d")):
        od = _inches(overall.get("d"))
        sd = _inches(seat.get("d"))
        if front_leg_base and rear_foot_base and seat_top and od and sd and od > 0:
            fx, fy = front_leg_base
            rx, ry = rear_foot_base
            dx, dy = rx - fx, ry - fy
            overall_len = math.hypot(dx, dy) or 1.0
            ux, uy = dx / overall_len, dy / overall_len
            seat_len = overall_len * (sd / od)

            # Anchor the back at rear-left seat top; step toward the front
            # along the overall-D axis so the line stays parallel to overall D.
            back_x = (seat_back or rear_foot_base)[0]
            back_y = seat_top[1]
            p2 = (back_x, back_y)
            p1 = (back_x - ux * seat_len, back_y - uy * seat_len)
            layout.append({
                "type": "seat_d",
                "text": seat["d"],
                "p1": p1,
                "p2": p2,
                "orientation": "depth",
                "offset": 35,
            })

    # Cushion thickness: only when that field exists
    thickness = cushion.get("thickness") or seat.get("thickness")
    if thickness and cushion_top and cushion_bottom:
        x_col = cushion_top[0]
        layout.append({
            "type": "cushion_thickness",
            "text": thickness,
            "p1": (x_col, cushion_top[1]),
            "p2": (x_col, cushion_bottom[1]),
            "orientation": "vertical",
            "offset": 20,
        })

    return layout
