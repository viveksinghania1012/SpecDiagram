import os
import tempfile

from PIL import Image
import gradio as gr
from dotenv import load_dotenv
from services.imagen_api import generate_clean_schematic
from utils.drawing_engine import add_dimension_line
from utils.edge_detector import detect_chair_anchors
from utils.layout_engine import calculate_layout
from utils.spec_parser import parse_spec_text
from utils.vision_locator import get_schematic_corners, merge_vision_anchors

# Initialize environment variables
load_dotenv()

# Room for dimension lines outside the chair (W sits below the front feet).
PAD_LEFT, PAD_TOP, PAD_RIGHT, PAD_BOTTOM = 156, 24, 48, 96


def _pad_schematic(img, anchors):
    """Expand the canvas and shift anchors so offset dimension lines stay visible."""
    rgb = img.convert("RGB")
    w, h = rgb.size
    canvas = Image.new(
        "RGB",
        (w + PAD_LEFT + PAD_RIGHT, h + PAD_TOP + PAD_BOTTOM),
        (255, 255, 255),
    )
    canvas.paste(rgb, (PAD_LEFT, PAD_TOP))
    shifted = {}
    for key, value in anchors.items():
        if key == "bbox" and value is not None:
            min_x, min_y, max_x, max_y = value
            shifted[key] = (
                min_x + PAD_LEFT,
                min_y + PAD_TOP,
                max_x + PAD_LEFT,
                max_y + PAD_TOP,
            )
        elif isinstance(value, tuple) and len(value) == 2:
            shifted[key] = (value[0] + PAD_LEFT, value[1] + PAD_TOP)
        else:
            shifted[key] = value
    return canvas, shifted


def generate_base(input_image, specs=None, raw_specs_text=None):
    # Ensure an image was actually uploaded
    if input_image is None:
        return None, []
    # Pass the uploaded PIL image to the API service
    schematic_img = generate_clean_schematic(input_image)

    # Re-parse raw PDP text when present so newly added lines (e.g. Arms 26" H)
    # are not ignored because an older parsed JSON is still in the UI.
    if raw_specs_text and str(raw_specs_text).strip():
        specs = parse_spec_text(raw_specs_text)

    if not specs:
        return schematic_img, []

    # Persist line drawing so edge detection can scan the file asset
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name
            schematic_img.save(tmp_path)

        anchors = detect_chair_anchors(tmp_path)
        bbox = anchors.get("bbox")
        if not bbox:
            return schematic_img, []

        try:
            vision_pts = get_schematic_corners(tmp_path)
            anchors = merge_vision_anchors(anchors, vision_pts)
            print(f"vision corners: {vision_pts}")
        except Exception as vis_exc:
            print(f"vision corners failed (using pixel anchors): {vis_exc}")

        schematic_img, anchors = _pad_schematic(schematic_img, anchors)
        bbox = anchors.get("bbox")

        layout = calculate_layout(bbox, specs, anchors=anchors)
        for item in layout:
            text = item.get("text")
            p1 = item.get("p1")
            p2 = item.get("p2")
            if text is None or p1 is None or p2 is None:
                continue
            schematic_img = add_dimension_line(
                schematic_img,
                str(text),
                p1,
                p2,
                orientation=item.get("orientation", "vertical"),
                offset=item.get("offset", 50),
                flagged=bool(item.get("flagged")),
            )
    except Exception as exc:
        print(f"edge_detector/layout failed: {exc}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

    # Return the labeled template and clear old clicks
    return schematic_img, []


def record_click(img, evt: gr.SelectData, clicks):
    clicks.append(evt.index)
    return clicks

def apply_h(img, text, clicks):
    if img is None or len(clicks) < 2:
        return img, clicks
    coord1, coord2 = clicks[-2], clicks[-1]
    return add_dimension_line(img, text, coord1, coord2, orientation="vertical"), clicks

def apply_w(img, text, clicks):
    if img is None or len(clicks) < 2:
        return img, clicks
    coord1, coord2 = clicks[-2], clicks[-1]
    return add_dimension_line(img, text, coord1, coord2, orientation="horizontal"), clicks

def apply_d(img, text, clicks):
    if img is None or len(clicks) < 2:
        return img, clicks
    coord1, coord2 = clicks[-2], clicks[-1]
    return add_dimension_line(img, text, coord1, coord2, orientation="depth"), clicks

def parse_specs(raw_text):
    if not raw_text or not str(raw_text).strip():
        return None
    return parse_spec_text(raw_text)

# Build the Web UI
with gr.Blocks() as demo:
    gr.Markdown("# StyleBoard Automated Audits: Project 1 (Deterministic Labeling)")
    
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 1. Upload Product Photo")
            photo_in = gr.Image(type="pil", label="Upload Product Photo (JPG/PNG)")
            generate_btn = gr.Button("Generate Schematic Template", variant="primary")

            gr.Markdown("### 1b. Parse PDP Dimension Specs")
            pdp_specs = gr.Textbox(
                label="PDP Dimension Specs",
                lines=6,
                placeholder="Paste raw product dimension text here...",
            )
            parse_btn = gr.Button("Parse Specs")
            parsed_json = gr.JSON(label="Parsed Spec Schema")
            
            gr.Markdown("### 2. Apply Dimensions")
            gr.Markdown("*For each step: click two points on the schematic, then Apply.*")
            with gr.Group():
                h_text = gr.Textbox(label="Height (e.g. 39' H)")
                btn_h = gr.Button("Apply Height")
            with gr.Group():
                w_text = gr.Textbox(label="Width (e.g. 22' W)")
                btn_w = gr.Button("Apply Width")
            with gr.Group():
                d_text = gr.Textbox(label="Depth (e.g. 25' D)")
                btn_d = gr.Button("Apply Depth")
            
        with gr.Column(scale=2):
            output_img = gr.Image(type="pil", label="Schematic Interactive Canvas")
            
    click_state = gr.State([])
    
    generate_btn.click(
        fn=generate_base, 
        inputs=[photo_in, parsed_json, pdp_specs],
        outputs=[output_img, click_state]
    )

    parse_btn.click(
        fn=parse_specs,
        inputs=[pdp_specs],
        outputs=[parsed_json],
    )
    
    output_img.select(
        fn=record_click,
        inputs=[output_img, click_state],
        outputs=[click_state]
    )
    
    btn_h.click(
        fn=apply_h,
        inputs=[output_img, h_text, click_state],
        outputs=[output_img, click_state]
    )
    btn_w.click(
        fn=apply_w,
        inputs=[output_img, w_text, click_state],
        outputs=[output_img, click_state]
    )
    btn_d.click(
        fn=apply_d,
        inputs=[output_img, d_text, click_state],
        outputs=[output_img, click_state]
    )

if __name__ == "__main__":
    print("Initializing local Multimodal server...")
    demo.launch(theme=gr.themes.Soft())
