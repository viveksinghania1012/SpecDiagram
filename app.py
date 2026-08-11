import gradio as gr
from dotenv import load_dotenv
from services.imagen_api import generate_clean_schematic
from utils.drawing_engine import add_deterministic_dimension

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
    # (Keep record_click function the same)
    clicks.append(evt.index)
    return clicks

def apply_label(img, text, clicks):
    # (Keep apply_label function the same)
    if img is None or len(clicks) < 2:
        return img, clicks
    coord1 = clicks[-2]
    coord2 = clicks[-1]
    labeled_img = add_deterministic_dimension(img, text, coord1, coord2)
    return labeled_img, clicks

# Build the Web UI
with gr.Blocks() as demo:
    gr.Markdown("# StyleBoard Automated Audits: Project 1 (Deterministic Labeling)")
    
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 1. Upload Product Photo")
            # REPLACE TEXTBOX WITH IMAGE UPLOAD
            photo_in = gr.Image(type="pil", label="Upload Product Photo (JPG/PNG)")
            generate_btn = gr.Button("Generate Schematic Template", variant="primary")
            
            gr.Markdown("### 2. Apply Dimensional Data")
            gr.Markdown("*Click twice directly on the schematic to set points.*")
            dim_text = gr.Textbox(label="Dimension Text (e.g., 39'' H)")
            apply_btn = gr.Button("Apply Dimension Label")
            
        with gr.Column(scale=2):
            output_img = gr.Image(type="pil", label="Schematic Interactive Canvas")
            
    # (Keep click_state and event wiring same, update inputs/outputs)
    click_state = gr.State([])
    
    generate_btn.click(
        fn=generate_base, 
        inputs=[photo_in], # Input is now the photo, not text
        outputs=[output_img, click_state]
    )
    
    output_img.select(
        fn=record_click,
        inputs=[output_img, click_state],
        outputs=[click_state]
    )
    
    apply_btn.click(
        fn=apply_label,
        inputs=[output_img, dim_text, click_state],
        outputs=[output_img, click_state]
    )

if __name__ == "__main__":
    print("Initializing local Multimodal server...")
    # Move the theme parameter to the launch method here
    demo.launch(theme=gr.themes.Soft())
