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

LANG_PACK_PATH = os.getenv("LANG_PACK_PATH")
if not LANG_PACK_PATH:
    raise ValueError("LANG_PACK_PATH environment variable is not set.")

# Load language pack first
with open(LANG_PACK_PATH, "r", encoding="UTF-8") as f:
    LANG_PACK = json.load(f)
if not LANG_PACK:
    raise ValueError(f"Language pack file {LANG_PACK_PATH} is empty or not found.")

BOUNDING_BOX_REGRESSION_SERVICE_HOST = os.getenv("BOUNDING_BOX_REGRESSION_HOST")
if not BOUNDING_BOX_REGRESSION_SERVICE_HOST:
    raise ValueError(LANG_PACK["error_messages"]["bb_service_unavailable"])
SEGMENTATION_SERVICE_HOST = os.getenv("SEGMENTATION_HOST")
if not SEGMENTATION_SERVICE_HOST:
    raise ValueError(LANG_PACK["error_messages"]["seg_service_unavailable"])


# Internal classes (always in English for consistency)
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

# Create mapping from English to localized class names
CLASS_TRANSLATIONS = dict(zip(CLASSES, LANG_PACK["class_names"]))
REVERSE_CLASS_TRANSLATIONS = dict(zip(LANG_PACK["class_names"], CLASSES))

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
            raise ValueError(LANG_PACK["error_messages"]["invalid_label"].format(
                label=label, classes=CLASSES
            ))
        return label

    def get_localized_label(self):
        """Returns the localized version of the label"""
        return CLASS_TRANSLATIONS.get(self.label, self.label)

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
            raise RuntimeError(LANG_PACK["error_messages"]["bb_service_error"].format(
                error=response.text
            ))
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
        st.error(LANG_PACK["error_messages"]["auto_detection_failed"].format(error=str(e)))
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
            raise RuntimeError(LANG_PACK["error_messages"]["bb_service_error"].format(
                error=response.text
            ))
        response_data = SegPredictionResponse.model_validate(response.json())
        seg_mask = np.array(response_data.prediction.seg_mask)
        endpoints = response_data.prediction.tn_endpoints
        return seg_mask, endpoints
    except Exception as e:
        st.error(LANG_PACK["error_messages"]["segmentation_failed"].format(error=str(e)))
        return None
    
def draw_canvas(image_height: int,
                IMG_DATA_URL: str,
                MASK_DATA_URL: str = "null",
                initial_bounding_boxes=None,
                initial_endpoints=None
                ):
    canvas_html = f"""
        <div id="interactive-canvas"></div>
        <script>
            window.imageUrl = '{IMG_DATA_URL}';
            window.maskUrl = {MASK_DATA_URL};
            window.initialRectangles = {initial_bounding_boxes if len(initial_bounding_boxes) else 'null'};
            window.initialEndpoints = {initial_endpoints if len(initial_endpoints) else 'null'};
            window.clearLocalStorage = {str(st.session_state.clear_local_storage).lower()}; 
            {open('./interactive_canvas.js', "r", encoding="UTF-8").read()}
        </script>
        """
    components.html(canvas_html, height=image_height+300)
    st.session_state.clear_local_storage = False

