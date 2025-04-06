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
COL_DELAY_MINUTES = "scheduled_delay_minutes" # Used for chart AND now for filter result
COL_HOUR = "hour_of_day"
COL_SCHEDULED_ARRIVAL = "scheduled_arrival"
COL_PREDICTION_ERROR = "prediction_error_minutes" # Still loaded if needed elsewhere

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

# Model for the stop delay chart endpoint
class StopDelayChartDataResponse(BaseModel):
    stop_names: List[str] = Field(..., description="List of unique bus stop names.")
    avg_delays: List[float] = Field(
        ..., description="List of corresponding average scheduled delays in minutes for each stop."
    )

# Model for StopRouteScheduleInfo (used in /stop-schedule)
class StopRouteScheduleInfo(BaseModel):
    route: str = Field(..., description="The bus route identifier (published_line).")
    average_scheduled_delay_at_schedule: Optional[float] = Field(
        None, description="Average scheduled delay (in minutes) for all records matching the next_scheduled_arrival time. Null if no data or next arrival found."
    )
    next_bus_id: Optional[str] = Field(
        None, description="The bus_id of the next scheduled bus at or after the requested time. Null if none found."
    )
    next_scheduled_arrival: Optional[str] = Field(
        None, description="The scheduled arrival time string for the next bus. Null if none found."
    )

# Model for StopScheduleResponse (used in /stop-schedule)
class StopScheduleResponse(BaseModel):
    stop_name: str = Field(..., description="The requested stop name.")
    requested_time: str = Field(..., description="The requested time in HH:MM format.")
    routes_at_stop: List[StopRouteScheduleInfo] = Field(
        ..., description="Schedule information for each unique route serving this stop."
    )

# Model for the stop names endpoint
class StopNamesResponse(BaseModel):
    stop_names: List[str] = Field(..., description="List of unique stop names found in the data.")


