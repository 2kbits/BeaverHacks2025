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

## File Descriptions

Here's a breakdown of the important files and directories in this project:

*   `README.md`:
    *   This file, providing information about the project, setup, and file structure.

*   `requirements.txt`:
    *   Lists the Python dependencies required for the backend. Install them using `pip install -r requirements.txt`.

### Backend (`backend/`)

*   `backend/app/main.py`:
    *   The main entry point for the FastAPI backend application.
    *   Initializes the FastAPI app instance.
    *   Configures CORS (Cross-Origin Resource Sharing) middleware to allow the frontend to communicate with the API.
    *   Includes the API routers defined in the `routers` directory.
    *   Defines a root endpoint (`/`) for basic API health check.

*   `backend/app/routers/bus_data.py`:
    *   Contains the core API logic using FastAPI's `APIRouter`.
    *   Defines Pydantic models for request validation and response structuring.
    *   Includes the `load_bus_data` function to read and preprocess data from the CSV file upon startup.
    *   Defines API endpoints:
        *   `/api/bus-data`: Calculates and returns average scheduled delays per stop name for the overview chart.
        *   `/api/stop-names`: Returns a list of unique bus stop names for the filter dropdown.
        *   `/api/stop-schedule`: Finds upcoming bus schedules and their average scheduled delays for a specific stop and time based on user input.
        *   *(Note: Contains potentially unused endpoints `/api/filter-options` and `/api/find-arrival` from previous iterations)*.

*   `backend/data/busDatabase.csv`:
    *   The primary data source for the application.
    *   Contains NYC bus data records, including stop names, routes, scheduled arrival times, and delays.

*   `backend/data/bus_arrival_data.db`:
    *   *(Potentially unused)* An SQLite database file. It does not appear to be actively used by the current backend code (`bus_data.py`).

### Frontend (`frontend/`)

*   `frontend/index.html`:
    *   The main landing page for the application.
    *   Displays a welcome message and provides navigation links to the chart and filter pages.
    *   Features the background image grid layout.

*   `frontend/chart.html`:
    *   The page dedicated to displaying the overall bus delay chart.
    *   Contains the `div` element (`#main`) where the ECharts chart is rendered.
    *   Includes the ECharts library (via CDN).
    *   Links to `script.js` for chart generation logic.
    *   Features the background image grid layout.

*   `frontend/filter.html`:
    *   The page allowing users to filter bus schedules.
    *   Contains the form with inputs for selecting a bus stop and specifying a time (hour/minute).
    *   Includes an area (`#filtered-results`) to display the schedule information returned by the API.
    *   Links to `filter.js` for handling form interactions and API calls.
    *   Features the background image grid layout.

*   `frontend/css/style.css`:
    *   The main stylesheet for all frontend pages.
    *   Defines the visual appearance, including the background image grid, container styling, button styles, form layout, and chart container dimensions.

*   `frontend/js/script.js`:
    *   JavaScript file specifically for `chart.html`.
    *   Fetches average delay data from the backend (`/api/bus-data`).
    *   Initializes and configures the ECharts bar chart to visualize the data.
    *   Handles chart resizing.

*   `frontend/js/filter.js`:
    *   JavaScript file specifically for `filter.html`.
    *   Populates the stop name dropdown by fetching data from `/api/stop-names`.
    *   Handles user interactions with the time inputs and the "Find Schedules" button.
    *   Sends requests to the backend (`/api/stop-schedule`) with the selected filter criteria.
    *   Displays the returned schedule results in the `#filtered-results` div.

*   `frontend/js/echarts.js`:
    *   *(Likely unused or local copy)* Represents the ECharts charting library. The project currently includes this library via a CDN link in `chart.html`. If this file exists, it might be a downloaded version or leftover.

*   `frontend/images/`:
    *   Directory containing the image files (`.jpg`, `.jpeg`) used in the background grid layout on all HTML pages.
