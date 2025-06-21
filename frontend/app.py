"""
Main application file for the First Trimester Screening Tool.
"""


import os
from datetime import datetime
import json
import base64
from io import BytesIO
import time

import requests
import streamlit as st
import streamlit.components.v1 as components
from streamlit_local_storage import LocalStorage
import pandas as pd
from PIL import Image
import numpy as np
from dotenv import load_dotenv
from pydantic import BaseModel


load_dotenv()

BOUNDING_BOX_REGRESSION_SERVICE_HOST = os.getenv("BOUNDING_BOX_REGRESSION_HOST")
if not BOUNDING_BOX_REGRESSION_SERVICE_HOST:
    raise ValueError("BOUNDING_BOX_REGRESSION_HOST environment variable is not set.")
SEGMENTATION_SERVICE_HOST = os.getenv("SEGMENTATION_HOST")
if not SEGMENTATION_SERVICE_HOST:
    raise ValueError("SEGMENTATION_HOST environment variable is not set.")


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
    """
    Request model for bounding box predictions.
    """
    data: BWImage


class BBPrediction(BaseModel):
    """
    Prediction model for bounding boxes.
    """
    class_name: str
    x_min: float
    y_min: float
    width: float
    height: float


class BBPredictionResponse(BaseModel):
    """
    Response model for bounding box predictions.
    """
    predictions: list[BBPrediction]


class BoundingBox(BaseModel):
    """
    Represents a bounding box with label, coordinates, dimensions, color, and timestamp.
    """
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
        """
        Validates the label against the predefined classes.
        """
        if label not in CLASSES:
            raise ValueError(f"Invalid label: {label}. Must be one of {CLASSES}.")
        return label


class SegPredictionRequest(BaseModel):
    data: BWImage


class SegPrediction(BaseModel):
    seg_mask: BWImage
    tn_endpoints: tuple[tuple[float, float], tuple[float, float]] | None = None


class SegPredictionResponse(BaseModel):
    prediction: SegPrediction


class TNEndpoint(BaseModel):
    x: float
    y: float


class TNMeasurement(BaseModel):
    endpoints: list[TNEndpoint]


def local_storage_manager():
    """
    Returns a LocalStorage instance for managing local storage in Streamlit.
    """
    return LocalStorage()


def sync_data() -> None:
    """
    Syncs the bounding boxes with local storage.
    """
    localS = local_storage_manager()
    for _ in range(100):
        localS.refreshItems()
    data = localS.getItem("streamlit_annotations")
    if data is None:
        synced_boxes = []
        synced_tn_endpoints = []
    else:
        synced_boxes = data.get("rectangles", [])
        synced_tn_endpoints = data.get("tn_endpoints", [])
    st.session_state.bounding_boxes = [BoundingBox(**bb) for bb in synced_boxes]
    st.session_state.bounding_boxes_present_classes = set(
        bb.label for bb in st.session_state.bounding_boxes
    )
    st.session_state.tn_endpoints = [TNEndpoint(**ep) for ep in synced_tn_endpoints]


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
            raise RuntimeError(f"Error from bounding box regression service: {response.text}")
        response_data = BBPredictionResponse.model_validate(response.json())
        bounding_boxes = []
        for prediction in response_data.predictions:
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


def get_segmentation_mask(image: np.ndarray) -> tuple[np.ndarray, tuple[tuple[float, float], tuple[float, float]] | None] | None:
    """
    Placeholder function for segmentation mask retrieval.
    This should be replaced with actual segmentation logic.
    """
    try:
        list_of_vals = [row.tolist() for row in image]
        prediction_request = SegPredictionRequest(data=list_of_vals)
        response = requests.post(
            f"http://{SEGMENTATION_SERVICE_HOST}/predict",
            json=prediction_request.model_dump(),
            timeout=30
        )
        if response.status_code != 200:
            raise RuntimeError(f"Error from bounding box regression service: {response.text}")
        response_data = SegPredictionResponse.model_validate(response.json())
        seg_mask = np.array(response_data.prediction.seg_mask)
        endpoints = response_data.prediction.tn_endpoints
        return seg_mask, endpoints
    except Exception as e:
        st.error(f"Failed to get automatic detection: {str(e)}")
        return None


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
if 'bounding_boxes_present_classes' not in st.session_state:
    st.session_state.bounding_boxes_present_classes = set()
if 'notes' not in st.session_state:
    st.session_state.notes = ""
if 'uploaded_file' not in st.session_state:
    st.session_state.uploaded_file = None
if 'seg_mask' not in st.session_state:
    st.session_state.seg_mask = None
if 'tn_endpoints' not in st.session_state:
    st.session_state.tn_endpoints = []

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

# Clear session state when a new file is uploaded
if uploaded_file is not None and uploaded_file != st.session_state.uploaded_file:
    st.session_state.bounding_boxes = []
    st.session_state.bounding_boxes_present_classes = set()
    st.session_state.notes = ""
    st.session_state.seg_mask = None
    st.session_state.tn_endpoints = []