# --- Data Loading Function ---
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

        # Define all columns expected in the CSV
        required_columns = {
            COL_STOP_NAME, COL_BUS_ID, COL_ROUTE,
            COL_DELAY_MINUTES, COL_HOUR, COL_SCHEDULED_ARRIVAL,
            COL_PREDICTION_ERROR
        }
        # Add any other columns from your CSV header list if needed for other endpoints

        with open(CSV_FILE_PATH, mode="r", encoding="utf-8-sig") as csvfile:
            reader = csv.DictReader(csvfile)
            if not reader.fieldnames:
                 raise ValueError("CSV file appears to be empty or has no header row.")
            # Check if ALL required columns are present
            if not required_columns.issubset(reader.fieldnames):
                missing = required_columns - set(reader.fieldnames)
                available = list(reader.fieldnames)
                raise ValueError(
                    f"Missing required columns: {missing}. Available columns: {available}"
                )

            for i, row in enumerate(reader):
                line_num = i + 2 # For potential error reporting
                try:
                    # Extract required fields, handling potential missing keys gracefully
                    stop_name = row.get(COL_STOP_NAME, "").strip()
                    bus_id = row.get(COL_BUS_ID, "").strip()
                    route = row.get(COL_ROUTE, "").strip()
                    hour_str = row.get(COL_HOUR)
                    delay_str = row.get(COL_DELAY_MINUTES)
                    scheduled_arrival_str = row.get(COL_SCHEDULED_ARRIVAL)
                    prediction_error_str = row.get(COL_PREDICTION_ERROR) # Keep loading if needed elsewhere

                    # --- Start Basic Validation ---
                    if not all([stop_name, bus_id, route, scheduled_arrival_str]):
                        # logger.debug(f"Skipping row {line_num}: Missing essential string data.")
                        skipped_count += 1; continue
                    if hour_str is None or delay_str is None or prediction_error_str is None:
                        # logger.debug(f"Skipping row {line_num}: Missing numeric/time string data.")
                         skipped_count += 1; continue
                    # --- End Basic Validation ---

                    # --- Start Conversion and Detailed Validation ---
                    try:
                        hour = int(hour_str)
                        delay_minutes = float(delay_str)
                        prediction_error_minutes = float(prediction_error_str) # Keep converting if needed

                        if not (0 <= hour <= 23):
                            # logger.debug(f"Skipping row {line_num}: Invalid hour value '{hour_str}'.")
                            skipped_count += 1; continue
                        if not math.isfinite(delay_minutes):
                            # logger.debug(f"Skipping row {line_num}: Non-finite delay value '{delay_str}'.")
                            skipped_count += 1; continue
                        if not math.isfinite(prediction_error_minutes): # Keep validating if needed
                            # logger.debug(f"Skipping row {line_num}: Non-finite prediction error value '{prediction_error_str}'.")
                            skipped_count += 1; continue

                        if len(scheduled_arrival_str) < 16: # Basic check for 'YYYY-MM-DD HH:MM'
                             # logger.debug(f"Skipping row {line_num}: Invalid scheduled arrival format '{scheduled_arrival_str}'.")
                             skipped_count += 1; continue
                        datetime.strptime(scheduled_arrival_str, '%Y-%m-%d %H:%M:%S')

                    except (ValueError, TypeError) as conv_err:
                        # logger.debug(f"Skipping row {line_num}: Conversion error - {conv_err}. Values: hour='{hour_str}', delay='{delay_str}', arrival='{scheduled_arrival_str}'.")
                        skipped_count += 1; continue
                    # --- End Conversion and Detailed Validation ---

                    processed_row = {
                        COL_STOP_NAME: stop_name,
                        COL_BUS_ID: bus_id,
                        COL_ROUTE: route,
                        COL_HOUR: hour,
                        COL_DELAY_MINUTES: delay_minutes,
                        COL_SCHEDULED_ARRIVAL: scheduled_arrival_str,
                        COL_PREDICTION_ERROR: prediction_error_minutes # Include if needed elsewhere
                    }
                    BUS_DATA.append(processed_row)
                    stop_name_set.add(stop_name) # Add valid stop name to set
                    processed_count += 1

                except Exception as inner_e: # Catch unexpected errors within the loop for a specific row
                    logger.warning(f"Skipping row {line_num} due to unexpected error: {inner_e}")
                    skipped_count += 1; continue

        UNIQUE_STOP_NAMES = sorted(list(stop_name_set))
        logger.info(
            f"Successfully processed {processed_count} records. Skipped {skipped_count} rows due to validation/errors. Found {len(UNIQUE_STOP_NAMES)} unique stop names."
        )
        if processed_count == 0 and skipped_count > 0:
             data_load_error = "CSV contains rows, but none could be processed successfully due to data format or validation issues."
             logger.error(data_load_error)
        elif processed_count == 0:
             data_load_error = "CSV file appears empty or contains no processable data matching requirements."
             logger.error(data_load_error)

    except FileNotFoundError as e:
        data_load_error = f"Error loading data: {e}"; logger.error(data_load_error)
    except ValueError as e: # Catches header issues or empty file from DictReader checks
        data_load_error = f"CSV format or data error: {e}"; logger.error(data_load_error)
    except Exception as e: # Catch broader exceptions during file open or initial read
        data_load_error = f"An unexpected error occurred during data loading: {e}"; logger.exception(data_load_error)


# --- Load data when the module is imported ---
load_bus_data()

# --- API Router ---
router = APIRouter(prefix="/api", tags=["Bus Data"])

# --- Helper Function to Check Data Loading Status ---
def check_data_loaded():
    """Raises HTTPException if data failed to load or is unavailable."""
    if data_load_error:
        logger.error(f"Data loading check failed: {data_load_error}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: Could not load bus data. Reason: {data_load_error}")
    if not BUS_DATA:
        logger.warning("Data check: BUS_DATA list is empty.")
        raise HTTPException(status_code=503, detail="Service Unavailable: No bus data has been loaded.")

# --- API Endpoints ---

