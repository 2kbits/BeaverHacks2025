# backend/app/routers/chart_data.py

from fastapi import APIRouter
from collections import defaultdict
import math # To check for valid numbers

# Create a router object. We can add API endpoints to this.
router = APIRouter()

# Define the raw bus data (using the sample you provided)
raw_bus_data = [
  {
    "id": 1, "bus_id": "MTA NYCT_5511", "line": "MTA NYCT_M86-SBS", "published_line": "M86-SBS",
    "stop_id": 401929, "stop_name": "8 AV/W 86 ST", "scheduled_arrival": "2025-04-05 16:10:52",
    "predicted_arrival": "2025-04-05 16:03:05", "actual_arrival": "2025-04-05 16:10:48",
    "scheduled_delay_minutes": -0.07, "prediction_error_minutes": 7.72, "initial_distance": "at stop",
    "date": "2025-04-05", "day_of_week": "Saturday", "hour_of_day": 16, "timestamp": "2025-04-05 16:10:48"
  },
  {
    "id": 2, "bus_id": "MTA NYCT_6144", "line": "MTA NYCT_M86-SBS", "published_line": "M86-SBS",
    "stop_id": 401929, "stop_name": "8 AV/W 86 ST", "scheduled_arrival": "2025-04-05 15:56:52",
    "predicted_arrival": "2025-04-05 15:54:20", "actual_arrival": "2025-04-05 15:57:12",
    "scheduled_delay_minutes": 0.33, "prediction_error_minutes": 2.53, "initial_distance": "approaching",
    "date": "2025-04-05", "day_of_week": "Saturday", "hour_of_day": 15, "timestamp": "2025-04-05 15:57:12"
  },
  {
    "id": 3, "bus_id": "MTA NYCT_4487", "line": "MTA NYCT_B63", "published_line": "B63",
    "stop_id": 308204, "stop_name": "5 AV/9 ST", "scheduled_arrival": "2025-04-05 16:08:00",
    "predicted_arrival": "2025-04-05 16:06:29", "actual_arrival": "2025-04-05 16:07:15",
    "scheduled_delay_minutes": -0.75, "prediction_error_minutes": 0.27, "initial_distance": "1 stop away",
    "date": "2025-04-05", "day_of_week": "Saturday", "hour_of_day": 16, "timestamp": "2025-04-05 16:07:15"
  },
  {
    "id": 4, "bus_id": "MTA NYCT_6022", "line": "MTA NYCT_M4", "published_line": "M4",
    "stop_id": 400069, "stop_name": "BROADWAY/W 32 ST", "scheduled_arrival": "2025-04-05 16:15:00",
    "predicted_arrival": "2025-04-05 16:20:33", "actual_arrival": "2025-04-05 16:22:17",
    "scheduled_delay_minutes": 7.28, "prediction_error_minutes": 1.73, "initial_distance": "< 1 mile",
    "date": "2025-04-05", "day_of_week": "Saturday", "hour_of_day": 16, "timestamp": "2025-04-05 16:22:17"
  },
  {
    "id": 5, "bus_id": "MTA NYCT_5813", "line": "MTA NYCT_M34-SBS", "published_line": "M34-SBS",
    "stop_id": 400069, "stop_name": "BROADWAY/W 32 ST", "scheduled_arrival": "2025-04-05 16:00:00",
    "predicted_arrival": "2025-04-05 16:04:15", "actual_arrival": "2025-04-05 16:05:42",
    "scheduled_delay_minutes": 5.70, "prediction_error_minutes": 1.45, "initial_distance": "approaching",
    "date": "2025-04-05", "day_of_week": "Saturday", "hour_of_day": 16, "timestamp": "2025-04-05 16:05:42"
  },
  {
    "id": 6, "bus_id": "MTA NYCT_7124", "line": "MTA NYCT_Q60", "published_line": "Q60",
    "stop_id": 502458, "stop_name": "QUEENS BLVD/71 AV", "scheduled_arrival": "2025-04-05 16:30:00",
    "predicted_arrival": "2025-04-05 16:35:18", "actual_arrival": "2025-04-05 16:37:24",
    "scheduled_delay_minutes": 7.40, "prediction_error_minutes": 2.10, "initial_distance": "2 stops away",
    "date": "2025-04-05", "day_of_week": "Saturday", "hour_of_day": 16, "timestamp": "2025-04-05 16:37:24"
  },
  {
    "id": 7, "bus_id": "MTA NYCT_3355", "line": "MTA NYCT_B38", "published_line": "B38",
    "stop_id": 307220, "stop_name": "FLATBUSH AV/ATLANTIC AV", "scheduled_arrival": "2025-04-05 16:45:00",
    "predicted_arrival": "2025-04-05 16:42:12", "actual_arrival": "2025-04-05 16:41:35",
    "scheduled_delay_minutes": -3.42, "prediction_error_minutes": -0.62, "initial_distance": "approaching",
    "date": "2025-04-05", "day_of_week": "Saturday", "hour_of_day": 16, "timestamp": "2025-04-05 16:41:35"
  }
  # --- Add more data records here if needed ---
]


@router.get("/api/bus-data") # Ensure this path matches the frontend fetch URL
async def get_processed_bus_data():
    """
    Processes raw bus data to calculate average scheduled delay per route.
    Returns data formatted for an ECharts bar chart.
    """
    # --- Step 1: Aggregate data ---
    route_stats = defaultdict(lambda: {"sum_delay": 0.0, "count": 0})

    for record in raw_bus_data:
        route_name = record.get("published_line")
        delay_minutes = record.get("scheduled_delay_minutes")

        # Basic validation
        if route_name and isinstance(delay_minutes, (int, float)) and math.isfinite(delay_minutes):
            route_stats[route_name]["sum_delay"] += delay_minutes
            route_stats[route_name]["count"] += 1

    # --- Step 2: Format the output ---
    chart_output = {"routes": [], "avg_delays": []}
    sorted_routes = sorted(route_stats.keys())

    for route in sorted_routes:
        stats = route_stats[route]
        if stats["count"] > 0:
            average_delay = stats["sum_delay"] / stats["count"]
            chart_output["routes"].append(route)
            chart_output["avg_delays"].append(round(average_delay, 2))

    return chart_output
