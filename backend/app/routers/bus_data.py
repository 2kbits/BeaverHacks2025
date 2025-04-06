# backend/app/routers/bus_data.py

import csv
import math
import logging
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Any, Optional # For type hinting

from fastapi import APIRouter, HTTPException, Query # Query for parameter validation
from pydantic import BaseModel, Field # For request/response models

# --- Configuration ---
# Get the directory where this script (bus_data.py) is located
CURRENT_DIR = Path(__file__).parent
# Go up two levels to the 'backend' directory
BACKEND_DIR = CURRENT_DIR.parent.parent
# Construct the full path to the CSV file in the 'data' subdirectory
CSV_FILE_PATH = BACKEND_DIR / "data" / "busDatabase.csv"

# --- Column Names (Centralized Configuration) ---
# !! IMPORTANT: Verify these match your busDatabase.csv headers exactly !!
# Using constants makes it easier to change if the CSV format changes.
COL_ROUTE = "published_line" # Was "published_line"
COL_DELAY_MINUTES = "scheduled_delay_minutes" # Was "scheduled_delay_minutes"
COL_HOUR = "hour_of_day" # Was "hour_of_day"
COL_SCHEDULED_ARRIVAL = "scheduled_arrival" # Was "scheduled_arrival"

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- Data Storage ---
BUS_DATA: List[Dict[str, Any]] = [] # Type hint for clarity
data_load_error: Optional[str] = None # Type hint

# --- Pydantic Models (for Response Validation & Documentation) ---
# These define the expected structure of the JSON responses.
# FastAPI uses these for automatic validation and OpenAPI documentation.

class ChartDataResponse(BaseModel):
    routes: List[str] = Field(..., description="List of unique bus route names.")
    avg_delays: List[float] = Field(
        ..., description="List of corresponding average delays in minutes."
    )

class FilterOptionsResponse(BaseModel):
    routes: List[str] = Field(..., description="List of unique bus route names.")
    # Add hours here if you ever need them for filtering
    # hours: List[int] = Field(..., description="List of unique hours (0-23).")

class ArrivalDataResponse(BaseModel):
    # Allow scheduled_arrival to be None if not found for the specific hour/route combo
    scheduled_arrival: Optional[str] = Field(
        None, description="First scheduled arrival time found for the criteria (ISO format or similar)."
    )
    average_delay: float = Field(
        ..., description="Average delay in minutes for the specified route and hour."
    )

# --- Data Loading Function ---
def load_bus_data():
    """Loads and preprocesses bus data from the CSV file."""
    global BUS_DATA, data_load_error
    BUS_DATA = []
    data_load_error = None
    processed_count = 0
    skipped_count = 0

    try:
        logger.info(f"Attempting to load bus data from: {CSV_FILE_PATH}")
        if not CSV_FILE_PATH.is_file():
            raise FileNotFoundError(f"CSV file not found at {CSV_FILE_PATH}")

        required_columns = {
            COL_ROUTE,
            COL_DELAY_MINUTES,
            COL_HOUR,
            COL_SCHEDULED_ARRIVAL,
        }

        with open(CSV_FILE_PATH, mode="r", encoding="utf-8-sig") as csvfile:
            reader = csv.DictReader(csvfile)

            if not required_columns.issubset(reader.fieldnames):
                missing = required_columns - set(reader.fieldnames)
                available = reader.fieldnames
                raise ValueError(
                    f"Missing required columns: {missing}. "
                    f"Available columns: {available}"
                )

            for i, row in enumerate(reader):
                line_num = i + 2 # Account for header and 0-based index
                try:
                    route = row.get(COL_ROUTE, "").strip()
                    hour_str = row.get(COL_HOUR)
                    delay_str = row.get(COL_DELAY_MINUTES)

                    # Basic validation before conversion
                    if not route:
                        logger.warning(f"Skipping row {line_num}: Empty route name.")
                        skipped_count += 1
                        continue
                    if hour_str is None or delay_str is None:
                         logger.warning(f"Skipping row {line_num}: Missing hour or delay value.")
                         skipped_count += 1
                         continue

                    # Convert and validate data types
                    hour = int(hour_str)
                    delay_minutes = float(delay_str)
                    scheduled_arrival = row.get(COL_SCHEDULED_ARRIVAL) # Keep as string

                    if not (0 <= hour <= 23):
                        logger.warning(f"Skipping row {line_num}: Invalid hour '{hour_str}'.")
                        skipped_count += 1
                        continue
                    if not math.isfinite(delay_minutes):
                         logger.warning(f"Skipping row {line_num}: Invalid delay value '{delay_str}'.")
                         skipped_count += 1
                         continue

                    # Store processed data
                    processed_row = {
                        COL_ROUTE: route,
                        COL_HOUR: hour,
                        COL_DELAY_MINUTES: delay_minutes,
                        COL_SCHEDULED_ARRIVAL: scheduled_arrival,
                        # Add other columns if needed
                    }
                    BUS_DATA.append(processed_row)
                    processed_count += 1

                except (ValueError, TypeError) as conv_err:
                    logger.warning(
                        f"Skipping row {line_num} due to data conversion error: {conv_err}. Row data: {row}"
                    )
                    skipped_count += 1
                    continue

        logger.info(
            f"Successfully processed {processed_count} records. Skipped {skipped_count} rows."
        )
        if processed_count == 0 and skipped_count > 0:
             logger.error("No valid data records were loaded. Check CSV format and column names.")
             data_load_error = "No valid data records could be loaded from the CSV."
        elif processed_count == 0:
             logger.warning("CSV file loaded, but it appears to be empty or contain no processable data.")
             # Decide if this is an error or just an empty dataset
             # data_load_error = "CSV file is empty or contains no processable data."


    except FileNotFoundError as e:
        data_load_error = f"Error loading data: {e}"
        logger.error(data_load_error)
    except ValueError as e: # Catches missing columns or conversion errors during header check
        data_load_error = f"CSV format or data error: {e}"
        logger.error(data_load_error)
    except Exception as e:
        data_load_error = f"An unexpected error occurred during data loading: {e}"
        logger.exception(data_load_error) # Log the full traceback

