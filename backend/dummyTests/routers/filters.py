# backend/routers/filters.py

import csv
from pathlib import Path
from fastapi import APIRouter, HTTPException
import logging  # Optional: for logging errors

# --- Configuration ---
# Get the directory where this script is located
CURRENT_DIR = Path(__file__).parent
# Go up one level to the 'backend' directory's parent (project root)
# then down into 'backend'
# Adjust this if your script structure is different
CSV_FILE_PATH = CURRENT_DIR.parent / "busDatabase.csv"
# IMPORTANT: Change this to the actual column name in your CSV that holds the route ID/Name
ROUTE_COLUMN_NAME = "PublishedLineName"

# --- Setup Logging (Optional but Recommended) ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Data Loading ---
# We load the data ONCE when the application starts, not on every request
loaded_routes = set()  # Use a set to automatically handle duplicates
data_load_error = None

try:
    logger.info(f"Attempting to load bus data from: {CSV_FILE_PATH}")
    if not CSV_FILE_PATH.is_file():
        raise FileNotFoundError(f"CSV file not found at {CSV_FILE_PATH}")

    with open(CSV_FILE_PATH, mode="r", encoding="utf-8") as csvfile:
        # Use DictReader to access columns by header name
        reader = csv.DictReader(csvfile)

        # Check if the essential column exists in the header
        if ROUTE_COLUMN_NAME not in reader.fieldnames:
            raise ValueError(
                f"Required column '{ROUTE_COLUMN_NAME}' not found in CSV header. "
                f"Available columns: {reader.fieldnames}"
            )

        for row in reader:
            route_name = row.get(ROUTE_COLUMN_NAME)
            if route_name:  # Ensure the route name is not empty
                loaded_routes.add(route_name.strip())  # Add to set, strip whitespace

    # Convert set to a sorted list for consistent dropdown order
    unique_sorted_routes = sorted(list(loaded_routes))
    logger.info(
        f"Successfully loaded {len(unique_sorted_routes)} unique routes."
    )

except FileNotFoundError as e:
    data_load_error = f"Error loading data: {e}"
    logger.error(data_load_error)
    unique_sorted_routes = []  # Ensure it's an empty list on error
except ValueError as e:
    data_load_error = f"CSV format error: {e}"
    logger.error(data_load_error)
    unique_sorted_routes = []
except Exception as e:
    # Catch any other unexpected errors during loading
    data_load_error = f"An unexpected error occurred during data loading: {e}"
    logger.exception(data_load_error) # Log the full traceback
    unique_sorted_routes = []


# --- API Router ---
router = APIRouter()


@router.get("/api/filter-options", tags=["Filters"])
async def get_filter_options():
    """
    Provides filter options, currently just the list of unique bus routes.
    """
    if data_load_error:
        # If loading failed, return an internal server error
        raise HTTPException(status_code=500, detail=data_load_error)

    if not unique_sorted_routes:
        # If loading succeeded but found no routes (or file was empty)
        logger.warning("Filter options requested, but no routes were loaded.")
        # You might return an empty list or a 404, depending on desired behavior
        # Returning empty list is often safer for the frontend
        # raise HTTPException(status_code=404, detail="No route data available.")

    # Return the data in the format expected by the frontend
    return {"routes": unique_sorted_routes}

# You might add other filter-related endpoints here later
