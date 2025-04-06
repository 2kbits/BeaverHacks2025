# backend/app/routers/prediction.py

import pickle
import numpy as np
import logging
from pathlib import Path
from datetime import datetime, time
from typing import Optional, Tuple # Added Tuple

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from statsmodels.nonparametric.smoothers_lowess import lowess # Ensure lowess is available

# --- Configuration ---
CURRENT_DIR = Path(__file__).parent
BACKEND_DIR = CURRENT_DIR.parent.parent
MODEL_FILE_PATH = BACKEND_DIR / "data" / "bus_delay_model.pkl" # Path to your model

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- Import data and constants from the bus_data router ---
# This assumes bus_data.py is in the same directory or accessible
# Be mindful of potential circular imports if prediction.py imports bus_data
# and bus_data.py were to import prediction.py (which it doesn't here).
try:
    # Import the actual list, the column name constant, and the check function
    from .bus_data import BUS_DATA, COL_SCHEDULED_ARRIVAL, check_data_loaded as check_bus_data_loaded
    logger.info("Successfully imported BUS_DATA and COL_SCHEDULED_ARRIVAL from .bus_data")
except ImportError as e:
    # Fallback if running script directly or structure changes
    logger.error(f"Could not import from .bus_data: {e}. Schedule lookup will fail.")
    BUS_DATA = [] # Define as empty list to prevent NameError later
    COL_SCHEDULED_ARRIVAL = "scheduled_arrival" # Default fallback name
    # Define a dummy check function if import fails
    def check_bus_data_loaded():
         if not BUS_DATA:
             logger.error("Bus data check failed: BUS_DATA is empty (import failed).")
             raise HTTPException(status_code=503, detail="Historical bus data is unavailable due to import error.")

# --- Model Storage ---
MODEL_DATA: Optional[dict] = None
model_load_error: Optional[str] = None

# --- Pydantic Models ---
class NextPredictionResponse(BaseModel): # Renamed for clarity
    requested_time: str = Field(..., description="The time string submitted by the user (HH:MM:SS).")
    next_scheduled_time_used: Optional[str] = Field(
        None, description="The next scheduled bus time (HH:MM:SS) found at or after the requested time, used for prediction. Null if none found."
    )
    predicted_delay_minutes: Optional[float] = Field(
        None, description="Predicted delay in minutes for the next_scheduled_time_used. Null if prediction failed or no next time found."
    )
    message: str = Field(..., description="A message indicating success or the reason for failure/no prediction.")

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
        if not isinstance(MODEL_DATA['smoothed_curve'], np.ndarray) or MODEL_DATA['smoothed_curve'].ndim != 2:
             raise ValueError("Model data 'smoothed_curve' is not a 2D numpy array.")

        logger.info("Prediction model loaded successfully.")

    except FileNotFoundError as e:
        model_load_error = f"Error loading prediction model: {e}"; logger.error(model_load_error)
    except (pickle.UnpicklingError, ValueError, EOFError, TypeError) as e: # Added TypeError
        model_load_error = f"Error reading or validating model file ({type(e).__name__}): {e}"; logger.error(model_load_error)
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

# --- Helper: Find Next Scheduled Time ---
def find_next_scheduled_time(user_time_str: str) -> Optional[time]:
    """
    Finds the earliest unique scheduled arrival time from BUS_DATA
    that occurs at or after the user's requested time.

    Args:
        user_time_str: Time string in HH:MM:SS format.

    Returns:
        The next datetime.time object, or None if none found or data error.
    """
    try:
        # Use the imported check function for bus data
        check_bus_data_loaded()
        user_time = datetime.strptime(user_time_str, '%H:%M:%S').time()
    except ValueError: # Catches invalid user time format
        logger.error(f"Invalid user time format provided: {user_time_str}")
        return None
    except HTTPException as e: # Catches bus data loading issues
         logger.error(f"Bus data unavailable for finding next schedule: {e.detail}")
         return None

    potential_next_times = set() # Use set for unique times

    for record in BUS_DATA:
        # Use the imported constant for the column name
        scheduled_arrival_str = record.get(COL_SCHEDULED_ARRIVAL)
        if not scheduled_arrival_str: continue
        try:
            # We only care about the TIME part for comparison and finding the *next* time slot
            scheduled_dt = datetime.strptime(scheduled_arrival_str, '%Y-%m-%d %H:%M:%S')
            scheduled_time = scheduled_dt.time()

            if scheduled_time >= user_time:
                potential_next_times.add(scheduled_time)
        except (ValueError, TypeError):
            # Log invalid format in historical data if needed, but continue
            # logger.debug(f"Skipping record with invalid datetime format: {scheduled_arrival_str}")
            continue

    if not potential_next_times:
        logger.info(f"No scheduled times found in BUS_DATA at or after {user_time_str}")
        return None # No schedules found at or after user time

    # Find the minimum (earliest) time from the set
    next_time = min(potential_next_times)
    logger.debug(f"Found next potential scheduled time: {next_time.strftime('%H:%M:%S')}")
    return next_time