# --- Load data when the module is imported (when FastAPI starts) ---
load_bus_data()

# --- API Router ---
router = APIRouter(
    prefix="/api", # Add prefix to all routes in this router
    tags=["Bus Data"] # Group endpoints in API docs
)

# --- Helper Function to Check Data Loading Status ---
def check_data_loaded():
    """Raises HTTPException if data failed to load or is unavailable."""
    if data_load_error:
        # Provide a generic error message to the client for internal errors
        logger.error(f"Data loading check failed: {data_load_error}")
        raise HTTPException(
            status_code=500,
            detail="Internal Server Error: Could not load bus data.",
        )
    if not BUS_DATA:
        # If loading technically succeeded but resulted in no data
        logger.warning("Data check: No bus data available.")
        raise HTTPException(
            status_code=404,
            detail="No bus data available.",
        )

# --- API Endpoints ---

@router.get("/bus-data", response_model=ChartDataResponse)
async def get_bus_data_for_chart():
    """
    Calculates the average scheduled delay for each unique bus route.
    Used to populate the main overview chart.
    """
    check_data_loaded()

    route_stats = defaultdict(lambda: {"sum_delay": 0.0, "count": 0})
    for record in BUS_DATA:
        # Access data using the defined constants
        route_name = record.get(COL_ROUTE)
        delay_minutes = record.get(COL_DELAY_MINUTES) # Should be float

        # We assume data in BUS_DATA is already validated during load
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
        else:
             # This case shouldn't happen with defaultdict logic but good practice
             logger.warning(f"Route '{route}' found with zero count in stats.")


    if not chart_output["routes"]:
        logger.warning("No valid route data found to generate chart output.")
        # Let Pydantic handle the response model validation if empty
        # Or raise: raise HTTPException(status_code=404, detail="No chart data generated.")

    return chart_output


@router.get("/filter-options", response_model=FilterOptionsResponse)
async def get_filter_options():
    """
    Provides unique bus route names available in the dataset.
    Used to populate the filter dropdown on the frontend.
    """
    check_data_loaded()

    unique_routes = set(record.get(COL_ROUTE) for record in BUS_DATA)
    # Filter out potential None or empty strings if they somehow got through loading
    sorted_routes = sorted([route for route in unique_routes if route])

    if not sorted_routes:
        logger.warning("Filter options requested, but no unique routes found.")
        # Let Pydantic handle response if empty
        # Or raise: raise HTTPException(status_code=404, detail="No routes available.")

    return {"routes": sorted_routes}


@router.get("/find-arrival", response_model=ArrivalDataResponse)
async def find_average_delay_for_route_hour(
    route: str = Query(..., description="The bus route name (e.g., 'M15')."),
    hour: int = Query(..., ge=0, le=23, description="The hour of the day (0-23).")
):
    """
    Finds the average scheduled delay for a specific bus route at a specific hour.
    Also returns the first scheduled arrival time encountered for matching records.
    """
    check_data_loaded()
    # Input validation for route format could be added here if needed

    logger.info(f"Searching for route: '{route}', hour: {hour}")

    total_delay = 0.0
    record_count = 0
    first_scheduled_arrival = None

    for record in BUS_DATA:
        # Check if the record matches the requested route and hour
        if (
            record.get(COL_ROUTE) == route
            and record.get(COL_HOUR) == hour
        ):
            # Delay is already validated as float during load
            total_delay += record.get(COL_DELAY_MINUTES)
            record_count += 1
            # Capture the first matching scheduled arrival time found
            if first_scheduled_arrival is None:
                first_scheduled_arrival = record.get(COL_SCHEDULED_ARRIVAL)

    if record_count > 0:
        average_delay = total_delay / record_count
        logger.info(
            f"Found {record_count} records for route '{route}' at hour {hour}. Avg delay: {average_delay:.2f}"
        )
        if first_scheduled_arrival is None:
             logger.warning(f"Data found for route '{route}' hour {hour}, but no scheduled arrival time captured.")

        return {
            "scheduled_arrival": first_scheduled_arrival,
            "average_delay": round(average_delay, 2),
        }
    else:
        logger.info(f"No matching records found for route '{route}' at hour {hour}.")
        # Raise 404 Not Found if no data matches the criteria
        raise HTTPException(
            status_code=404,
            detail=f"No arrival data found for route '{route}' at hour {hour}.",
        )