if uploaded_file is not None:
    st.session_state.uploaded_file = uploaded_file
    image = Image.open(uploaded_file)
    image_array = np.array(image.convert('L'))
    col1, col2 = st.columns([2, 1])
    with col2:
        st.subheader("🔍 Automatic Detection")
        if st.button("Run Auto Detection", type="primary"):
            with st.spinner("Running automatic detection..."):
                auto_boxes = get_automatic_bounding_boxes(image_array)
                if auto_boxes:
                    for box in auto_boxes:
                        if box.label not in st.session_state.bounding_boxes_present_classes:
                            st.session_state.bounding_boxes_present_classes.add(box.label)
                            st.session_state.bounding_boxes.append(box)
                    st.rerun()
                else:
                    st.warning("No structures detected")
        st.subheader("Nuchal Translucency Measurement")
        seg_col_1, seg_col_2 = st.columns([1, 1])
        with seg_col_1:
            if st.button("Run Auto Segmentation", type="primary"):
                with st.spinner("Running automatic segmentation..."):
                    seg_results = get_segmentation_mask(image_array)
                    if seg_results is None:
                        st.error("Segmentation failed. Please check the service status.")
                    else:
                        seg_mask, endpoints = seg_results
                        st.session_state.seg_mask = np.array(seg_mask, dtype=np.uint8)
                        st.session_state.tn_endpoints = [TNEndpoint(x=ep[0], y=ep[1]) for ep in endpoints] if endpoints else []
                        if endpoints is None:
                            st.warning("No valid measurement for TN was found.")
                            time.sleep(2)
                        st.rerun()
        with seg_col_2:
            if st.session_state.seg_mask is not None:
                if st.button("Delete Segmentation Mask", type="primary"):
                    st.session_state.seg_mask = None
                    st.session_state.tn_endpoints = None
                    st.rerun()
        if st.session_state.tn_endpoints:
            tn_col_1, tn_col_2 = st.columns([1, 1])
            with tn_col_1:
                # Let the clinnician set the pixel size in mm
                pixel_mm = st.number_input(
                    "Pixel size in mm",
                    min_value=0.01,
                    value=0.18,  # Default value
                    step=0.01,
                    help="Enter the pixel size in millimeters for accurate TN measurement."
                )
            with tn_col_2:
                endpoints = st.session_state.tn_endpoints
                x1, y1 = endpoints[0].x, endpoints[0].y
                x2, y2 = endpoints[1].x, endpoints[1].y
                tn_meas = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2) * pixel_mm
                st.success(f"Nuchal Translucency Measurement: {tn_meas:.2f} mm")
    with col1:
        initial_bounding_boxes = json.dumps([bb.model_dump() for bb in st.session_state.bounding_boxes])
        
        # Handle TN endpoints
        if 'tn_endpoints' not in st.session_state:
            st.session_state.tn_endpoints = []
        
        initial_endpoints = json.dumps([endpoint.model_dump() for endpoint in st.session_state.tn_endpoints])
        
        # Interactive Rectangle Drawing
        st.subheader("🖱️ Interactive Annotation Tool")
        st.info("Switch between drawing bounding boxes and measuring TN endpoints")
        
        # Convert image to base64 for embedding
        buffered_image = BytesIO()
        image.save(buffered_image, format="PNG")
        img_str = base64.b64encode(buffered_image.getvalue()).decode()
        IMG_DATA_URL = f"data:image/png;base64,{img_str}"
        
        # Convert mask to base64 if available
        MASK_DATA_URL = "null"
        if st.session_state.seg_mask is not None:
            buffered_mask = BytesIO()
            # Convert binary mask (0,1) to proper image format (0,255)
            mask_normalized = (st.session_state.seg_mask * 255).astype(np.uint8)
            mask_image = Image.fromarray(mask_normalized, mode='L')  # Grayscale mode
            mask_image.save(buffered_mask, format="PNG")
            mask_str = base64.b64encode(buffered_mask.getvalue()).decode()
            MASK_DATA_URL = f"'data:image/png;base64,{mask_str}'"
        
        # Create HTML with embedded JavaScript
        canvas_html = f"""
        <div id="interactive-canvas"></div>
        <script>
            window.imageUrl = '{IMG_DATA_URL}';
            window.maskUrl = {MASK_DATA_URL};
            window.initialRectangles = {initial_bounding_boxes};
            window.initialEndpoints = {initial_endpoints};
            {open('./interactive_canvas.js', "r", encoding="UTF-8").read()}
        </script>
        """
        
        # Display interactive canvas
        canvas_result = components.html(canvas_html, height=image.height+150)

    # Display current annotations if any exist
    if st.button("🔄 Load Annotations"):
        components.html(
            """
            <script>
                const localS = window.localStorage;
                const data = localS.getItem("streamlit_annotations");
                if (data) {
                    console.log("Loaded annotations from localStorage:", JSON.parse(data));
                } else {
                    console.log("No annotations found in localStorage.");
                }
            </script>
            """,
            height=0
        )
        sync_data()
    
    if st.session_state.bounding_boxes:
        st.subheader("📋 Saved Annotations")
        df = pd.DataFrame([bb.model_dump() for bb in st.session_state.bounding_boxes])
        st.dataframe(df, use_container_width=True)
    
    if st.session_state.tn_endpoints:
        st.subheader("📏 TN Measurement")
        if len(st.session_state.tn_endpoints) == 2:
            endpoint1 = st.session_state.tn_endpoints[0]
            endpoint2 = st.session_state.tn_endpoints[1]
            
            # Calculate distance
            distance = np.sqrt((endpoint2.x - endpoint1.x)**2 + (endpoint2.y - endpoint1.y)**2)
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("TN Distance (pixels)", f"{distance:.2f}")
            with col2:
                st.metric("Endpoints", f"({endpoint1.x:.0f}, {endpoint1.y:.0f}) → ({endpoint2.x:.0f}, {endpoint2.y:.0f})")
        else:
            st.info("Place two endpoints to measure TN distance")