# --- Prediction Logic (Adapted from your script, uses numpy.interp) ---
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
        # Validate structure again just before use
        if 'smoothed_curve' not in model_data or not isinstance(model_data['smoothed_curve'], np.ndarray):
             logger.error("Invalid model structure passed to predict_delay_from_model.")
             return None
        smoothed = model_data['smoothed_curve']

        # Convert target time to minutes
        t = datetime.strptime(target_time_str, '%H:%M:%S').time()
        target_minutes = t.hour * 60 + t.minute + t.second / 60

        # Extract X and Y from the smoothed data
        # Ensure smoothed_x is sorted (should be from LOWESS)
        smoothed_x = smoothed[:, 0]
        smoothed_y = smoothed[:, 1]

        # Use numpy.interp for efficient interpolation (handles edges automatically)
        predicted_delay = np.interp(target_minutes, smoothed_x, smoothed_y)

        # Optional: Check if target_minutes is outside the range of smoothed_x
        # if not (smoothed_x.min() <= target_minutes <= smoothed_x.max()):
        #     logger.warning(f"Target time {target_minutes:.2f} min is outside the model's trained range ({smoothed_x.min():.2f}-{smoothed_x.max():.2f}). Prediction might be less reliable.")

        return float(predicted_delay) # Ensure it's a standard float

    except ValueError as e: # Catch errors like invalid time format
        logger.error(f"ValueError during prediction calculation for time '{target_time_str}': {e}")
        return None
    except IndexError as e: # Catch potential issues if smoothed_curve isn't 2D
         logger.error(f"IndexError during prediction calculation (check model data format): {e}")
         return None
    except Exception as e:
        logger.error(f"Unexpected error during prediction calculation for time '{target_time_str}': {e}")
        return None


# --- API Endpoint for Predicting Next Delay ---
@router.get("/predict-next-delay", response_model=NextPredictionResponse)
async def get_next_delay_prediction(
    time_str: str = Query(
        ...,
        description="User's current/desired time in HH:MM:SS format.",
        regex="^([01]\d|2[0-3]):([0-5]\d):([0-5]\d)$" # Regex for HH:MM:SS validation
    )
):
    """
    Finds the next scheduled bus time at or after the requested time,
    then predicts the delay for *that* scheduled time using the AI model.
    """
    check_model_loaded() # Ensure AI model is ready first

    logger.info(f"Next delay prediction requested for time >= {time_str}")

    # 1. Find the next scheduled time using the helper
    next_schedule_time_obj = find_next_scheduled_time(time_str)

    # Handle case where no next time is found (includes bus data errors)
    if next_schedule_time_obj is None:
        logger.warning(f"Could not find a valid scheduled bus time at or after {time_str}.")
        # Check if the reason was invalid user input time format
        try:
            datetime.strptime(time_str, '%H:%M:%S')
            message = "No scheduled bus found at or after the requested time in the historical data."
        except ValueError:
             message = "Invalid requested time format provided."

        return NextPredictionResponse(
            requested_time=time_str,
            next_scheduled_time_used=None,
            predicted_delay_minutes=None,
            message=message
        )

    # Format the found time for prediction input and response
    next_schedule_time_str = next_schedule_time_obj.strftime('%H:%M:%S')
    logger.info(f"Found next scheduled time: {next_schedule_time_str}. Predicting delay for this time.")

    # 2. Predict delay for the found scheduled time
    predicted_value = predict_delay_from_model(MODEL_DATA, next_schedule_time_str)

    # Handle successful prediction
    if predicted_value is not None:
        return NextPredictionResponse(
            requested_time=time_str,
            next_scheduled_time_used=next_schedule_time_str,
            predicted_delay_minutes=round(predicted_value, 2),
            message="Prediction successful for the next scheduled bus time."
        )
    # Handle prediction failure for the found time
    else:
        logger.error(f"AI model failed to predict delay for the found time: {next_schedule_time_str}")
        return NextPredictionResponse(
            requested_time=time_str,
            next_scheduled_time_used=next_schedule_time_str,
            predicted_delay_minutes=None,
            message=f"Found next schedule time ({next_schedule_time_str}), but failed to get AI prediction for it. Check server logs."
        )

# --- Optional: Keep or remove the original endpoint ---
# If you want to keep the endpoint that predicts for the *exact* time given:
# from pydantic import BaseModel as PredictionResponse # Define or import original model
# @router.get("/predict-delay", response_model=PredictionResponse)
# async def get_delay_prediction(...): ... (original logic)

# --- (End of file) ---
