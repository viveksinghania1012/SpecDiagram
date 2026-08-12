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

    # Seat W: cushion front-left → front-right (full front lip).
    if seat.get("w") and not _same_dim(seat.get("w"), overall.get("w")):
        cfl = anchors.get("cushion_front_left") or seat_left
        cfr = anchors.get("cushion_front_right") or seat_right
        if cfl and cfr and abs(cfr[0] - cfl[0]) > 12:
            layout.append({
                "type": "seat_w",
                "text": seat["w"],
                "p1": cfl,
                "p2": cfr,
                "orientation": "horizontal",
                "offset": 28,
            })

    # Seat D: cushion front-left → rear-left (left cushion edge only).
    if seat.get("d") and not _same_dim(seat.get("d"), overall.get("d")):
        cfl = anchors.get("cushion_front_left") or seat_front
        crl = anchors.get("cushion_rear_left") or seat_back or seat_top
        if cfl and crl and (abs(cfl[0] - crl[0]) > 8 or abs(cfl[1] - crl[1]) > 8):
            layout.append({
                "type": "seat_d",
                "text": seat["d"],
                "p1": cfl,
                "p2": crl,
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
