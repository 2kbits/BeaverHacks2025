// frontend/js/predict.js

document.addEventListener("DOMContentLoaded", () => {
    const timeInput = document.getElementById("predict-time");
    const predictButton = document.getElementById("predict-button");
    const resultDiv = document.getElementById("prediction-result");
  
    // Use the NEW backend API endpoint URL
    const apiUrl = "http://127.0.0.1:8000/api/predict-next-delay"; // <-- CHANGED
  
    predictButton.addEventListener("click", () => {
      const timeValue = timeInput.value; // Gets time as HH:MM
  
      if (!timeValue) {
        resultDiv.textContent = "Please select a time.";
        resultDiv.className = "error";
        return;
      }
  
      const timeStringForAPI = `${timeValue}:00`;
  
      if (!/^\d{2}:\d{2}:\d{2}$/.test(timeStringForAPI)) {
        resultDiv.textContent = "Invalid time format selected.";
        resultDiv.className = "error";
        return;
      }
  
      resultDiv.textContent = "Finding next schedule and predicting..."; // Updated text
      resultDiv.className = "loading";
  
      const fetchUrl = `${apiUrl}?time_str=${encodeURIComponent(
        timeStringForAPI
      )}`;
  
      fetch(fetchUrl)
        .then((response) => {
          if (!response.ok) {
            return response.json().then((errData) => {
              throw new Error(
                errData.detail || `API Error: ${response.statusText}`
              );
            });
          }
          return response.json();
        })
        .then((data) => {
          console.log("Next Prediction API Response:", data);
  
          // --- UPDATED RESULT DISPLAY ---
          if (data.predicted_delay_minutes !== null && data.next_scheduled_time_used) {
            // Success case
            resultDiv.innerHTML = `Requested Time: ${data.requested_time}<br>
                                 Next Scheduled Bus at: ${data.next_scheduled_time_used}<br>
                                 Predicted Delay: <strong>${data.predicted_delay_minutes.toFixed(
                                   1
                                 )} minutes</strong>`;
            resultDiv.className = "success";
          } else {
            // Failure case (no next schedule found OR prediction failed for the found schedule)
            resultDiv.textContent = `Prediction failed: ${
              data.message || "Could not get prediction."
            }`;
            resultDiv.className = "error";
          }
          // --- END UPDATED DISPLAY ---
        })
        .catch((error) => {
          console.error("Error fetching next prediction:", error);
          resultDiv.textContent = `Error: ${error.message}`;
          resultDiv.className = "error";
        });
    });
  });
  