# Endpoint: Average Scheduled Delay per STOP NAME
@router.get("/bus-data", response_model=StopDelayChartDataResponse)
async def get_stop_delay_data_for_chart():
    """
    Calculates the average scheduled delay for each unique bus **stop** across all data.
    Used to populate an overview chart showing average delays per stop.
    """
    check_data_loaded()
    stop_stats = defaultdict(lambda: {"sum_delay": 0.0, "count": 0})

    for record in BUS_DATA:
        stop_name = record.get(COL_STOP_NAME)
        delay_minutes = record.get(COL_DELAY_MINUTES)

        if stop_name and isinstance(delay_minutes, float) and math.isfinite(delay_minutes):
            stop_stats[stop_name]["sum_delay"] += delay_minutes
            stop_stats[stop_name]["count"] += 1

    chart_output = {"stop_names": [], "avg_delays": []}
    sorted_stop_names = sorted(stop_stats.keys())

    for stop in sorted_stop_names:
        stats = stop_stats[stop]
        if stats["count"] > 0:
            average_delay = stats["sum_delay"] / stats["count"]
            chart_output["stop_names"].append(stop)
            chart_output["avg_delays"].append(round(average_delay, 2))

    if not chart_output["stop_names"]:
        logger.warning("No valid stop data with delays found to generate chart output.")

    logger.info(f"Generated average delay data for {len(chart_output['stop_names'])} stops.")
    return chart_output

# Endpoint for populating stop name filter dropdown
@router.get("/stop-names", response_model=StopNamesResponse)
async def get_stop_names():
    """ Provides a sorted list of unique stop names found in the data. """
    check_data_loaded()
    if not UNIQUE_STOP_NAMES:
         logger.warning("Stop names requested, but the UNIQUE_STOP_NAMES list is empty.")
         return {"stop_names": []}
    return {"stop_names": UNIQUE_STOP_NAMES}

