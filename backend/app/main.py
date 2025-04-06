# backend/app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import the router from the bus_data module within the routers package
from .routers import bus_data

# Create the FastAPI application instance
# Added description and contact info (good practice)
app = FastAPI(
    title="NYC Bus Delay API",
    description="API for retrieving and analyzing NYC bus delay data.",
    version="1.0.0",
    contact={
        "name": "Michael",
        # Add your email or website if desired
    },
)

# --- CORS Configuration ---
# Allow frontend origin (adjust port if necessary)
origins = [
    "http://localhost",
    "http://localhost:8080", # Default for python -m http.server
    "http://127.0.0.1:8080",
    # Add any other origins if your frontend is served differently
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET"], # Only GET is needed for this API
    allow_headers=["*"],
)

# --- Include Routers ---
# Include the router from bus_data.py
# All endpoints defined there (/api/bus-data, /api/filter-options, /api/find-arrival)
# will be accessible.
app.include_router(bus_data.router)


# --- Root Endpoint ---
@app.get("/")
async def read_root():
    """Provides a simple welcome message indicating the API is running."""
    return {"message": "Welcome to the NYC Bus Delay API!"}

# --- How to Run ---
# Navigate to the 'backend' directory in your terminal
# Run: uvicorn app.main:app --reload
# The API will be available at http://127.0.0.1:8000
