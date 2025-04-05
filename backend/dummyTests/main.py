from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import the router we created from the routers module
from .routers import chart_data

# Create the FastAPI application instance
app = FastAPI(title="ECharts Data API", version="0.1.0")

# --- CORS Configuration ---
# This is important because your frontend (e.g., http://localhost:8080)
# will be running on a different "origin" (domain/port) than your backend
# (e.g., http://localhost:8000). Browsers block such requests by default
# for security reasons unless the server explicitly allows them via CORS headers.

# List of origins that are allowed to make requests to this backend.
# You might want to restrict this more in production.
# Using "*" allows all origins, which is convenient for local development.
origins = [
    "http://localhost", # Base domain if needed
    "http://localhost:8080", # Default for python -m http.server
    "http://127.0.0.1:8080", # Alternative for python -m http.server
    # Add the origin where your frontend is served if it's different
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, # Allow specific origins
    allow_credentials=True, # Allow cookies if needed later
    allow_methods=["*"], # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"], # Allow all headers
)

# --- Include Routers ---
# Include the router from chart_data.py.
# All endpoints defined in that router (like /api/chart-data)
# will now be accessible through the main 'app'.
# You could add a prefix here like prefix="/v1" if you wanted all
# routes in chart_data.py to start with /v1/api/chart-data
app.include_router(chart_data.router)


# --- Root Endpoint (Optional) ---
# A simple endpoint at the root path ("/") just to check if the API is running
@app.get("/")
async def read_root():
    return {"message": "Welcome to the ECharts Data API!"}

# Note: You don't run the app from this file directly using 'python app/main.py'.
# Instead, you use an ASGI server like Uvicorn.
