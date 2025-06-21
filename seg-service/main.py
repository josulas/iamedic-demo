import numpy as np
import onnxruntime as ort
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from PIL import Image as PILImage
import cv2

MODEL_PATH = "unet_fetus_segmentation.onnx"

TARGET_HEIGHT = 400
TARGET_WIDTH = 600
THRESHOLD = 0.5
CLASS_NAMES = {
    0: "Cisternae Magna",
    1: "Intracranial Translucency",
    2: "Nuchal Translucency",
    3: "Midbrain",
    4: "Nasal Bone",
    5: "Nasal Skin",
    6: "Nasal Tip",
    7: "Palate",
    8: "Thalami"
}

app = FastAPI(title="Segmentation Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BWImage = list[list[int]]

class PredictionRequest(BaseModel):
    data: BWImage

class Ellipse(BaseModel):
    center_x: float
    center_y: float
    major_axis: float
    minor_axis: float
    angle: float

class Prediction(BaseModel):
    seg_mask: BWImage
    tn_endpoints: tuple[tuple[float, float], tuple[float, float]] | None = None

class PredictionResponse(BaseModel):
    prediction: Prediction

class ModelService:
    def __init__(self):
        self.model = None
        self.load_model()
    
    def load_model(self):
        try: 
            # Load ONNX model (assuming you saved it as ONNX in MLflow)
            onnx_path = MODEL_PATH
            self.model = ort.InferenceSession(onnx_path)
            print(f"Model loaded successfully")            
        except Exception as e:
            print(f"Error loading model: {e}")
            raise
    
    def predict(self, data: np.ndarray) -> np.ndarray:
        """Make predictions using the loaded model"""
        if self.model is None:
            raise RuntimeError("Model not loaded")
        inputs = {self.model.get_inputs()[0].name: data}
        results = self.model.run(None, inputs)
        return results[0]


def fit_ellipse(bin_mask: np.ndarray):
    """
    Fits an ellipse to the largest contour in a binary image.

    :param thresh: Binary image (numpy array) where the ellipse will be fitted.
    :return: An Ellipse object representing the fitted ellipse.
    """
    contours, _ = cv2.findContours(bin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cnt = max(contours, key=cv2.contourArea)
    ellipse = cv2.fitEllipse(cnt)
    (center, axes, angle) = ellipse
    (eje_mayor, eje_menor) = axes
    return Ellipse(
        center_x=center[0],
        center_y=center[1],
        major_axis=eje_mayor,
        minor_axis=eje_menor,
        angle=angle
    )


# Initialize model service
model_service = ModelService()

@app.get("/")
def read_root():
    return {"message": "Segmentation Service is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    try:
        image = np.array(request.data, dtype=np.uint8)
        original_height, original_width = image.shape
        pil_image = PILImage.fromarray(image)
        pil_image = pil_image.resize((TARGET_WIDTH, TARGET_HEIGHT), PILImage.LANCZOS)
        image = np.array(pil_image)
        image = image.astype(np.float32) / 255.0  # Normalize to [0, 1]
        image = np.expand_dims(image, axis=0)  # Add channel dimension
        image = np.expand_dims(image, axis=0)  # Add batch dimension
        # Make prediction
        output = model_service.predict(image)
        output_image = output[0][0]
        print(np.max(output_image))
        print(np.min(output_image))
        print(np.sum(output_image > THRESHOLD))
        output_pil = PILImage.fromarray((output_image * 255).astype(np.uint8))
        output_pil = output_pil.resize((original_width, original_height), PILImage.LANCZOS)
        output_array = np.array(output_pil) / 255.0
        predicted_mask = (output_array > THRESHOLD).astype(np.uint8)
        if np.any(predicted_mask == 1):
            ellipse = fit_ellipse(predicted_mask)
        else:
            ellipse = None
        endpoint1 = endpoint2 = None
        if ellipse is not None:
            # Get the two coordinates of the minor axis endpoints
            center_x, center_y = ellipse.center_x, ellipse.center_y
            minor_axis_half = ellipse.minor_axis / 2
            angle_rad = np.radians(ellipse.angle + 90)  # Add 90 degrees for minor axis
            
            # Calculate the two endpoints of the minor axis
            dx = minor_axis_half * np.cos(angle_rad)
            dy = minor_axis_half * np.sin(angle_rad)
            endpoint1 = (center_x + dx, center_y + dy)
            endpoint2 = (center_x - dx, center_y - dy)
        output_mask = [mask_row.tolist() for mask_row in predicted_mask]
        return PredictionResponse(prediction=Prediction(
            seg_mask=output_mask,
            endpoints=(endpoint1, endpoint2) if endpoint1 and endpoint2 else None
        ))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)