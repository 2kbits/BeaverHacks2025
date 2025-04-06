// frontend/js/filter.js

document.addEventListener("DOMContentLoaded", function () {
    console.log("Filter page DOM loaded.");
  
    // --- Get references to elements ---
    const routeSelect = document.getElementById("route-select");
    const hourInput = document.getElementById("hour-input");
    const hourDecrement = document.getElementById("hour-decrement");
    const hourIncrement = document.getElementById("hour-increment");
    const minuteInput = document.getElementById("minute-input");
    const minuteDecrement = document.getElementById("minute-decrement");
    const minuteIncrement = document.getElementById("minute-increment");
    const filterButton = document.getElementById("filter-button");
    const resultsDiv = document.getElementById("filtered-results"); // Area to display results
  
    // --- Check if all required elements exist ---
    if (
      !routeSelect ||
      !hourInput || !hourDecrement || !hourIncrement ||
      !minuteInput || !minuteDecrement || !minuteIncrement ||
      !filterButton || !resultsDiv // Also check resultsDiv
    ) {
      console.error("Required form or display elements not found in the DOM!");
      // Optionally display an error message on the page itself
      if(resultsDiv) resultsDiv.textContent = "Error: Page elements missing. Cannot initialize filters.";
      else console.error("Results display area (#filtered-results) is also missing.");
      return; // Stop execution if essential elements are missing
    }
  
    // --- API endpoint URLs ---
    const optionsApiUrl = "http://127.0.0.1:8000/api/filter-options";
    const findArrivalBaseUrl = "http://127.0.0.1:8000/api/find-arrival"; // Base URL for finding arrivals
  
    // --- Helper function to populate route select dropdown ---
    function populateRouteSelect(selectElement, optionsArray, defaultLabel) {
      selectElement.innerHTML = ""; // Clear existing options
      const defaultOption = document.createElement("option");
      defaultOption.value = ""; // Important: empty value for the default/placeholder
      defaultOption.textContent = defaultLabel;
      if (defaultLabel.includes("Loading")) {
          defaultOption.disabled = true; // Disable "Loading..."
      } else {
          defaultOption.selected = true; // Make "Select..." or error message selected
      }
      selectElement.appendChild(defaultOption);
  
      // Add actual route options
      optionsArray.forEach((optionValue) => {
        const option = document.createElement("option");
        option.value = optionValue;
        option.textContent = optionValue;
        selectElement.appendChild(option);
      });
    }
  
    // --- Fetch filter options (routes) and populate dropdown ---
    console.log("Fetching filter options from:", optionsApiUrl);
    fetch(optionsApiUrl)
      .then((response) => {
        if (!response.ok) {
          // Try to get more details from the response body on error
          return response.text().then(text => {
              throw new Error(`HTTP error ${response.status}: ${text || "Failed to fetch filter options"}`);
          });
        }
        return response.json();
      })
      .then((data) => {
        console.log("Filter options received:", data);
  
        // --- CORRECTED CHECK ---
        // Check specifically if data exists, is an object, and data.routes is an array
        if (data && typeof data === 'object' && Array.isArray(data.routes)) {
          populateRouteSelect(routeSelect, data.routes, "-- Select a Route --");
          console.log("Route dropdown populated.");
          // We ignore data.hours here as it's not used for a dropdown anymore
        } else {
          // Throw error if data is not an object or data.routes is not a valid array
          console.error("Invalid data structure received for filter options:", data);
          throw new Error("Invalid data structure received for filter options (expected object with 'routes' array).");
        }
      })
      .catch((error) => {
        console.error("Error fetching or populating filter options:", error);
        if (resultsDiv) { // Display error in results area if possible
            resultsDiv.textContent = "Error loading filter options: " + error.message;
        }
        // Ensure dropdown shows an error state
        routeSelect.innerHTML = '<option value="" disabled selected>Error loading routes</option>';
      });
  
  
    // --- Helper function to handle increment/decrement WITH WRAP-AROUND ---
    function setupIncrementDecrement(inputElem, decBtn, incBtn, minVal, maxVal) {
        decBtn.addEventListener('click', () => {
            let currentValue = parseInt(inputElem.value, 10);
            if (isNaN(currentValue) || currentValue < minVal || currentValue > maxVal) {
                currentValue = minVal;
            }
            let newValue = (currentValue === minVal) ? maxVal : currentValue - 1;
            inputElem.value = newValue;
            inputElem.dispatchEvent(new Event('input', { bubbles: true })); // Trigger input event
        });
  
        incBtn.addEventListener('click', () => {
            let currentValue = parseInt(inputElem.value, 10);
            if (isNaN(currentValue) || currentValue < minVal || currentValue > maxVal) {
                currentValue = minVal;
            }
            let newValue = (currentValue === maxVal) ? minVal : currentValue + 1;
            inputElem.value = newValue;
            inputElem.dispatchEvent(new Event('input', { bubbles: true })); // Trigger input event
        });
  
        // Input listener for typed values (clamps, doesn't wrap)
        inputElem.addEventListener('input', () => {
            let valueStr = inputElem.value;
            if (valueStr === '') return;
            let currentValue = parseInt(valueStr, 10);
            if (isNaN(currentValue)) {
                 inputElem.value = minVal;
                 return;
            }
            if (currentValue < minVal) inputElem.value = minVal;
            else if (currentValue > maxVal) inputElem.value = maxVal;
        });
  
         // Blur listener to finalize validation
         inputElem.addEventListener('blur', () => {
            let currentValue = parseInt(inputElem.value, 10);
             if (isNaN(currentValue) || currentValue < minVal) inputElem.value = minVal;
             else if (currentValue > maxVal) inputElem.value = maxVal;
         });
    }
  
    // --- Setup listeners for hour and minute inputs ---
    setupIncrementDecrement(hourInput, hourDecrement, hourIncrement, 0, 23);
    setupIncrementDecrement(minuteInput, minuteDecrement, minuteIncrement, 0, 59);
  
  
    // --- Event listener for the main filter button ---
    filterButton.addEventListener("click", function () {
      const selectedRoute = routeSelect.value;
      const selectedHour = hourInput.value;
      const selectedMinute = minuteInput.value; // Still captured, though not used in API call yet
  
      console.log("Filter button clicked!");
      console.log("Selected Route:", selectedRoute || "None");
      console.log("Selected Hour:", selectedHour);
      console.log("Selected Minute:", selectedMinute);
  
      // Clear previous results and show loading message
      resultsDiv.innerHTML = '<p><em>Loading arrival data...</em></p>';
  
      // --- Validate inputs before fetching ---
      if (!selectedRoute) { // Check if a route is selected (value is not empty)
          resultsDiv.innerHTML = '<p style="color: red;">Please select a route.</p>';
          return; // Stop if no route selected
      }
      // Basic check for hour/minute (should be valid due to input type/listeners)
      if (selectedHour === '' || selectedMinute === '') {
          resultsDiv.innerHTML = '<p style="color: red;">Please ensure hour and minute are set.</p>';
          return;
      }
  
      // --- Construct URL for the find-arrival endpoint ---
      // Using encodeURIComponent for the route name is good practice
      const findApiUrl = `${findArrivalBaseUrl}?route=${encodeURIComponent(selectedRoute)}&hour=${selectedHour}`;
      console.log("Fetching arrival data from:", findApiUrl);
  
      // --- Fetch data from the find-arrival endpoint ---
      fetch(findApiUrl)
        .then(response => {
          console.log("Find arrival response status:", response.status);
          // Check for specific error codes first
          if (response.status === 404) {
            return response.json().then(errorData => {
                throw new Error(errorData.detail || "No arrival data found for the selected criteria.");
            });
          }
          // Check for other non-OK statuses
          if (!response.ok) {
             return response.text().then(text => {
                 throw new Error(`HTTP error ${response.status}: ${text || "Failed to fetch arrival data"}`);
             });
          }
          // If response is OK (200)
          return response.json();
        })
        .then(data => {
          console.log("Arrival data received:", data);
          // Check if data has the expected properties
          if (data && data.scheduled && data.predicted) {
            // --- Display the results in the two boxes ---
            resultsDiv.innerHTML = `
              <div class="result-box">
                <h3>Scheduled Arrival</h3>
                <p>${formatDateTime(data.scheduled)}</p>
              </div>
              <div class="result-box">
                <h3>Predicted Arrival (Estimate)</h3>
                <p>${formatDateTime(data.predicted)}</p>
              </div>
            `;
          } else {
            // Fallback error if data format is wrong despite 200 OK
            resultsDiv.innerHTML = '<p>Arrival data received, but format is incorrect.</p>';
            console.warn("Received data format unexpected:", data);
          }
        })
        .catch(error => {
          console.error("Error fetching or displaying arrival data:", error);
          // Display the specific error message caught
          resultsDiv.innerHTML = `<p style="color: red;">Error: ${error.message}</p>`;
        });
    }); // End of filterButton listener
  
    // --- Helper function to format date/time string (optional but nice) ---
    function formatDateTime(dateTimeString) {
        if (!dateTimeString) return "N/A";
        try {
            const date = new Date(dateTimeString);
            // Use Intl for better locale support if needed, or keep simple
            return date.toLocaleString('en-US', {
                year: 'numeric', month: 'short', day: 'numeric',
                hour: 'numeric', minute: '2-digit', hour12: true
            });
        } catch (e) {
            console.warn("Could not format date:", dateTimeString, e);
            return dateTimeString; // Return original string if formatting fails
        }
    }
  
  }); // End of DOMContentLoaded listener
  