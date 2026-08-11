import gradio as gr
from dotenv import load_dotenv
from services.imagen_api import generate_clean_schematic
from utils.drawing_engine import add_dimension_line

# Initialize environment variables
load_dotenv()

def generate_base(input_image):
    # Ensure an image was actually uploaded
    if input_image is None:
        return None, []
    # Pass the uploaded PIL image to the API service
    schematic_img = generate_clean_schematic(input_image)
    # Return the generated template and clear old clicks
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

# Build the Web UI
with gr.Blocks() as demo:
    gr.Markdown("# StyleBoard Automated Audits: Project 1 (Deterministic Labeling)")
    
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 1. Upload Product Photo")
            photo_in = gr.Image(type="pil", label="Upload Product Photo (JPG/PNG)")
            generate_btn = gr.Button("Generate Schematic Template", variant="primary")
            
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
        inputs=[photo_in],
        outputs=[output_img, click_state]
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
