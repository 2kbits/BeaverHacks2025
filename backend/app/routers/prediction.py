# backend/app/routers/prediction.py

import pickle
import numpy as np
import logging
from pathlib import Path
from datetime import datetime, time
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from statsmodels.nonparametric.smoothers_lowess import lowess # Make sure lowess is available

# --- Configuration ---
CURRENT_DIR = Path(__file__).parent
BACKEND_DIR = CURRENT_DIR.parent.parent
MODEL_FILE_PATH = BACKEND_DIR / "data" / "bus_delay_model.pkl" # Path to your model

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- Model Storage ---
MODEL_DATA: Optional[dict] = None
model_load_error: Optional[str] = None

# --- Pydantic Models ---
class PredictionResponse(BaseModel):
    requested_time: str = Field(..., description="The time string submitted for prediction (HH:MM:SS).")
    predicted_delay_minutes: Optional[float] = Field(
        None, description="Predicted delay in minutes. Null if prediction failed or time is out of range."
    )
    message: str = Field(..., description="A message indicating success or the reason for failure.")

# --- Model Loading Function ---
def load_prediction_model():
    """Loads the pickled prediction model data from disk."""
    global MODEL_DATA, model_load_error
    MODEL_DATA = None # Reset on reload
    model_load_error = None
    try:
        logger.info(f"Attempting to load prediction model from: {MODEL_FILE_PATH}")
        if not MODEL_FILE_PATH.is_file():
            raise FileNotFoundError(f"Model file not found at {MODEL_FILE_PATH}")

        with open(MODEL_FILE_PATH, 'rb') as f:
            MODEL_DATA = pickle.load(f)

        # Basic validation of loaded model structure (adjust based on your actual .pkl content)
        if not isinstance(MODEL_DATA, dict) or 'smoothed_curve' not in MODEL_DATA:
             raise ValueError("Loaded model data is not in the expected format (missing 'smoothed_curve').")

        logger.info("Prediction model loaded successfully.")

    except FileNotFoundError as e:
        model_load_error = f"Error loading prediction model: {e}"; logger.error(model_load_error)
    except (pickle.UnpicklingError, ValueError, EOFError) as e:
        model_load_error = f"Error reading or validating model file: {e}"; logger.error(model_load_error)
    except Exception as e:
        model_load_error = f"An unexpected error occurred during model loading: {e}"; logger.exception(model_load_error)

# --- Load model when the module is imported ---
load_prediction_model()

# --- API Router ---
router = APIRouter(prefix="/api", tags=["Prediction"])

# --- Helper Function to Check Model Loading Status ---
def check_model_loaded():
    """Raises HTTPException if the model failed to load."""
    if model_load_error:
        logger.error(f"Model loading check failed: {model_load_error}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: Could not load prediction model. Reason: {model_load_error}")
    if MODEL_DATA is None:
        logger.warning("Prediction check: MODEL_DATA is None.")
        raise HTTPException(status_code=503, detail="Service Unavailable: Prediction model not loaded.")

# --- Prediction Logic (Adapted from your script) ---
def predict_delay_from_model(model_data: dict, target_time_str: str) -> Optional[float]:
    """
    Uses the loaded LOWESS model data to predict delay for a target time.

    Args:
        model_data: The dictionary loaded from the .pkl file.
        target_time_str: Time string in 'HH:MM:SS' format.

    Returns:
        Predicted delay in minutes, or None if prediction fails.
    """
    try:
        smoothed = model_data['smoothed_curve'] # Assumes this structure exists

        # Convert target time to minutes
        t = datetime.strptime(target_time_str, '%H:%M:%S').time()
        target_minutes = t.hour * 60 + t.minute + t.second / 60

        # Interpolate using the smoothed data (X is smoothed[:, 0], Y is smoothed[:, 1])
        smoothed_x = smoothed[:, 0]
        smoothed_y = smoothed[:, 1]

        # Use numpy.interp for efficient interpolation (handles edges automatically)
        # It requires that smoothed_x is sorted, which LOWESS output should be.
        predicted_delay = np.interp(target_minutes, smoothed_x, smoothed_y)

        # Optional: Check if target_minutes is outside the range of smoothed_x
        # np.interp handles this by default by returning the boundary value,
        # but you could add a check if you want different behavior.
        # if not (smoothed_x.min() <= target_minutes <= smoothed_x.max()):
        #     logger.warning(f"Target time {target_minutes} min is outside the model's trained range ({smoothed_x.min()}-{smoothed_x.max()}). Prediction might be less reliable.")

        return float(predicted_delay) # Ensure it's a standard float

    except ValueError as e: # Catch errors like invalid time format
        logger.error(f"ValueError during prediction for time '{target_time_str}': {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during prediction for time '{target_time_str}': {e}")
        return None


# --- API Endpoint ---
@router.get("/predict-delay", response_model=PredictionResponse)
async def get_delay_prediction(
    time_str: str = Query(
        ...,
        description="Time for prediction in HH:MM:SS format.",
        regex="^([01]\d|2[0-3]):([0-5]\d):([0-5]\d)$" # Regex for HH:MM:SS validation
    )
):
    """
    Predicts the bus delay based on the time of day using a pre-trained model.
    """
    check_model_loaded() # Ensure model is ready

    logger.info(f"Prediction requested for time: {time_str}")

    predicted_value = predict_delay_from_model(MODEL_DATA, time_str)

    if predicted_value is not None:
        return PredictionResponse(
            requested_time=time_str,
            predicted_delay_minutes=round(predicted_value, 2),
            message="Prediction successful."
        )
    else:
        # Prediction failed (e.g., error during interpolation, invalid time caught deeper)
        # We return None for the value but indicate failure in the message.
        # The specific reason would be in the server logs.
        # We could raise HTTPException here, but returning a structured error might be better for the frontend.
        logger.warning(f"Prediction failed for time: {time_str}. See previous logs for details.")
        return PredictionResponse(
            requested_time=time_str,
            predicted_delay_minutes=None,
            message="Prediction failed. The requested time might be invalid or an internal error occurred."
        )

# --- (End of file) ---
