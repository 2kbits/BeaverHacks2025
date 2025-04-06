# backend/app/routers/bus_data.py

import csv
import math
import logging
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Any, Optional
from datetime import datetime, time # Import datetime objects

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

# --- Configuration ---
CURRENT_DIR = Path(__file__).parent
BACKEND_DIR = CURRENT_DIR.parent.parent
CSV_FILE_PATH = BACKEND_DIR / "data" / "busDatabase.csv"

# --- Column Names ---
# !! IMPORTANT: Verify these match your busDatabase.csv headers exactly !!
COL_STOP_NAME = "stop_name"
COL_BUS_ID = "bus_id"
COL_ROUTE = "published_line"
COL_DELAY_MINUTES = "scheduled_delay_minutes" # Still needed for original endpoints
COL_HOUR = "hour_of_day"
COL_SCHEDULED_ARRIVAL = "scheduled_arrival"
COL_PREDICTION_ERROR = "prediction_error_minutes" # Added

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- Data Storage ---
BUS_DATA: List[Dict[str, Any]] = []
data_load_error: Optional[str] = None
UNIQUE_STOP_NAMES: List[str] = [] # Cache for stop names

# --- Pydantic Models ---

# Original endpoint models
class ChartDataResponse(BaseModel):
    routes: List[str] = Field(..., description="List of unique bus route names.")
    avg_delays: List[float] = Field(
        ..., description="List of corresponding average delays in minutes."
    )

class FilterOptionsResponse(BaseModel):
    routes: List[str] = Field(..., description="List of unique bus route names.")

class ArrivalDataResponse(BaseModel):
    scheduled_arrival: Optional[str] = Field(
        None, description="First scheduled arrival time found for the criteria (ISO format or similar)."
    )
    average_delay: float = Field(
        ..., description="Average delay in minutes for the specified route and hour."
    )

# Modified StopRouteScheduleInfo model for the new average calculation
class StopRouteScheduleInfo(BaseModel):
    route: str = Field(..., description="The bus route identifier (published_line).")
    average_prediction_error_at_schedule: Optional[float] = Field(
        None, description="Average prediction error (in minutes) for all records matching the next_scheduled_arrival time. Null if no data or next arrival found."
    )
    next_bus_id: Optional[str] = Field(
        None, description="The bus_id of the next scheduled bus at or after the requested time. Null if none found."
    )
    next_scheduled_arrival: Optional[str] = Field(
        None, description="The scheduled arrival time string for the next bus. Null if none found."
    )

class StopScheduleResponse(BaseModel):
    stop_name: str = Field(..., description="The requested stop name.")
    requested_time: str = Field(..., description="The requested time in HH:MM format.")
    routes_at_stop: List[StopRouteScheduleInfo] = Field(
        ..., description="Schedule information for each unique route serving this stop."
    )

# Add model for the new stop names endpoint
class StopNamesResponse(BaseModel):
    stop_names: List[str] = Field(..., description="List of unique stop names found in the data.")


