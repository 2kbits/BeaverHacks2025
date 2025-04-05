# BeaverHacks2025

File hierarchy example:

*   **BeaverHacks2025/**
    *   **backend/** `# All FastAPI backend code (Your friend's focus)`
        *   **app/** `# Main application package`
            *   `__init__.py` `# Makes 'app' a Python package`
            *   `main.py` `# FastAPI app creation, middleware, router inclusion`
            *   **routers/** `# Directory for API endpoint definitions`
                *   `__init__.py`
                *   `chart_data.py` `# Example: Router for chart data endpoints`
            *   **models/** `# Pydantic models for request/response validation`
                *   `__init__.py`
                *   `chart.py` `# Example: Pydantic model for chart data structure`
            *   **core/** `# Optional: Core logic, settings, db connections etc.`
                *   `__init__.py`
                *   `config.py` `# Example: Configuration settings`
        *   **tests/** `# Backend tests`
            *   `...`
        *   **venv/** `# Python virtual environment (add to .gitignore!)`
        *   `requirements.txt` `# Backend Python dependencies (FastAPI, uvicorn, etc.)`
    *   **frontend/** `# All static frontend code (Your focus)`
        *   `index.html` `# Your main HTML file`
        *   **js/**
            *   `script.js` `# Your ECharts JavaScript logic`
        *   **css/** `# Optional: CSS styling`
            *   `style.css`
    *   `.gitignore` `# Git ignore file`
    *   `README.md` `# Project description, setup, run instructions`
