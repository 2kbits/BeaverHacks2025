# backend/routers/chart_data.py

import csv
import math
import logging
from pathlib import Path
from collections import defaultdict
from fastapi import APIRouter, HTTPException

# --- Configuration ---
# Get the directory where this script (chart_data.py) is located
CURRENT_DIR = Path(__file__).parent
# Go up one level to the 'backend' directory
BACKEND_DIR = CURRENT_DIR.parent
# Construct the full path to the CSV file
CSV_FILE_PATH = BACKEND_DIR / "busDatabase.csv"

# --- Column Names (IMPORTANT: Adjust these to match your CSV header exactly!) ---
# These are based on your original hardcoded data structure.
# Verify these against the actual headers in busDatabase.csv. Case matters!
ROUTE_COLUMN = "published_line"
DELAY_COLUMN = "scheduled_delay_minutes"
HOUR_COLUMN = "hour_of_day"
SCHEDULED_ARRIVAL_COLUMN = "scheduled_arrival"

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Data Storage ---
# This list will hold our data loaded from the CSV
BUS_DATA = []
data_load_error = None  # Store any error during loading

# --- Data Loading Function ---
def load_bus_data():
    """Loads bus data from the CSV file into the BUS_DATA list."""
    global BUS_DATA, data_load_error  # Allow modification of global variables
    BUS_DATA = [] # Clear previous data if reloading
    data_load_error = None # Reset error status
    try:
        logger.info(f"Attempting to load bus data from: {CSV_FILE_PATH}")
        if not CSV_FILE_PATH.is_file():
            raise FileNotFoundError(f"CSV file not found at {CSV_FILE_PATH}")

        required_columns = {
            ROUTE_COLUMN,
            DELAY_COLUMN,
            HOUR_COLUMN,
            SCHEDULED_ARRIVAL_COLUMN,
        }

        with open(CSV_FILE_PATH, mode="r", encoding="utf-8-sig") as csvfile:
            # Use DictReader for easy access by column name
            reader = csv.DictReader(csvfile)

            # Check if all required columns exist in the header
            if not required_columns.issubset(reader.fieldnames):
                missing = required_columns - set(reader.fieldnames)
                available = reader.fieldnames
                raise ValueError(
                    f"Missing required columns: {missing}. "
                    f"Available columns: {available}"
                )

            line_num = 1 # Start from 1 for header
            for row in reader:
                line_num += 1
                try:
                    # Basic validation and type conversion
                    processed_row = {
                        ROUTE_COLUMN: row.get(ROUTE_COLUMN, "").strip(),
                        SCHEDULED_ARRIVAL_COLUMN: row.get(SCHEDULED_ARRIVAL_COLUMN),
                        # Convert delay to float, handle potential errors
                        DELAY_COLUMN: float(row.get(DELAY_COLUMN, 0.0)),
                        # Convert hour to int, handle potential errors
                        HOUR_COLUMN: int(row.get(HOUR_COLUMN, -1)),
                        # Add other columns if needed, converting types as necessary
                        # e.g., "id": int(row.get("id", 0))
                    }

                    # Add more specific validation if needed (e.g., hour range)
                    if not processed_row[ROUTE_COLUMN]:
                         logger.warning(f"Skipping row {line_num}: Empty route name.")
                         continue # Skip rows with no route name

                    if not (0 <= processed_row[HOUR_COLUMN] <= 23):
                         logger.warning(f"Skipping row {line_num}: Invalid hour '{row.get(HOUR_COLUMN)}'.")
                         continue # Skip rows with invalid hour

                    BUS_DATA.append(processed_row)

                except (ValueError, TypeError) as conv_err:
                    logger.warning(
                        f"Skipping row {line_num} due to data conversion error: {conv_err}. Row data: {row}"
                    )
                    continue # Skip rows with conversion errors

        logger.info(
            f"Successfully loaded {len(BUS_DATA)} records from CSV."
        )

    except FileNotFoundError as e:
        data_load_error = f"Error loading data: {e}"
        logger.error(data_load_error)
    except ValueError as e:
        data_load_error = f"CSV format or data error: {e}"
        logger.error(data_load_error)
    except Exception as e:
        data_load_error = f"An unexpected error occurred during data loading: {e}"
        logger.exception(data_load_error) # Log the full traceback

# --- Load data when the module is imported (when FastAPI starts) ---
load_bus_data()

# --- API Router ---
router = APIRouter()

# --- Helper Function to Check Data Loading Status ---
def check_data_loaded():
    """Raises HTTPException if data failed to load."""
    if data_load_error:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {data_load_error}")
    if not BUS_DATA:
         raise HTTPException(status_code=404, detail="No bus data available.")


