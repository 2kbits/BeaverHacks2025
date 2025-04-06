from fastapi import APIRouter, HTTPException
from collections import defaultdict
import math

router = APIRouter()

raw_bus_data = [
    {
        "id": 1,
        "bus_id": "MTA NYCT_5511",
        "line": "MTA NYCT_M86-SBS",
        "published_line": "M86-SBS",
        "stop_id": 401929,
        "stop_name": "8 AV/W 86 ST",
        "scheduled_arrival": "2025-04-05 16:10:52",
        "predicted_arrival": "2025-04-05 16:03:05",
        "actual_arrival": "2025-04-05 16:10:48",
        "scheduled_delay_minutes": -0.07,
        "prediction_error_minutes": 7.72,
        "initial_distance": "at stop",
        "date": "2025-04-05",
        "day_of_week": "Saturday",
        "hour_of_day": 16,
        "timestamp": "2025-04-05 16:10:48",
    },
    {
        "id": 2,
        "bus_id": "MTA NYCT_6144",
        "line": "MTA NYCT_M86-SBS",
        "published_line": "M86-SBS",
        "stop_id": 401929,
        "stop_name": "8 AV/W 86 ST",
        "scheduled_arrival": "2025-04-05 15:56:52",
        "predicted_arrival": "2025-04-05 15:54:20",
        "actual_arrival": "2025-04-05 15:57:12",
        "scheduled_delay_minutes": 0.33,
        "prediction_error_minutes": 2.53,
        "initial_distance": "approaching",
        "date": "2025-04-05",
        "day_of_week": "Saturday",
        "hour_of_day": 15,
        "timestamp": "2025-04-05 15:57:12",
    },
    {
        "id": 3,
        "bus_id": "MTA NYCT_4487",
        "line": "MTA NYCT_B63",
        "published_line": "B63",
        "stop_id": 308204,
        "stop_name": "5 AV/9 ST",
        "scheduled_arrival": "2025-04-05 16:08:00",
        "predicted_arrival": "2025-04-05 16:06:29",
        "actual_arrival": "2025-04-05 16:07:15",
        "scheduled_delay_minutes": -0.75,
        "prediction_error_minutes": 0.27,
        "initial_distance": "1 stop away",
        "date": "2025-04-05",
        "day_of_week": "Saturday",
        "hour_of_day": 16,
        "timestamp": "2025-04-05 16:07:15",
    },
    {
        "id": 4,
        "bus_id": "MTA NYCT_6022",
        "line": "MTA NYCT_M4",
        "published_line": "M4",
        "stop_id": 400069,
        "stop_name": "BROADWAY/W 32 ST",
        "scheduled_arrival": "2025-04-05 16:15:00",
        "predicted_arrival": "2025-04-05 16:20:33",
        "actual_arrival": "2025-04-05 16:22:17",
        "scheduled_delay_minutes": 7.28,
        "prediction_error_minutes": 1.73,
        "initial_distance": "< 1 mile",
        "date": "2025-04-05",
        "day_of_week": "Saturday",
        "hour_of_day": 16,
        "timestamp": "2025-04-05 16:22:17",
    },
    {
        "id": 5,
        "bus_id": "MTA NYCT_5813",
        "line": "MTA NYCT_M34-SBS",
        "published_line": "M34-SBS",
        "stop_id": 400069,
        "stop_name": "BROADWAY/W 32 ST",
        "scheduled_arrival": "2025-04-05 16:00:00",
        "predicted_arrival": "2025-04-05 16:04:15",
        "actual_arrival": "2025-04-05 16:05:42",
        "scheduled_delay_minutes": 5.70,
        "prediction_error_minutes": 1.45,
        "initial_distance": "approaching",
        "date": "2025-04-05",
        "day_of_week": "Saturday",
        "hour_of_day": 16,
        "timestamp": "2025-04-05 16:05:42",
    },
    {
        "id": 6,
        "bus_id": "MTA NYCT_7124",
        "line": "MTA NYCT_Q60",
        "published_line": "Q60",
        "stop_id": 502458,
        "stop_name": "QUEENS BLVD/71 AV",
        "scheduled_arrival": "2025-04-05 16:30:00",
        "predicted_arrival": "2025-04-05 16:35:18",
        "actual_arrival": "2025-04-05 16:37:24",
        "scheduled_delay_minutes": 7.40,
        "prediction_error_minutes": 2.10,
        "initial_distance": "2 stops away",
        "date": "2025-04-05",
        "day_of_week": "Saturday",
        "hour_of_day": 16,
        "timestamp": "2025-04-05 16:37:24",
    },
    {
        "id": 7,
        "bus_id": "MTA NYCT_3355",
        "line": "MTA NYCT_B38",
        "published_line": "B38",
        "stop_id": 307220,
        "stop_name": "FLATBUSH AV/ATLANTIC AV",
        "scheduled_arrival": "2025-04-05 16:45:00",
        "predicted_arrival": "2025-04-05 16:42:12",
        "actual_arrival": "2025-04-05 16:41:35",
        "scheduled_delay_minutes": -3.42,
        "prediction_error_minutes": -0.62,
        "initial_distance": "approaching",
        "date": "2025-04-05",
        "day_of_week": "Saturday",
        "hour_of_day": 16,
        "timestamp": "2025-04-05 16:41:35",
    },
]


