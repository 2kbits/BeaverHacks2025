# NYC Bus Delay Analysis Project

This project provides a web interface to visualize and filter NYC bus delay data. It consists of a Python FastAPI backend and a plain HTML/CSS/JS frontend.

## Project Structure

-   `backend/`: Contains the FastAPI application.
    -   `app/`: Core application code (main setup, routers).
    -   `data/`: Holds the raw data files (e.g., `busDatabase.csv`).
-   `frontend/`: Contains the static web files (HTML, CSS, JS, images).
-   `requirements.txt`: Python dependencies for the backend.
-   `README.md`: This file.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd <your-repo-directory>
    ```

2.  **Backend Setup:**
    -   Navigate to the `backend` directory: `cd backend`
    -   (Recommended) Create and activate a virtual environment:
        ```bash
        python -m venv venv
        source venv/bin/activate # On Windows use `venv\Scripts\activate`
        ```
    -   Install Python dependencies:
        ```bash
        pip install -r requirements.txt
        ```
    -   Place your `busDatabase.csv` file inside the `backend/data/` directory.
    -   **Verify Column Names:** Ensure the column names defined as constants at the top of `backend/app/routers/bus_data.py` (e.g., `COL_ROUTE`, `COL_DELAY_MINUTES`) exactly match the headers in your `busDatabase.csv`.

3.  **Frontend Setup:**
    -   No specific build steps required for this simple frontend.

## Running the Application

1.  **Start the Backend Server:**
    -   Make sure you are in the `backend` directory with your virtual environment activated.
    -   Run the Uvicorn server:
        ```bash
        uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
        ```
    -   The API should be running at `http://127.0.0.1:8000`. You can access the auto-generated documentation at `http://127.0.0.1:8000/docs`.

2.  **Serve the Frontend:**
    -   Navigate to the `frontend` directory: `cd ../frontend`
    -   Start a simple HTTP server (Python's built-in one works well for development):
        ```bash
        python -m http.server 8080
        ```
        (If port 8080 is taken, use another port like 8081 and ensure it's listed in the `origins` in `backend/app/main.py`).
    -   Open your web browser and go to `http://127.0.0.1:8080`.

## Usage

-   The homepage (`index.html`) provides links to the chart and filter pages.
-   The "Overall Chart" page (`chart.html`) displays the average delay per bus route.
-   The "Bus Delays" page (`filter.html`) allows you to select a route and hour to see the specific average delay and scheduled arrival time.