# --- API Endpoints (Modified to use BUS_DATA) ---

@router.get("/api/bus-data")
async def get_processed_bus_data():
    """Calculates average delay per route for the chart."""
    check_data_loaded() # Check if data is loaded

    route_stats = defaultdict(lambda: {"sum_delay": 0.0, "count": 0})
    for record in BUS_DATA:
        route_name = record.get(ROUTE_COLUMN)
        # Delay should already be a float from loading
        delay_minutes = record.get(DELAY_COLUMN)

        # Check if data is valid (route exists, delay is a finite number)
        if route_name and isinstance(delay_minutes, float) and math.isfinite(delay_minutes):
            route_stats[route_name]["sum_delay"] += delay_minutes
            route_stats[route_name]["count"] += 1

    chart_output = {"routes": [], "avg_delays": []}
    # Sort routes alphabetically for consistent chart order
    sorted_routes = sorted(route_stats.keys())

    for route in sorted_routes:
        stats = route_stats[route]
        if stats["count"] > 0:
            average_delay = stats["sum_delay"] / stats["count"]
            chart_output["routes"].append(route)
            # Round the average delay for cleaner display
            chart_output["avg_delays"].append(round(average_delay, 2))

    if not chart_output["routes"]:
         logger.warning("No valid route data found to generate chart.")
         # Return empty lists, frontend should handle this
         # Or raise 404: raise HTTPException(status_code=404, detail="No chart data could be generated.")

    return chart_output


@router.get("/api/filter-options")
async def get_filter_options():
    """Provides unique route names for the filter dropdown."""
    check_data_loaded() # Check if data is loaded

    unique_routes = set()
    # Hours are not needed based on filter.js, but kept for potential future use
    # unique_hours = set()

    for record in BUS_DATA:
        route = record.get(ROUTE_COLUMN)
        # hour = record.get(HOUR_COLUMN) # Hour should be int from loading
        if route: # Ensure route is not empty
            unique_routes.add(route)
        # if isinstance(hour, int) and 0 <= hour <= 23:
        #     unique_hours.add(hour)

    sorted_routes = sorted(list(unique_routes))
    # sorted_hours = sorted(list(unique_hours))

    if not sorted_routes:
        logger.warning("Filter options requested, but no unique routes found in loaded data.")
        # Return empty list, frontend should handle this
        # Or raise 404: raise HTTPException(status_code=404, detail="No routes available for filtering.")

    # Frontend filter.js only expects 'routes'
    return {"routes": sorted_routes}


@router.get("/api/find-arrival")
async def find_average_delay(route: str, hour: int):
    """
    Calculates the average delay for a specific route and hour.
    Returns the average delay and the first scheduled arrival time found.
    """
    check_data_loaded() # Check if data is loaded

    # Validate input hour (FastAPI does basic int conversion, but check range)
    if not (0 <= hour <= 23):
        raise HTTPException(
            status_code=400,
            detail="Invalid hour parameter. Hour must be between 0 and 23.",
        )

    logger.info(f"Searching for route: {route}, hour: {hour}")

    total_delay = 0.0
    record_count = 0
    first_scheduled_arrival = None

    for record in BUS_DATA:
        record_route = record.get(ROUTE_COLUMN)
        # Hour should already be an int from loading
        record_hour = record.get(HOUR_COLUMN)
        # Delay should already be a float from loading
        delay_minutes = record.get(DELAY_COLUMN)
        scheduled_arrival = record.get(SCHEDULED_ARRIVAL_COLUMN)

        # Check if the record matches the requested route and hour
        # Also ensure delay is a valid number
        if (
            record_route == route
            and record_hour == hour
            and isinstance(delay_minutes, float) and math.isfinite(delay_minutes)
        ):
            total_delay += delay_minutes
            record_count += 1

            # Capture the first matching scheduled arrival time found
            if first_scheduled_arrival is None:
                first_scheduled_arrival = scheduled_arrival

    if record_count > 0:
        average_delay = total_delay / record_count
        logger.info(
            f"Found {record_count} records for route {route} at hour {hour}. Avg delay: {average_delay:.2f}"
        )
        if first_scheduled_arrival is None:
             logger.warning(f"Data found for route {route} hour {hour}, but no scheduled arrival time captured.")
             # Decide how to handle this - return None, or raise error? Let's return None.

        return {
            "scheduled_arrival": first_scheduled_arrival, # Might be None if not found in matching rows
            "average_delay": round(average_delay, 2),
        }
    else:
        logger.info(f"No matching records found for route {route} at hour {hour}.")
        # Raise 404 Not Found if no data matches the criteria
        raise HTTPException(
            status_code=404,
            detail=f"No arrival data found for route '{route}' at hour {hour}",
        )