# --- Data Loading Function (Modified to cache stop names and load prediction error) ---
def load_bus_data():
    """Loads and preprocesses bus data from the CSV file."""
    global BUS_DATA, data_load_error, UNIQUE_STOP_NAMES
    BUS_DATA = []
    UNIQUE_STOP_NAMES = [] # Clear cache on reload
    data_load_error = None
    processed_count = 0
    skipped_count = 0
    stop_name_set = set() # Use a set for efficient uniqueness check

    try:
        logger.info(f"Attempting to load bus data from: {CSV_FILE_PATH}")
        if not CSV_FILE_PATH.is_file():
            raise FileNotFoundError(f"CSV file not found at {CSV_FILE_PATH}")

        # Add the new column to required columns
        required_columns = {
            COL_STOP_NAME, COL_BUS_ID, COL_ROUTE,
            COL_DELAY_MINUTES, COL_HOUR, COL_SCHEDULED_ARRIVAL,
            COL_PREDICTION_ERROR # Added
        }

        with open(CSV_FILE_PATH, mode="r", encoding="utf-8-sig") as csvfile:
            reader = csv.DictReader(csvfile)
            if not reader.fieldnames:
                 raise ValueError("CSV file appears to be empty or has no header row.")
            if not required_columns.issubset(reader.fieldnames):
                missing = required_columns - set(reader.fieldnames)
                available = list(reader.fieldnames)
                raise ValueError(
                    f"Missing required columns: {missing}. Available columns: {available}"
                )

            for i, row in enumerate(reader):
                line_num = i + 2
                try:
                    stop_name = row.get(COL_STOP_NAME, "").strip()
                    bus_id = row.get(COL_BUS_ID, "").strip()
                    route = row.get(COL_ROUTE, "").strip()
                    hour_str = row.get(COL_HOUR)
                    delay_str = row.get(COL_DELAY_MINUTES)
                    scheduled_arrival_str = row.get(COL_SCHEDULED_ARRIVAL)
                    prediction_error_str = row.get(COL_PREDICTION_ERROR) # Added

                    # --- Start Validation ---
                    if not all([stop_name, bus_id, route, scheduled_arrival_str]):
                        skipped_count += 1; continue
                    # Check new column too
                    if hour_str is None or delay_str is None or prediction_error_str is None:
                         skipped_count += 1; continue

                    hour = int(hour_str)
                    delay_minutes = float(delay_str)
                    prediction_error_minutes = float(prediction_error_str) # Added conversion

                    if not (0 <= hour <= 23): skipped_count += 1; continue
                    if not math.isfinite(delay_minutes): skipped_count += 1; continue
                    if not math.isfinite(prediction_error_minutes): # Added validation
                         skipped_count += 1; continue
                    if len(scheduled_arrival_str) < 16: skipped_count += 1; continue
                    try: datetime.strptime(scheduled_arrival_str, '%Y-%m-%d %H:%M:%S')
                    except (ValueError, TypeError): skipped_count += 1; continue
                    # --- End Validation ---

                    processed_row = {
                        COL_STOP_NAME: stop_name, COL_BUS_ID: bus_id, COL_ROUTE: route,
                        COL_HOUR: hour, COL_DELAY_MINUTES: delay_minutes,
                        COL_SCHEDULED_ARRIVAL: scheduled_arrival_str,
                        COL_PREDICTION_ERROR: prediction_error_minutes # Added to stored data
                    }
                    BUS_DATA.append(processed_row)
                    stop_name_set.add(stop_name) # Add valid stop name to set
                    processed_count += 1

                except (ValueError, TypeError) as conv_err:
                    # Log less verbosely during normal operation
                    # logger.warning(f"Skipping row {line_num} due to data conversion error: {conv_err}.")
                    skipped_count += 1
                    continue

        # Assign the sorted list of unique names to the global variable
        UNIQUE_STOP_NAMES = sorted(list(stop_name_set))
        logger.info(
            f"Successfully processed {processed_count} records. Skipped {skipped_count} rows. Found {len(UNIQUE_STOP_NAMES)} unique stop names."
        )
        if processed_count == 0:
             logger.error("No valid data records were loaded. Check CSV format/content.")
             if skipped_count > 0:
                 data_load_error = "CSV contains rows, but none could be processed successfully."
             else:
                 data_load_error = "CSV file appears empty or contains no processable data."

    except FileNotFoundError as e:
        data_load_error = f"Error loading data: {e}"
        logger.error(data_load_error)
    except ValueError as e: # Catches header/format issues
        data_load_error = f"CSV format or data error: {e}"
        logger.error(data_load_error)
    except Exception as e:
        data_load_error = f"An unexpected error occurred during data loading: {e}"
        logger.exception(data_load_error) # Log full traceback for unexpected errors

# --- Load data when the module is imported (FastAPI starts/reloads) ---
load_bus_data()

# --- API Router ---
router = APIRouter(
    prefix="/api",
    tags=["Bus Data"]
)

# --- Helper Function to Check Data Loading Status ---
def check_data_loaded():
    """Raises HTTPException if data failed to load or is unavailable."""
    if data_load_error:
        logger.error(f"Data loading check failed: {data_load_error}")
        # Send generic error to client, keep details in server logs
        raise HTTPException(
            status_code=500,
            detail="Internal Server Error: Could not load bus data.",
        )
    # Check BUS_DATA specifically, as UNIQUE_STOP_NAMES might be empty even if loading succeeded
    if not BUS_DATA:
        logger.warning("Data check: BUS_DATA list is empty.")
        raise HTTPException(
            status_code=404,
            detail="No bus data available.",
        )

