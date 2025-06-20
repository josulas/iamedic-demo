import os
from datetime import datetime
import json
import requests
import streamlit as st
import streamlit.components.v1 as components
from streamlit_local_storage import LocalStorage
import pandas as pd
from PIL import Image
import numpy as np
from dotenv import load_dotenv
from pydantic import BaseModel


CLASSES = [
    "Cisternae Magna",
    "Intracranial Translucency",
    "Nuchal Translucency",
    "Midbrain",
    "Nasal Bone",
    "Nasal Skin",
    "Nasal Tip",
    "Palate",
    "Thalami"
]

CLASS_COLORS = {
    "Cisternae Magna": "#FF5733",
    "Intracranial Translucency": "#33FF57",
    "Nuchal Translucency": "#3357FF",
    "Midbrain": "#F1C40F",
    "Nasal Bone": "#8E44AD",
    "Nasal Skin": "#E67E22",
    "Nasal Tip": "#2ECC71",
    "Palate": "#3498DB",
    "Thalami": "#E74C3C"
}

BWImage = list[list[int]]

class BBPredictionRequest(BaseModel):
    data: BWImage

class BBPrediction(BaseModel):
    class_name: str
    x_min: float
    y_min: float
    width: float
    height: float

class BBPredictionResponse(BaseModel):
    predictions: list[BBPrediction]


class BoundingBox(BaseModel):
    label: str
    x: float
    y: float
    width: float
    height: float
    color: str = "#FF0000"  # Default color red
    timestamp: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def __init__(self, **data):
        super().__init__(**data)
        # Set color based on label if not provided
        if self.label in CLASS_COLORS:
            self.color = CLASS_COLORS[self.label]

    @classmethod
    def validate_label(cls, label: str):
        if label not in CLASSES:
            raise ValueError(f"Invalid label: {label}. Must be one of {CLASSES}.")
        return label

load_dotenv()

BOUNDING_BOX_REGRESSION_SERVICE_HOST = os.getenv("BOUNDING_BOX_REGRESSION_HOST")
if not BOUNDING_BOX_REGRESSION_SERVICE_HOST:
    raise ValueError("BOUNDING_BOX_REGRESSION_HOST environment variable is not set.")


def local_storage_manager():
    """
    Returns a LocalStorage instance for managing local storage in Streamlit.
    """
    return LocalStorage()


def get_automatic_bounding_boxes(image: np.ndarray) -> list[BoundingBox]:
    """
    Gets automatic bounding boxes from the ML service.
    """
    try:
        list_of_vals = [row.tolist() for row in image]
        prediction_request = BBPredictionRequest(data=list_of_vals)

        response = requests.post(
            f"http://{BOUNDING_BOX_REGRESSION_SERVICE_HOST}/predict",
            json=prediction_request.model_dump(),
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"Error from bounding box regression service: {response.text}")
            
        response_data = BBPredictionResponse.model_validate(response.json())
        bounding_boxes = []
        
        for prediction in response_data.predictions:
            # Create BoundingBox with proper color assignment
            box = BoundingBox(
                label=prediction.class_name,
                x=prediction.x_min,
                y=prediction.y_min,
                width=prediction.width,
                height=prediction.height,
                color=CLASS_COLORS.get(prediction.class_name, "#FF0000"),
                timestamp=datetime.now().isoformat()
            )
            bounding_boxes.append(box)
        
        return bounding_boxes
        
    except Exception as e:
        st.error(f"Failed to get automatic detection: {str(e)}")
        return []

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
st.header("Fetal US Image Annotation Tool")

# File upload
uploaded_file = st.file_uploader(
    "Upload ultrasound image",
    type=['png', 'jpg', 'jpeg', 'tiff', 'bmp'],
    help="Supported formats: PNG, JPG, JPEG, TIFF, BMP"
)

if uploaded_file is not None:

    st.session_state.uploaded_file = uploaded_file
    image = Image.open(uploaded_file)
    image_array = np.array(image.convert('L'))

    st.subheader("🤖 Automatic Detection")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔍 Run Auto Detection", type="primary"):
            with st.spinner("Running automatic detection..."):
                auto_boxes = get_automatic_bounding_boxes(image_array)
                if auto_boxes:
                    # Extend the existing bounding boxes with auto-detected ones
                    st.session_state.bounding_boxes.extend(auto_boxes)
                    st.success(f"Added {len(auto_boxes)} auto-detected structures!")
                    st.rerun()
                else:
                    st.warning("No structures detected")
        with col2:
            if st.session_state.bounding_boxes and st.button("🗑️ Clear All Annotations"):
                st.session_state.bounding_boxes = []
                st.success("All annotations cleared!")
                st.rerun()
    
    initial_bounding_boxes = json.dumps([bb.model_dump() for bb in st.session_state.bounding_boxes])

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
        localS = local_storage_manager()
        data = localS.getItem("streamlit_annotations")
        st.text("Loaded annotations from localStorage:")
        st.text(data)
    
    # Display current annotations if any exist
    if st.session_state.bounding_boxes:
        st.subheader("📋 Saved Annotations")
        df = pd.DataFrame(st.session_state.bounding_boxes)
        st.dataframe(df, use_container_width=True)
