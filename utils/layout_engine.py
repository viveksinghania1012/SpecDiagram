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


def _vertical_span_px(item):
    p1, p2 = item.get("p1"), item.get("p2")
    if not p1 or not p2:
        return 0.0
    return abs(float(p2[1]) - float(p1[1]))


def flag_height_errors(layout, dim_type, threshold=0.25, min_overall_px=40, min_dim_px=20):
    """
    Scale from overall H pixels/inches; flag a vertical dim when given is ≥threshold off.
    Leaves the dim in place; drawing uses flagged to color the number red.
    """
    overall_h = next((i for i in layout if i.get("type") == "overall_h"), None)
    target = next((i for i in layout if i.get("type") == dim_type), None)
    if not overall_h or not target:
        return layout

    overall_in = _inches(overall_h.get("text"))
    given_in = _inches(target.get("text"))
    overall_px = _vertical_span_px(overall_h)
    dim_px = _vertical_span_px(target)
    if (
        overall_in is None
        or overall_in <= 0
        or given_in is None
        or given_in <= 0
        or overall_px < min_overall_px
        or dim_px < min_dim_px
    ):
        return layout

    measured_in = dim_px * (overall_in / overall_px)
    rel_err = abs(measured_in - given_in) / given_in
    if rel_err >= threshold:
        target["flagged"] = True
        print(
            f"audit {dim_type}: given {given_in}\" measured ~{measured_in:.1f}\" "
            f"({rel_err:.0%} off) → flagged"
        )
    else:
        print(
            f"audit {dim_type}: given {given_in}\" measured ~{measured_in:.1f}\" "
            f"({rel_err:.0%} off) → ok"
        )
    return layout


def flag_seat_height_errors(layout, threshold=0.25, min_overall_px=40, min_seat_px=20):
    return flag_height_errors(
        layout, "seat_h", threshold=threshold,
        min_overall_px=min_overall_px, min_dim_px=min_seat_px,
    )


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
    arm = specs.get("arm") or specs.get("arms") or {}
    cushion = specs.get("cushion") or {}
    arm_top = anchors.get("arm_top")

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

    # Arm Height: floor → left armrest top (between seat H and overall H).
    if not arm.get("h"):
        print("arm_h skipped: no arm.h in parsed specs")
    elif not arm_top:
        print("arm_h skipped: no arm_top anchor (vision miss or Gemini down)")
    elif arm.get("h") and arm_top and rear_foot_base:
        if seat_top and arm_top[1] >= seat_top[1]:
            print("arm_h skipped: arm top at or below seat top")
        else:
            x_col_arm = rear_foot_base[0]
            layout.append({
                "type": "arm_h",
                "text": arm["h"],
                "p1": (x_col_arm, arm_top[1]),
                "p2": (x_col_arm, rear_foot_base[1]),
                "orientation": "vertical",
                "offset": 88,
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

    flag_height_errors(layout, "seat_h")
    flag_height_errors(layout, "arm_h")
    return layout