# --- API Endpoints ---

@router.get("/bus-data", response_model=ChartDataResponse)
async def get_bus_data_for_chart():
    """
    Calculates the average scheduled delay for each unique bus route across all data.
    Used to populate the main overview chart.
    """
    check_data_loaded()
    route_stats = defaultdict(lambda: {"sum_delay": 0.0, "count": 0})
    for record in BUS_DATA:
        route_name = record.get(COL_ROUTE)
        delay_minutes = record.get(COL_DELAY_MINUTES)
        # Data should be validated during load, but check anyway
        if route_name and isinstance(delay_minutes, float) and math.isfinite(delay_minutes):
            route_stats[route_name]["sum_delay"] += delay_minutes
            route_stats[route_name]["count"] += 1

    chart_output = {"routes": [], "avg_delays": []}
    sorted_routes = sorted(route_stats.keys())
    for route in sorted_routes:
        stats = route_stats[route]
        if stats["count"] > 0:
            average_delay = stats["sum_delay"] / stats["count"]
            chart_output["routes"].append(route)
            chart_output["avg_delays"].append(round(average_delay, 2))

    if not chart_output["routes"]:
        logger.warning("No valid route data found to generate chart output.")
    return chart_output

@router.get("/filter-options", response_model=FilterOptionsResponse)
async def get_filter_options():
    """
    Provides unique bus route names available in the dataset.
    """
    check_data_loaded()
    unique_routes = set(record.get(COL_ROUTE) for record in BUS_DATA if record.get(COL_ROUTE))
    sorted_routes = sorted(list(unique_routes))
    if not sorted_routes:
        logger.warning("Filter options requested, but no unique routes found.")
    return {"routes": sorted_routes}

@router.get("/find-arrival", response_model=ArrivalDataResponse)
async def find_average_delay_for_route_hour(
    route: str = Query(..., description="The bus route name (e.g., 'M15')."),
    hour: int = Query(..., ge=0, le=23, description="The hour of the day (0-23).")
):
    """
    (Original endpoint) Finds the average scheduled delay for a specific bus route
    at a specific hour across all stops.
    """
    check_data_loaded()
    logger.info(f"Original endpoint search for route: '{route}', hour: {hour}")
    total_delay = 0.0
    record_count = 0
    first_scheduled_arrival = None
    for record in BUS_DATA:
        if (
            record.get(COL_ROUTE) == route
            and record.get(COL_HOUR) == hour
        ):
            delay = record.get(COL_DELAY_MINUTES)
            # Data validated during load
            total_delay += delay
            record_count += 1
            if first_scheduled_arrival is None:
                first_scheduled_arrival = record.get(COL_SCHEDULED_ARRIVAL)

    if record_count > 0:
        average_delay = total_delay / record_count
        logger.info(
            f"Found {record_count} records for route '{route}' at hour {hour}. Avg delay: {average_delay:.2f}"
        )
        return {
            "scheduled_arrival": first_scheduled_arrival,
            "average_delay": round(average_delay, 2),
        }
    else:
        logger.info(f"No matching records found for route '{route}' at hour {hour}.")
        raise HTTPException(
            status_code=404,
            detail=f"No arrival data found for route '{route}' at hour {hour}",
        )

# --- Endpoint for Stop Names (Corrected Access) ---
@router.get("/stop-names", response_model=StopNamesResponse)
async def get_stop_names():
    """Provides a sorted list of unique stop names found in the data."""
    # 1. Check if data loading failed or resulted in no BUS_DATA
    check_data_loaded()

    # 2. Access the global variable populated by load_bus_data
    if not UNIQUE_STOP_NAMES:
         logger.warning("Stop names requested, but the UNIQUE_STOP_NAMES list is empty.")
         return {"stop_names": []}

    # If we reach here, UNIQUE_STOP_NAMES is defined and likely not empty
    return {"stop_names": UNIQUE_STOP_NAMES}


