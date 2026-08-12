import numpy as np
from PIL import Image


def _cluster_columns(cols, gap=2):
    """Group nearby column indices into (start, end) inclusive clusters."""
    if not cols:
        return []
    cols = sorted(cols)
    clusters = []
    start = prev = cols[0]
    for x in cols[1:]:
        if x <= prev + gap:
            prev = x
        else:
            clusters.append((start, prev))
            start = prev = x
    clusters.append((start, prev))
    return clusters


def _cluster_foot(start, end, col_bottoms):
    xs = [x for x in range(start, end + 1) if x in col_bottoms]
    ys = [col_bottoms[x] for x in xs]
    return {
        "x": int((start + end) // 2),
        "y": int(max(ys)),
        "start": start,
        "end": end,
    }


def _cluster_runs(indices, gap=2):
    """Group nearby 1D indices into (start, end) inclusive runs."""
    if len(indices) == 0:
        return []
    indices = sorted(int(i) for i in indices)
    runs = []
    start = prev = indices[0]
    for i in indices[1:]:
        if i <= prev + gap:
            prev = i
        else:
            runs.append((start, prev))
            start = prev = i
    runs.append((start, prev))
    return runs


def detect_chair_anchors(image_path):
    """
    Directly analyzes the line drawing asset array to extract
    precise coordinate anchors.

    Image Y increases downward. For a forward-right 3/4 chair:
    front feet are closer → larger Y; rear feet are farther → smaller Y.
    """
    img = Image.open(image_path)
    if img.mode != "L":
        img = img.convert("L")
    arr = np.array(img)

    ink_pixels = arr < 200
    y_indices, x_indices = np.where(ink_pixels)

    if len(x_indices) == 0 or len(y_indices) == 0:
        raise ValueError("No chair drawing detected on canvas.")

    min_x, max_x = int(x_indices.min()), int(x_indices.max())
    min_y, max_y = int(y_indices.min()), int(y_indices.max())
    height = max_y - min_y
    width = max_x - min_x

    col_bottoms = {}
    for x in range(min_x, max_x + 1):
        ys = np.where(arr[:, x] < 200)[0]
        if len(ys):
            col_bottoms[x] = int(ys[-1])

    floor_tol = max(2, int(height * 0.01))
    abs_floor = max(col_bottoms.values()) if col_bottoms else max_y

    # Front-left: strict lowest contact (largest Y), leftmost cluster.
    front_cols = [x for x, y in col_bottoms.items() if y >= abs_floor - floor_tol]
    front_clusters = [
        _cluster_foot(s, e, col_bottoms) for s, e in _cluster_columns(front_cols, gap=3)
    ]
    if front_clusters:
        front_left = min(front_clusters, key=lambda c: c["x"])
        best_x, best_span = front_left["x"], 0
        for x in range(front_left["start"], front_left["end"] + 1):
            ys = np.where(arr[:, x] < 200)[0]
            if len(ys):
                span = int(ys[-1] - ys[0])
                if span > best_span:
                    best_span = span
                    best_x = x
        front_left["x"] = best_x
    else:
        front_left = {"x": min_x + max(1, int(width * 0.18)), "y": abs_floor, "start": min_x, "end": min_x}

    front_leg_x = front_left["x"]
    front_leg_y = front_left["y"]

    # Front-right: lowest contact well to the right of the front-left foot.
    # In 3/4 view that foot is farther from camera, so it is often much higher
    # on the page than abs_floor and must not use the same Y threshold.
    min_sep = max(24, int(width * 0.22))
    foot_band_y = min_y + int(height * 0.62)
    right_cols = [
        x
        for x, y in col_bottoms.items()
        if x >= front_leg_x + min_sep and y >= foot_band_y
    ]
    right_clusters = [
        _cluster_foot(s, e, col_bottoms) for s, e in _cluster_columns(right_cols, gap=3)
    ]
    if right_clusters:
        # Lowest on-canvas (largest Y) among right-side foot clusters = front-right.
        front_right = max(right_clusters, key=lambda c: (c["y"], c["x"]))
        best_x, best_span = front_right["x"], 0
        for x in range(front_right["start"], front_right["end"] + 1):
            ys = np.where(arr[:, x] < 200)[0]
            if len(ys):
                span = int(ys[-1] - ys[0])
                if span > best_span:
                    best_span = span
                    best_x = x
        front_right["x"] = best_x
    else:
        right_x = max((x for x in col_bottoms if x >= front_leg_x + min_sep), default=max_x)
        front_right = {"x": right_x, "y": col_bottoms.get(right_x, abs_floor)}

    front_right_x = front_right["x"]
    front_right_y = front_right["y"]

    # Rear feet: still in the lower leg band, but clearly above the front floor
    # (smaller Y = farther from camera in this view).
    rear_elevate_min = max(floor_tol + 2, int(height * 0.03))
    rear_elevate_max = max(rear_elevate_min + 4, int(height * 0.18))
    # Rear-left sits on the left half, usually slightly inward of the front-left foot.
    left_limit = min(front_leg_x + int(width * 0.28), min_x + int(width * 0.40))
    rear_cols = [
        x
        for x, y in col_bottoms.items()
        if abs_floor - rear_elevate_max <= y <= abs_floor - rear_elevate_min
        and x <= left_limit
    ]
    rear_clusters = [
        _cluster_foot(s, e, col_bottoms) for s, e in _cluster_columns(rear_cols, gap=3)
    ]
    if rear_clusters:
        # Leftmost elevated foot in that band = rear-left.
        rear_left = min(rear_clusters, key=lambda c: c["x"])
    else:
        rear_left = {"x": min_x, "y": abs_floor - rear_elevate_min}

    rear_foot_x = rear_left["x"]
    rear_foot_y = rear_left["y"]

    # Seat deck: find the tall cushion slab in the front bay, then snap the
    # left-stack tick to the uppermost ink near that top in the rear-left plane
    # (narrow band — do not score "tallest" there or the leg/apron wins).
    bay_left = min(front_leg_x, front_right_x)
    bay_right = max(front_leg_x, front_right_x)
    inset = max(2, int((bay_right - bay_left) * 0.12))
    x0 = bay_left + inset
    x1 = bay_right - inset
    if x1 <= x0:
        x0, x1 = bay_left, bay_right

    y_lo = min_y + int(height * 0.40)
    y_hi = min_y + int(height * 0.68)
    bay_w = max(1, x1 - x0 + 1)
    bay = arr[y_lo : y_hi + 1, x0 : x1 + 1]
    row_densities = np.sum(bay < 200, axis=1)
    density_thresh = max(2, int(bay_w * 0.10))

    dense_local = np.where(row_densities >= density_thresh)[0]
    dense_rows = [int(y_lo + i) for i in dense_local]
    runs = _cluster_runs(dense_rows, gap=1)

    if runs:
        scored = []
        for r0, r1 in runs:
            thick = r1 - r0 + 1
            ink = int(np.sum(arr[r0 : r1 + 1, x0 : x1 + 1] < 200))
            scored.append((thick, ink, r0, r1))
        scored.sort(key=lambda t: (t[0], t[1]), reverse=True)
        _thick, _ink, cushion_top_front, cushion_bot = scored[0]
    else:
        cushion_top_front = min_y + int(height * 0.50)
        cushion_bot = cushion_top_front + max(8, int(height * 0.06))

    # Narrow band around the known cushion top. Rear plane can sit a bit higher
    # on the page (smaller Y) than the front-bay top.
    lift = max(6, int(height * 0.06))
    drop = max(3, int(height * 0.02))
    band_lo = max(y_lo, cushion_top_front - lift)
    band_hi = min(y_hi, cushion_top_front + drop)

    rx0 = max(min_x, rear_foot_x)
    rx1 = min(max_x, max(bay_left + inset, rear_foot_x + max(8, int(width * 0.10))))
    if rx1 <= rx0:
        rx1 = min(max_x, rx0 + max(6, int(width * 0.05)))

    seat_corner_y = cushion_top_front
    if rx1 > rx0 and band_hi >= band_lo:
        ink_rows = [
            y
            for y in range(band_lo, band_hi + 1)
            if np.any(arr[y, rx0 : rx1 + 1] < 200)
        ]
        if ink_rows:
            # Uppermost ink in the top-edge band = visual cushion top on the left.
            seat_corner_y = min(ink_rows)

    # Seat pan endpoints for Seat W / Seat D.
    # Seat W: across the seat at seat height (front bay).
    # Seat D: along the side depth axis (must have dy like overall D, or the
    # line collapses to horizontal and looks like width).
    seat_left = (x0, seat_corner_y)
    seat_right = (x1, seat_corner_y)
    # Front of seat = front-left of cushion (lower on page); back = rear-left
    # seat/back junction (higher on page / smaller Y).
    seat_front = (front_leg_x, int(cushion_top_front))
    seat_back = (rear_foot_x, seat_corner_y)
    cushion_top = (rear_foot_x, seat_corner_y)
    cushion_bottom = (rear_foot_x, int(cushion_bot))

    return {
        "top_backrest": (min_x, min_y),
        "rear_foot_base": (rear_foot_x, rear_foot_y),
        "seat_top": (rear_foot_x, seat_corner_y),
        "seat_left": seat_left,
        "seat_right": seat_right,
        "seat_front": seat_front,
        "seat_back": seat_back,
        "cushion_top": cushion_top,
        "cushion_bottom": cushion_bottom,
        "front_leg_base": (front_leg_x, front_leg_y),
        "front_right_base": (front_right_x, front_right_y),
        "floor_base": (front_leg_x, front_leg_y),
        "bbox": (min_x, min_y, max_x, max_y),
    }
