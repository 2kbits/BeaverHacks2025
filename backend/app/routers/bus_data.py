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

# Model for the chart endpoint
class ChartDataResponse(BaseModel):
    routes: List[str] = Field(..., description="List of unique bus route names.")
    avg_delays: List[float] = Field(
        ..., description="List of corresponding average scheduled delays in minutes."
    )

# Model for original filter endpoint (kept for potential use)
class FilterOptionsResponse(BaseModel):
    routes: List[str] = Field(..., description="List of unique bus route names.")

# Model for original filter endpoint (kept for potential use)
class ArrivalDataResponse(BaseModel):
    scheduled_arrival: Optional[str] = Field(
        None, description="First scheduled arrival time found for the criteria (ISO format or similar)."
    )
    average_delay: float = Field(
        ..., description="Average scheduled delay in minutes for the specified route and hour."
    )

# *** MODIFIED StopRouteScheduleInfo model ***
class StopRouteScheduleInfo(BaseModel):
    route: str = Field(..., description="The bus route identifier (published_line).")
    # Changed field name and description to reflect using scheduled delay
    average_scheduled_delay_at_schedule: Optional[float] = Field(
        None, description="Average scheduled delay (in minutes) for all records matching the next_scheduled_arrival time. Null if no data or next arrival found."
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
                    prediction_error_str = row.get(COL_PREDICTION_ERROR)

                    # --- Start Validation ---
                    if not all([stop_name, bus_id, route, scheduled_arrival_str]):
                        skipped_count += 1; continue
                    if hour_str is None or delay_str is None or prediction_error_str is None:
                         skipped_count += 1; continue

                    hour = int(hour_str)
                    delay_minutes = float(delay_str)
                    prediction_error_minutes = float(prediction_error_str)

                    if not (0 <= hour <= 23): skipped_count += 1; continue
                    if not math.isfinite(delay_minutes): skipped_count += 1; continue
                    if not math.isfinite(prediction_error_minutes): skipped_count += 1; continue
                    if len(scheduled_arrival_str) < 16: skipped_count += 1; continue
                    try: datetime.strptime(scheduled_arrival_str, '%Y-%m-%d %H:%M:%S')
                    except (ValueError, TypeError): skipped_count += 1; continue
                    # --- End Validation ---

                    processed_row = {
                        COL_STOP_NAME: stop_name, COL_BUS_ID: bus_id, COL_ROUTE: route,
                        COL_HOUR: hour, COL_DELAY_MINUTES: delay_minutes,
                        COL_SCHEDULED_ARRIVAL: scheduled_arrival_str,
                        COL_PREDICTION_ERROR: prediction_error_minutes
                    }
                    BUS_DATA.append(processed_row)
                    stop_name_set.add(stop_name) # Add valid stop name to set
                    processed_count += 1

                except (ValueError, TypeError) as conv_err:
                    skipped_count += 1; continue

        UNIQUE_STOP_NAMES = sorted(list(stop_name_set))
        logger.info(
            f"Successfully processed {processed_count} records. Skipped {skipped_count} rows. Found {len(UNIQUE_STOP_NAMES)} unique stop names."
        )
        if processed_count == 0:
             logger.error("No valid data records were loaded. Check CSV format/content.")
             if skipped_count > 0: data_load_error = "CSV contains rows, but none could be processed successfully."
             else: data_load_error = "CSV file appears empty or contains no processable data."

    except FileNotFoundError as e:
        data_load_error = f"Error loading data: {e}"; logger.error(data_load_error)
    except ValueError as e:
        data_load_error = f"CSV format or data error: {e}"; logger.error(data_load_error)
    except Exception as e:
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
        raise HTTPException(status_code=500, detail="Internal Server Error: Could not load bus data.")
    if not BUS_DATA:
        logger.warning("Data check: BUS_DATA list is empty.")
        raise HTTPException(status_code=404, detail="No bus data available.")

# --- API Endpoints ---

# Endpoint for the "Average Scheduled Delay per Bus Route" chart
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
        delay_minutes = record.get(COL_DELAY_MINUTES) # Uses scheduled delay
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

    if not chart_output["routes"]: logger.warning("No valid route data found to generate chart output.")
    return chart_output

# Endpoint for populating route filter (if ever needed again)
@router.get("/filter-options", response_model=FilterOptionsResponse)
async def get_filter_options():
    """ Provides unique bus route names available in the dataset. """
    check_data_loaded()
    unique_routes = set(record.get(COL_ROUTE) for record in BUS_DATA if record.get(COL_ROUTE))
    sorted_routes = sorted(list(unique_routes))
    if not sorted_routes: logger.warning("Filter options requested, but no unique routes found.")
    return {"routes": sorted_routes}

# Original endpoint for finding delay by route/hour (kept for reference)
@router.get("/find-arrival", response_model=ArrivalDataResponse)
async def find_average_delay_for_route_hour(
    route: str = Query(..., description="The bus route name (e.g., 'M15')."),
    hour: int = Query(..., ge=0, le=23, description="The hour of the day (0-23).")
):
    """ (Original endpoint) Finds the average scheduled delay for a specific bus route/hour. """
    check_data_loaded()
    logger.info(f"Original endpoint search for route: '{route}', hour: {hour}")
    total_delay = 0.0; record_count = 0; first_scheduled_arrival = None
    for record in BUS_DATA:
        if record.get(COL_ROUTE) == route and record.get(COL_HOUR) == hour:
            delay = record.get(COL_DELAY_MINUTES)
            total_delay += delay; record_count += 1
            if first_scheduled_arrival is None: first_scheduled_arrival = record.get(COL_SCHEDULED_ARRIVAL)
    if record_count > 0:
        average_delay = total_delay / record_count
        logger.info(f"Found {record_count} records for route '{route}' at hour {hour}. Avg delay: {average_delay:.2f}")
        return {"scheduled_arrival": first_scheduled_arrival, "average_delay": round(average_delay, 2)}
    else:
        logger.info(f"No matching records found for route '{route}' at hour {hour}.")
        raise HTTPException(status_code=404, detail=f"No arrival data found for route '{route}' at hour {hour}")

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
@router.get("/stop-schedule", response_model=StopScheduleResponse)
async def get_schedule_for_stop(
    stop_name: str = Query(..., min_length=1, description="The exact name of the bus stop."),
    hour: int = Query(..., ge=0, le=23, description="Requested hour (0-23)."),
    minute: int = Query(..., ge=0, le=59, description="Requested minute (0-59).")
):
    """
    For a given stop name and time (hour:minute), finds the next scheduled
    bus and the average SCHEDULED DELAY associated with that specific
    scheduled arrival time for each route serving the stop.
    """
    check_data_loaded()
    logger.info(f"Request received for stop: '{stop_name}', time: {hour:02d}:{minute:02d}")

    stop_specific_data = [rec for rec in BUS_DATA if rec.get(COL_STOP_NAME) == stop_name]
    if not stop_specific_data:
        raise HTTPException(status_code=404, detail=f"No data found for stop name: '{stop_name}'")

    routes_data = defaultdict(list)
    for record in stop_specific_data:
        route = record.get(COL_ROUTE)
        if route: routes_data[route].append(record)
    if not routes_data:
         return StopScheduleResponse(stop_name=stop_name, requested_time=f"{hour:02d}:{minute:02d}", routes_at_stop=[])

    results_for_routes: List[StopRouteScheduleInfo] = []
    user_time_obj = time(hour, minute)

    for route, records in routes_data.items():
        logger.debug(f"Processing route: {route} for stop '{stop_name}'")
        next_bus: Optional[Dict] = None
        valid_records_with_dt = []
        for record in records:
             try: dt = datetime.strptime(record[COL_SCHEDULED_ARRIVAL], '%Y-%m-%d %H:%M:%S'); valid_records_with_dt.append((dt, record))
             except (ValueError, TypeError): continue
        valid_records_with_dt.sort(key=lambda item: item[0])
        for scheduled_dt, record in valid_records_with_dt:
            if scheduled_dt.time() >= user_time_obj: next_bus = record; break

        # *** MODIFIED CALCULATION: Average SCHEDULED DELAY for the Found Schedule ***
        avg_scheduled_delay: Optional[float] = None
        if next_bus:
            target_schedule_str = next_bus.get(COL_SCHEDULED_ARRIVAL)
            total_scheduled_delay = 0.0
            delay_count = 0
            # Iterate through ALL records for this route/stop again to find matches
            for record in records:
                # Find records matching the exact scheduled arrival time string
                if record.get(COL_SCHEDULED_ARRIVAL) == target_schedule_str:
                    # Use the SCHEDULED DELAY column
                    scheduled_delay = record.get(COL_DELAY_MINUTES)
                    if isinstance(scheduled_delay, float) and math.isfinite(scheduled_delay):
                        total_scheduled_delay += scheduled_delay
                        delay_count += 1

            if delay_count > 0:
                avg_scheduled_delay = round(total_scheduled_delay / delay_count, 2)
                logger.debug(f"Avg scheduled delay for {route} @ {target_schedule_str}: {avg_scheduled_delay} ({delay_count} records)")
            else:
                 logger.warning(f"Found next bus for {route} @ {target_schedule_str}, but no valid scheduled delays to average.")
        else:
            logger.debug(f"No next bus found for route {route}, cannot calculate scheduled delay.")


        # --- Prepare result for this route ---
        results_for_routes.append(StopRouteScheduleInfo(
            route=route,
            # Use the new field name and the calculated scheduled delay average
            average_scheduled_delay_at_schedule=avg_scheduled_delay,
            next_bus_id=next_bus.get(COL_BUS_ID) if next_bus else None,
            next_scheduled_arrival=next_bus.get(COL_SCHEDULED_ARRIVAL) if next_bus else None,
        ))

    results_for_routes.sort(key=lambda r: r.route)
    return StopScheduleResponse(stop_name=stop_name, requested_time=f"{hour:02d}:{minute:02d}", routes_at_stop=results_for_routes)

