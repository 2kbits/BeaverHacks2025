// frontend/js/predict.js

document.addEventListener("DOMContentLoaded", () => {
    const timeInput = document.getElementById("predict-time");
    const predictButton = document.getElementById("predict-button");
    const resultDiv = document.getElementById("prediction-result");
  
    // Backend API endpoint URL
    const apiUrl = "http://127.0.0.1:8000/api/predict-delay"; // Adjust if needed
  
    predictButton.addEventListener("click", () => {
      const timeValue = timeInput.value; // Gets time as HH:MM
  
      if (!timeValue) {
        resultDiv.textContent = "Please select a time.";
        resultDiv.className = "error"; // Use class for styling
        return;
      }
  
      // Format time as HH:MM:SS for the backend
      const timeStringForAPI = `${timeValue}:00`;
  
      // Basic check (backend has regex validation too)
      if (!/^\d{2}:\d{2}:\d{2}$/.test(timeStringForAPI)) {
        resultDiv.textContent = "Invalid time format selected.";
        resultDiv.className = "error";
        return;
      }
  
      // --- Call the API ---
      resultDiv.textContent = "Predicting...";
      resultDiv.className = "loading"; // Style as loading
  
      // Construct URL with query parameter
      const fetchUrl = `${apiUrl}?time_str=${encodeURIComponent(
        timeStringForAPI
      )}`;
  
      fetch(fetchUrl)
        .then((response) => {
          if (!response.ok) {
            // Try to get error detail from backend response if possible
            return response.json().then((errData) => {
              throw new Error(
                errData.detail || `API Error: ${response.statusText}`
              );
            });
          }
          return response.json();
        })
        .then((data) => {
          console.log("Prediction API Response:", data); // Log for debugging
  
          if (data.predicted_delay_minutes !== null) {
            resultDiv.textContent = `Predicted Delay at ${
              data.requested_time
            }: ${data.predicted_delay_minutes.toFixed(1)} minutes`;
            resultDiv.className = "success"; // Style as success
          } else {
            // Prediction failed on the backend (e.g., time out of range, internal error)
            resultDiv.textContent = `Prediction failed: ${
              data.message || "Could not get prediction."
            }`;
            resultDiv.className = "error";
          }
        })
        .catch((error) => {
          console.error("Error fetching prediction:", error);
          resultDiv.textContent = `Error: ${error.message}`;
          resultDiv.className = "error";
        });
    });
  });
  