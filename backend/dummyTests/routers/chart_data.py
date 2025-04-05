from fastapi import APIRouter

# Create a router object. We can add API endpoints to this.
router = APIRouter()

# Define the dummy data (similar structure to what ECharts expects)
dummy_chart_data = {
    "categories": [
        "Mon",
        "Tue",
        "Wed",
        "Thu",
        "Fri",
        "Sat",
        "Sun",
    ],  # Corresponds to xAxis.data
    "values": [
        120,
        10,
        150,
        80,
        70,
        110,
        130,
    ],  # Corresponds to series[0].data
}


# Define an API endpoint using a "path operation decorator"
# @router.get tells FastAPI that the function below handles GET requests
# to the path specified ("/api/chart-data" relative to where this router is mounted)
@router.get("/api/chart-data")
async def get_chart_data():
    """
    Provides dummy data for a simple bar chart.
    """
    # FastAPI automatically converts Python dicts to JSON responses
    return dummy_chart_data
