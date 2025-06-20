from datetime import datetime
import json
import streamlit as st
import streamlit.components.v1 as components
from streamlit_local_storage import LocalStorage
import pandas as pd
from PIL import Image
import numpy as np


def localStorageManager():
    """
    Returns a LocalStorage instance for managing local storage in Streamlit.
    """
    return LocalStorage()


CLASSES = [
    "Nuchal Translucency",
    "Nasal Bone",
    "Nasal Tip",
    "Midbrain",
    "Intracranial Translucency",
    "Palate",
    "Thalami",
    "Cisterna Magna",
    "Other (specify)"
]

def get_automatic_bounding_boxes(image_width: int, image_height: int):
    """
    Returns a list of automatic bounding boxes for demonstration purposes.
    """
    n_boxes = np.random.randint(1, 4) # 1 to 3 boxes
    boxes = []
    for _ in range(n_boxes):
        top_left_corner_x = np.random.randint(0, image_width - 100)
        top_left_corner_y = np.random.randint(0, image_height - 100)
        width = np.random.randint(50, 150)
        height = np.random.randint(50, 150)
        label = np.random.choice(CLASSES)
        boxes.append({
            "x": top_left_corner_x,
            "y": top_left_corner_y,
            "width": width,
            "height": height,
            "label": label
        })
    return boxes


# Page configuration
st.set_page_config(
    page_title="First Trimester Screening Tool",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'bounding_boxes' not in st.session_state:
    st.session_state.bounding_boxes = []
if 'notes' not in st.session_state:
    st.session_state.notes = ""
if 'uploaded_file' not in st.session_state:
    st.session_state.uploaded_file = None
if 'selected_box' not in st.session_state:
    st.session_state.selected_box = None
if 'current_selector' not in st.session_state:
    st.session_state.current_selector = None
if 'temp_rect' not in st.session_state:
    st.session_state.temp_rect = None

# Sidebar - Information Panel
with st.sidebar:
    st.header("📋 Information Panel")

    # File metadata section
    with st.expander("📁 File Metadata", expanded=True):
        if st.session_state.uploaded_file is not None:
            image = Image.open(st.session_state.uploaded_file)
            file_details = {
                "Filename": st.session_state.uploaded_file.name,
                "File size": f"{st.session_state.uploaded_file.size / 1024:.2f} KB",
                "File type": st.session_state.uploaded_file.type,
                "Upload time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Dimensions": f"{image.width} x {image.height} px"
            }
            for key, value in file_details.items():
                st.text(f"{key}: {value}")
        else:
            st.info("No file uploaded yet")

    # Notes section
    with st.expander("📝 Clinical Notes", expanded=True):
        st.session_state.notes = st.text_area(
            "Add your clinical observations:",
            value=st.session_state.notes,
            height=200,
            placeholder="Enter clinical notes, measurements, observations, etc."
        )
        # Save notes button
        if st.button("💾 Save Notes"):
            st.success("Notes saved!")

# Main content area
st.header("📸 Image Analysis")

# File upload
uploaded_file = st.file_uploader(
    "Upload ultrasound image",
    type=['png', 'jpg', 'jpeg', 'tiff', 'bmp'],
    help="Supported formats: PNG, JPG, JPEG, TIFF, BMP"
)

if uploaded_file is not None:

    st.session_state.uploaded_file = uploaded_file
    image = Image.open(uploaded_file)

    initial_bounding_boxes = json.dumps(get_automatic_bounding_boxes(image.width, image.height))

    # Annotation tools
    st.subheader("🎯 Annotation Tools")

    # Interactive Rectangle Drawing
    st.subheader("🖱️ Interactive Rectangle Drawing")
    st.info("Click and drag on the image to draw bounding boxes")

    # Convert image to base64 for embedding
    import base64
    from io import BytesIO

    buffered = BytesIO()
    image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    img_data_url = f"data:image/png;base64,{img_str}"

    # Create HTML with embedded JavaScript
    # Replace lines 140-160 with:
    # Create HTML with embedded JavaScript
    canvas_html = f"""
    <div id="interactive-canvas"></div>
    <script>
        window.imageUrl = '{img_data_url}';
        window.initialRectangles = {initial_bounding_boxes};
        {open('./interactive_canvas.js', "r").read()}
    </script>
    """

    # Display interactive canvas and capture returned data
    canvas_result = components.html(canvas_html, height=700)
    
    if st.button("🔄 Load Annotations"):
        # Use JavaScript to read from localStorage and parse the data
        localS = localStorageManager()
        data = localS.getItem("streamlit_annotations")
        st.text("Loaded annotations from localStorage:")
        st.text(data)
    
    # Display current annotations if any exist
    if st.session_state.bounding_boxes:
        st.subheader("📋 Saved Annotations")
        df = pd.DataFrame(st.session_state.bounding_boxes)
        st.dataframe(df, use_container_width=True)
