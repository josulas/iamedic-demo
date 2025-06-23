import numpy as np
import onnxruntime as ort
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from PIL import Image as PILImage
import cv2

from lukinoising4GP import lukinoising

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
    minor_axis: float
    major_axis: float
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
            self.model = ort.InferenceSession(MODEL_PATH)
            print(f"Model loaded successfully")            
        except Exception as e:
            print(f"Error loading model: {e}")
            raise
    
    def predict(self, input_tensor: np.ndarray) -> np.ndarray:
        """Make predictions using the loaded model"""
        if self.model is None:
            raise RuntimeError("Model not loaded")
        inputs = {self.model.get_inputs()[0].name: input_tensor}
        outputs = self.model.run(None, inputs)
        ort_preds = outputs[0]
        return ort_preds


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
    (minor_axis, major_axis) = axes
    return Ellipse(
        center_x=center[0],
        center_y=center[1],
        minor_axis=minor_axis,
        major_axis=major_axis,
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
        input_array = np.array(request.data, dtype=np.uint8)
        original_height, original_width = input_array.shape
        denoised_array = lukinoising(input_array, alpha=0.5, beta=0.5)
        img = PILImage.fromarray(denoised_array)
        resized_img = img.resize((TARGET_WIDTH, TARGET_HEIGHT),  PILImage.LANCZOS)
        img_array = np.array(resized_img, dtype=np.float32) / 255.0
        input_tensor = img_array[np.newaxis, np.newaxis, :, :]
        output = model_service.predict(input_tensor)
        sigmoid_output = 1 / (1 + np.exp(-output))  # Apply sigmoid to the output
        output_image = sigmoid_output[0][0]
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
            center = (ellipse.center_x, ellipse.center_y)
            minor_axis = ellipse.minor_axis
            major_axis = ellipse.major_axis
            angle = ellipse.angle
            x1 = int(center[0] - minor_axis / 2 * np.cos(np.deg2rad(angle)))
            y1 = int(center[1] - minor_axis / 2 * np.sin(np.deg2rad(angle)))
            x2 = int(center[0] + minor_axis / 2 * np.cos(np.deg2rad(angle)))
            y2 = int(center[1] + minor_axis / 2 * np.sin(np.deg2rad(angle)))
            endpoint1 = (x1, y1)
            endpoint2 = (x2, y2)
        output_mask = [mask_row.tolist() for mask_row in predicted_mask]
        print(f"Endpoints: {endpoint1}, {endpoint2}")
        return PredictionResponse(prediction=Prediction(
            seg_mask=output_mask,
            tn_endpoints=(endpoint1, endpoint2) if endpoint1 and endpoint2 else None
        ))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)