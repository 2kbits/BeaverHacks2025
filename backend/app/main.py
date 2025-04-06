# backend/app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers
from .routers import bus_data
from .routers import prediction # <-- ADD THIS IMPORT

# Create the FastAPI application instance
app = FastAPI(
    title="NYC Bus Delay API",
    description="API for retrieving, analyzing, and predicting NYC bus delay data.", # <-- Updated description
    version="1.0.0",
    contact={
        "name": "Michael",
    },
)

# --- CORS Configuration ---
origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# --- Include Routers ---
app.include_router(bus_data.router)
app.include_router(prediction.router) # <-- ADD THIS LINE

# --- Root Endpoint ---
@app.get("/")
async def read_root():
    """Provides a simple welcome message indicating the API is running."""
    return {"message": "Welcome to the NYC Bus Delay API!"}

# --- How to Run ---
# Navigate to the 'backend' directory
# Run: uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