# --- Endpoint for Stop Schedule (Logic Modified for Avg Prediction Error) ---
@router.get("/stop-schedule", response_model=StopScheduleResponse)
async def get_schedule_for_stop(
    stop_name: str = Query(..., min_length=1, description="The exact name of the bus stop."),
    hour: int = Query(..., ge=0, le=23, description="Requested hour (0-23)."),
    minute: int = Query(..., ge=0, le=59, description="Requested minute (0-59).")
):
    """
    For a given stop name and time (hour:minute), finds the next scheduled
    bus and the average prediction error associated with that specific
    scheduled arrival time for each route serving the stop.
    """
    check_data_loaded()
    logger.info(f"Request received for stop: '{stop_name}', time: {hour:02d}:{minute:02d}")

    # Filter data for the specific stop first
    stop_specific_data = [
        record for record in BUS_DATA if record.get(COL_STOP_NAME) == stop_name
    ]
    if not stop_specific_data:
        # If the stop name doesn't exist in any processed record
        raise HTTPException(status_code=404, detail=f"No data found for stop name: '{stop_name}'")

    # Group the stop-specific data by route
    routes_data = defaultdict(list)
    for record in stop_specific_data:
        route = record.get(COL_ROUTE)
        if route: routes_data[route].append(record)

    if not routes_data:
         # Stop exists, but no routes associated (shouldn't happen if data is clean)
         logger.warning(f"Data found for stop '{stop_name}', but no valid routes associated.")
         return StopScheduleResponse(
             stop_name=stop_name, requested_time=f"{hour:02d}:{minute:02d}", routes_at_stop=[]
         )

    results_for_routes: List[StopRouteScheduleInfo] = []
    user_time_obj = time(hour, minute) # Target time for comparison

    # Process each route found at this stop
    for route, records in routes_data.items():
        logger.debug(f"Processing route: {route} for stop '{stop_name}'")

        # --- Find Nearest Scheduled Arrival >= user time ---
        next_bus: Optional[Dict] = None
        valid_records_with_dt = []
        for record in records:
             try:
                  dt = datetime.strptime(record[COL_SCHEDULED_ARRIVAL], '%Y-%m-%d %H:%M:%S')
                  valid_records_with_dt.append((dt, record)) # Store (datetime, record)
             except (ValueError, TypeError):
                  continue # Skip records with unparseable dates
        valid_records_with_dt.sort(key=lambda item: item[0]) # Sort by datetime
        for scheduled_dt, record in valid_records_with_dt:
            if scheduled_dt.time() >= user_time_obj:
                next_bus = record # Found the first match
                break # Stop searching for this route

        # --- Calculate Average Prediction Error for the Found Schedule ---
        avg_pred_error: Optional[float] = None
        if next_bus:
            # Get the exact scheduled arrival time string of the next bus found
            target_schedule_str = next_bus.get(COL_SCHEDULED_ARRIVAL)
            total_pred_error = 0.0
            pred_error_count = 0
            # Iterate through ALL records for this route/stop again to find matches
            for record in records:
                # Find records matching the exact scheduled arrival time string
                if record.get(COL_SCHEDULED_ARRIVAL) == target_schedule_str:
                    pred_error = record.get(COL_PREDICTION_ERROR)
                    # Ensure the error value is valid (should be float from loading)
                    if isinstance(pred_error, float) and math.isfinite(pred_error):
                        total_pred_error += pred_error
                        pred_error_count += 1

            if pred_error_count > 0:
                avg_pred_error = round(total_pred_error / pred_error_count, 2)
                logger.debug(f"Avg prediction error for {route} @ {target_schedule_str}: {avg_pred_error} ({pred_error_count} records)")
            else:
                 logger.warning(f"Found next bus for {route} @ {target_schedule_str}, but no valid prediction errors to average.")
        else:
            logger.debug(f"No next bus found for route {route}, cannot calculate prediction error.")


        # --- Prepare result for this route ---
        results_for_routes.append(StopRouteScheduleInfo(
            route=route,
            # Use the new average prediction error field
            average_prediction_error_at_schedule=avg_pred_error,
            next_bus_id=next_bus.get(COL_BUS_ID) if next_bus else None,
            next_scheduled_arrival=next_bus.get(COL_SCHEDULED_ARRIVAL) if next_bus else None,
        ))

    # Sort final results by route name before returning
    results_for_routes.sort(key=lambda r: r.route)
    return StopScheduleResponse(
        stop_name=stop_name, requested_time=f"{hour:02d}:{minute:02d}", routes_at_stop=results_for_routes
    )