@router.get("/api/bus-data")
async def get_processed_bus_data():
    route_stats = defaultdict(lambda: {"sum_delay": 0.0, "count": 0})
    for record in raw_bus_data:
        route_name = record.get("published_line")
        delay_minutes = record.get("scheduled_delay_minutes")
        if (
            route_name
            and isinstance(delay_minutes, (int, float))
            and math.isfinite(delay_minutes)
        ):
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
    return chart_output


@router.get("/api/filter-options")
async def get_filter_options():
    unique_routes = set()
    unique_hours = set()
    for record in raw_bus_data:
        route = record.get("published_line")
        hour = record.get("hour_of_day")
        if route:
            unique_routes.add(route)
        if isinstance(hour, int):
            unique_hours.add(hour)
    sorted_routes = sorted(list(unique_routes))
    sorted_hours = sorted(list(unique_hours))
    return {"routes": sorted_routes, "hours": sorted_hours}


@router.get("/api/find-arrival")
async def find_average_delay(route: str, hour: int):
    """
    Calculates the average delay in minutes for a specific bus route at a specific hour.
    Returns the average delay and the first scheduled arrival time found.
    """
    print(f"Searching for route: {route}, hour: {hour}")

    try:
        target_hour = int(hour)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid hour format. Hour must be an integer.",
        )

    total_delay = 0.0
    record_count = 0
    first_scheduled_arrival = None  # Store the first scheduled arrival time

    for record in raw_bus_data:
        record_route = record.get("published_line")
        record_hour = record.get("hour_of_day")
        delay_minutes = record.get("scheduled_delay_minutes")
        scheduled_arrival = record.get("scheduled_arrival")  # Get the
        # scheduled arrival

        if (
            record_route == route
            and isinstance(record_hour, int)
            and record_hour == target_hour
            and isinstance(delay_minutes, (int, float))
        ):
            total_delay += delay_minutes
            record_count += 1

            # Capture the first scheduled arrival time
            if first_scheduled_arrival is None:
                first_scheduled_arrival = scheduled_arrival

    if record_count > 0:
        average_delay = total_delay / record_count
        print(
            f"Found {record_count} records. Average delay: {average_delay}"
        )
        return {
            "scheduled_arrival": first_scheduled_arrival,
            "average_delay": round(average_delay, 2),
        }  # Return the scheduled time
    else:
        print("No matching records found.")
        raise HTTPException(
            status_code=404,
            detail=f"No arrival data found for route {route} at hour {hour}",
        )