# Page configuration
st.set_page_config(
    page_title=LANG_PACK["page_config"]["title"],
    page_icon=LANG_PACK["page_config"]["icon"],
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
if 'seg_mask' not in st.session_state:
    st.session_state.seg_mask = None
if 'tn_endpoints' not in st.session_state:
    st.session_state.tn_endpoints = []
if 'clear_local_storage' not in st.session_state:
    st.session_state.clear_local_storage = True

# Sidebar - Information Panel
with st.sidebar:
    st.header(LANG_PACK["sidebar"]["header"])

    # File metadata section
    with st.expander(LANG_PACK["sidebar"]["file_metadata"]["title"], expanded=True):
        if st.session_state.uploaded_file is not None:
            image = Image.open(st.session_state.uploaded_file)
            file_details = {
                LANG_PACK["sidebar"]["file_metadata"]["fields"]["filename"]: st.session_state.uploaded_file.name,
                LANG_PACK["sidebar"]["file_metadata"]["fields"]["file_size"]: f"{st.session_state.uploaded_file.size / 1024:.2f} {LANG_PACK['field_labels']['kb_suffix']}",
                LANG_PACK["sidebar"]["file_metadata"]["fields"]["file_type"]: st.session_state.uploaded_file.type,
                LANG_PACK["sidebar"]["file_metadata"]["fields"]["upload_time"]: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                LANG_PACK["sidebar"]["file_metadata"]["fields"]["dimensions"]: f"{image.width} x {image.height} {LANG_PACK['field_labels']['px_suffix']}"
            }
            for key, value in file_details.items():
                st.text(f"{key}{LANG_PACK['field_labels']['colon_separator']}{value}")
        else:
            st.info(LANG_PACK["sidebar"]["file_metadata"]["no_file_message"])

    # Notes section
    with st.expander(LANG_PACK["sidebar"]["clinical_notes"]["title"], expanded=True):
        st.session_state.notes = st.text_area(
            LANG_PACK["sidebar"]["clinical_notes"]["label"],
            value=st.session_state.notes,
            height=200,
            placeholder=LANG_PACK["sidebar"]["clinical_notes"]["placeholder"]
        )
        # Save notes button
        if st.button(LANG_PACK["sidebar"]["clinical_notes"]["save_button"]):
            st.success(LANG_PACK["sidebar"]["clinical_notes"]["save_success"])

# Main content area
st.header(LANG_PACK["main_content"]["header"])

# File upload
uploaded_file = st.file_uploader(
    label=LANG_PACK["main_content"]["file_upload"]["label"],
    type=['png', 'jpg', 'jpeg', 'tiff', 'bmp'],
    help=LANG_PACK["main_content"]["file_upload"]["help"]
)

# Clear session state when a new file is uploaded
if uploaded_file is not None and uploaded_file != st.session_state.uploaded_file:
    st.session_state.bounding_boxes = []
    st.session_state.notes = ""
    st.session_state.seg_mask = None
    st.session_state.tn_endpoints = []
    st.session_state.clear_local_storage = True

if uploaded_file is not None:
    st.session_state.uploaded_file = uploaded_file
    image = Image.open(uploaded_file)
    image_array = np.array(image.convert('L'))
    col1, col2 = st.columns([2, 1])
    
    with col2:
        st.subheader(LANG_PACK["main_content"]["automatic_detection"]["section_title"])
        if st.button(LANG_PACK["main_content"]["automatic_detection"]["run_button"]):
            with st.spinner(LANG_PACK["main_content"]["automatic_detection"]["loading_message"]):
                st.session_state.bounding_boxes = []
                auto_boxes = get_automatic_bounding_boxes(image_array)
                if auto_boxes:
                    for box in auto_boxes:
                        st.session_state.bounding_boxes.append(box)
                    st.rerun()
                else:
                    st.warning(LANG_PACK["main_content"]["automatic_detection"]["no_detection_warning"])
        
        st.subheader(LANG_PACK["main_content"]["segmentation"]["section_title"])
        if st.button(LANG_PACK["main_content"]["segmentation"]["run_button"]):
            with st.spinner(LANG_PACK["main_content"]["segmentation"]["loading_message"]):
                seg_results = get_segmentation_mask(image_array)
                if seg_results is None:
                    st.error(LANG_PACK["main_content"]["segmentation"]["error_message"])
                else:
                    seg_mask, endpoints = seg_results
                    st.session_state.seg_mask = np.array(seg_mask, dtype=np.uint8)
                    st.session_state.tn_endpoints = [TNEndpoint(x=ep[0], y=ep[1]) for ep in endpoints] if endpoints else []
                    if endpoints is None:
                        st.warning(LANG_PACK["main_content"]["segmentation"]["no_measurement_warning"])
                        time.sleep(2)
                    st.rerun()
        if st.session_state.seg_mask is not None:
            if st.button(LANG_PACK["main_content"]["segmentation"]["delete_button"], type="primary"):
                st.session_state.seg_mask = None
                st.session_state.tn_endpoints = []
                st.rerun()

    with col1:
        initial_bounding_boxes = json.dumps([bb.model_dump() for bb in st.session_state.bounding_boxes])
        
        # Handle TN endpoints
        if 'tn_endpoints' not in st.session_state:
            st.session_state.tn_endpoints = []
        
        initial_endpoints = json.dumps([endpoint.model_dump() for endpoint in st.session_state.tn_endpoints])
        
        # Interactive Rectangle Drawing
        st.subheader(LANG_PACK["main_content"]["interactive_canvas"]["section_title"])
        st.info(LANG_PACK["main_content"]["interactive_canvas"]["info_message"])
        
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
        
        draw_canvas(
            image_height=image.height,
            IMG_DATA_URL=IMG_DATA_URL,
            MASK_DATA_URL=MASK_DATA_URL,
            initial_bounding_boxes=initial_bounding_boxes,
            initial_endpoints=initial_endpoints
        )

        # Clear bounding boxes, segmentation mask, and TN endpoints. They will be cached in local storage.}
        st.session_state.bounding_boxes = []
        st.session_state.tn_endpoints = []