# Endpoint for the filter page (calculates avg SCHEDULED DELAY for next arrival)
# Endpoint for the filter page (REVISED LOGIC)
@router.get("/stop-schedule", response_model=StopScheduleResponse)
async def get_schedule_for_stop(
    stop_name: str = Query(..., min_length=1, description="The exact name of the bus stop."),
    hour: int = Query(..., ge=0, le=23, description="Requested hour (0-23)."),
    minute: int = Query(..., ge=0, le=59, description="Requested minute (0-59).")
):
    """
    For a given stop name and time (hour:minute), finds the next scheduled
    bus occurring at or after that time on any day in the dataset,
    and the average SCHEDULED DELAY associated with that specific
    scheduled arrival time for each route serving the stop.
    """
    check_data_loaded()
    logger.info(f"Request received for stop: '{stop_name}', time: {hour:02d}:{minute:02d}")

    # Filter data for the specific stop first for efficiency
    stop_specific_data = [rec for rec in BUS_DATA if rec.get(COL_STOP_NAME) == stop_name]
    if not stop_specific_data:
        logger.warning(f"No data found for stop name: '{stop_name}'")
        raise HTTPException(status_code=404, detail=f"No data found for stop name: '{stop_name}'")

    # Group remaining data by route
    routes_data = defaultdict(list)
    for record in stop_specific_data:
        route = record.get(COL_ROUTE)
        if route: routes_data[route].append(record) # Store the whole record

    if not routes_data:
         logger.warning(f"Data found for stop '{stop_name}', but no valid routes associated.")
         return StopScheduleResponse(stop_name=stop_name, requested_time=f"{hour:02d}:{minute:02d}", routes_at_stop=[])

    results_for_routes: List[StopRouteScheduleInfo] = []
    user_time_obj = time(hour, minute) # The time the user is interested in

    # Process each route serving this stop
    for route, all_records_for_route in routes_data.items():
        # logger.debug(f"Processing route: {route} for stop '{stop_name}'")

        potential_next_arrivals = []
        # 1. Parse datetimes and filter by user's requested TIME
        for record in all_records_for_route:
            scheduled_arrival_str = record.get(COL_SCHEDULED_ARRIVAL)
            if not scheduled_arrival_str: continue
            try:
                scheduled_dt = datetime.strptime(scheduled_arrival_str, '%Y-%m-%d %H:%M:%S')
                # Keep only records where the TIME part is >= user's requested time
                if scheduled_dt.time() >= user_time_obj:
                    potential_next_arrivals.append((scheduled_dt, record)) # Store tuple (datetime, record_dict)
            except (ValueError, TypeError):
                # logger.debug(f"Could not parse datetime for record on route {route}: {scheduled_arrival_str}")
                continue # Skip records with invalid datetime format

        # 2. Sort the filtered list by FULL DATETIME to find the earliest one
        potential_next_arrivals.sort(key=lambda item: item[0])

        # 3. Select the first one as the next bus (if any exist)
        next_bus_record: Optional[Dict] = None
        if potential_next_arrivals:
            # The first item in the sorted list is the next arrival at/after the requested time
            _ , next_bus_record = potential_next_arrivals[0]
            # logger.debug(f"Next bus found for route {route}: ID {next_bus_record.get(COL_BUS_ID)} scheduled at {next_bus_record.get(COL_SCHEDULED_ARRIVAL)}")
        else:
            # logger.debug(f"No scheduled arrivals found for route {route} at or after {user_time_obj.strftime('%H:%M')}")
            pass # next_bus_record remains None

        # 4. Calculate Average SCHEDULED DELAY for the Found Schedule Time
        avg_scheduled_delay: Optional[float] = None
        if next_bus_record:
            # Get the exact scheduled arrival string of the *found* next bus
            target_schedule_str = next_bus_record.get(COL_SCHEDULED_ARRIVAL)
            total_scheduled_delay = 0.0
            delay_count = 0

            # Iterate through ALL records for this route/stop again to find matches for the *exact* schedule time string
            # This averages delays for all observations of a bus scheduled at this specific time (e.g., same scheduled run on different days)
            for record in all_records_for_route: # Use the already filtered list for this route/stop
                if record.get(COL_SCHEDULED_ARRIVAL) == target_schedule_str:
                    scheduled_delay = record.get(COL_DELAY_MINUTES)
                    if isinstance(scheduled_delay, float) and math.isfinite(scheduled_delay):
                        total_scheduled_delay += scheduled_delay
                        delay_count += 1
                    # else: logger.debug(f"Record matching schedule {target_schedule_str} for route {route} has invalid delay: {scheduled_delay}")

            if delay_count > 0:
                avg_scheduled_delay = round(total_scheduled_delay / delay_count, 2)
                # logger.debug(f"Avg scheduled delay for {route} @ {target_schedule_str}: {avg_scheduled_delay} ({delay_count} records)")
            else:
                 # This case might happen if the 'next_bus_record' itself had an invalid delay value, or no other records matched exactly
                 logger.warning(f"Found next bus for {route} @ {target_schedule_str}, but no valid scheduled delays found matching this exact time to average.")
        # else: # No next bus was found, avg_scheduled_delay remains None
            # logger.debug(f"No next bus found for route {route}, cannot calculate scheduled delay.")

        # --- Prepare result for this route ---
        results_for_routes.append(StopRouteScheduleInfo(
            route=route,
            average_scheduled_delay_at_schedule=avg_scheduled_delay, # Use the calculated average
            next_bus_id=next_bus_record.get(COL_BUS_ID) if next_bus_record else None,
            next_scheduled_arrival=next_bus_record.get(COL_SCHEDULED_ARRIVAL) if next_bus_record else None,
        ))

    # Sort the final list of routes alphabetically for consistent frontend display
    results_for_routes.sort(key=lambda r: r.route)
    logger.info(f"Returning schedule info for {len(results_for_routes)} routes at stop '{stop_name}'.")
    return StopScheduleResponse(stop_name=stop_name, requested_time=f"{hour:02d}:{minute:02d}", routes_at_stop=results_for_routes)

# --- (End of file) ---