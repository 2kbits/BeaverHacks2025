// frontend/js/filter.js

document.addEventListener("DOMContentLoaded", function () {
    console.log("Filter page DOM loaded.");
  
    // --- Get references to elements ---
    const stopSelect = document.getElementById("stop-select");
    const hourInput = document.getElementById("hour-input");
    const hourDecrement = document.getElementById("hour-decrement");
    const hourIncrement = document.getElementById("hour-increment");
    const minuteInput = document.getElementById("minute-input");
    const minuteDecrement = document.getElementById("minute-decrement");
    const minuteIncrement = document.getElementById("minute-increment");
    const filterButton = document.getElementById("filter-button");
    const resultsDiv = document.getElementById("filtered-results");
  
    // --- Check if all required elements exist ---
    if (
      !stopSelect ||
      !hourInput || !hourDecrement || !hourIncrement ||
      !minuteInput || !minuteDecrement || !minuteIncrement ||
      !filterButton || !resultsDiv
    ) {
      console.error("Required form or display elements not found in the DOM!");
      if (resultsDiv) resultsDiv.innerHTML = '<p style="color: red;">Error: Page elements missing.</p>';
      return;
    }
  
    // --- API endpoint URL ---
    const apiBaseUrl = "http://127.0.0.1:8000/api"; // Adjust if needed
    const stopNamesApiUrl = `${apiBaseUrl}/stop-names`;
    const scheduleApiBaseUrl = `${apiBaseUrl}/stop-schedule`;
  
    // --- Helper function to populate stop select dropdown ---
    function populateStopSelect(selectElement, optionsArray, defaultLabel) {
      selectElement.innerHTML = ""; // Clear existing options
      const defaultOption = document.createElement("option");
      defaultOption.value = "";
      defaultOption.textContent = defaultLabel;
      if (defaultLabel.includes("Loading") || defaultLabel.includes("Error") || defaultLabel.includes("No stops")) {
        defaultOption.disabled = true;
      }
      defaultOption.selected = true;
      selectElement.appendChild(defaultOption);
  
      optionsArray.forEach((optionValue) => {
        const option = document.createElement("option");
        option.value = optionValue;
        option.textContent = optionValue;
        selectElement.appendChild(option);
      });
    }
  
    // --- Fetch stop names and populate dropdown ---
    console.log("Fetching stop names from:", stopNamesApiUrl);
    fetch(stopNamesApiUrl)
      .then((response) => {
        if (!response.ok) {
          return response.json().then(errData => { throw new Error(errData.detail || `HTTP error ${response.status}`); })
                 .catch(() => { throw new Error(`HTTP error ${response.status}: Failed to fetch stop names`); });
        }
        return response.json();
      })
      .then((data) => {
        console.log("Stop names received:", data);
        if (data && Array.isArray(data.stop_names)) {
          if (data.stop_names.length > 0) { populateStopSelect(stopSelect, data.stop_names, "-- Select a Stop --"); console.log("Stop dropdown populated."); }
          else { populateStopSelect(stopSelect, [], "-- No stops found --"); console.warn("No stop names returned from API."); }
        } else { throw new Error("Invalid data structure received for stop names."); }
      })
      .catch((error) => {
        console.error("Error fetching or populating stop names:", error);
        populateStopSelect(stopSelect, [], "Error loading stops");
        if (resultsDiv) { resultsDiv.innerHTML = `<p style="color: red;">Error loading stop options: ${error.message}. Please ensure the backend is running and data is loaded.</p>`; }
      });
  
  
    // --- Helper function to handle increment/decrement ---
    function setupIncrementDecrement(inputElem, decBtn, incBtn, minVal, maxVal) {
      decBtn.addEventListener("click", () => {
        let currentValue = parseInt(inputElem.value, 10); if (isNaN(currentValue) || currentValue < minVal || currentValue > maxVal) currentValue = minVal;
        let newValue = currentValue === minVal ? maxVal : currentValue - 1; inputElem.value = newValue; inputElem.dispatchEvent(new Event("input", { bubbles: true }));
      });
      incBtn.addEventListener("click", () => {
        let currentValue = parseInt(inputElem.value, 10); if (isNaN(currentValue) || currentValue < minVal || currentValue > maxVal) currentValue = minVal;
        let newValue = currentValue === maxVal ? minVal : currentValue + 1; inputElem.value = newValue; inputElem.dispatchEvent(new Event("input", { bubbles: true }));
      });
      inputElem.addEventListener("input", () => {
        let valueStr = inputElem.value; if (valueStr === "") return; let currentValue = parseInt(valueStr, 10);
        if (isNaN(currentValue)) { inputElem.value = minVal; return; }
        if (currentValue < minVal) inputElem.value = minVal; else if (currentValue > maxVal) inputElem.value = maxVal;
      });
      inputElem.addEventListener("blur", () => {
          if (inputElem.value === "") inputElem.value = minVal; let currentValue = parseInt(inputElem.value, 10);
          if (isNaN(currentValue) || currentValue < minVal) inputElem.value = minVal; else if (currentValue > maxVal) inputElem.value = maxVal;
      });
    }
  
    // --- Setup listeners for hour and minute inputs ---
    setupIncrementDecrement(hourInput, hourDecrement, hourIncrement, 0, 23);
    setupIncrementDecrement(minuteInput, minuteDecrement, minuteIncrement, 0, 59);
  
    // --- Event listener for the main filter button ---
    filterButton.addEventListener("click", function () {
      const selectedStopName = stopSelect.value;
      const selectedHour = hourInput.value;
      const selectedMinute = minuteInput.value;
  
      console.log("Filter button clicked!");
      console.log("Selected Stop Name:", selectedStopName);
      console.log("Selected Hour:", selectedHour);
      console.log("Selected Minute:", selectedMinute);
  
      resultsDiv.innerHTML = "<p><em>Loading schedule data...</em></p>";
  
      // --- Validate inputs ---
      if (!selectedStopName) { resultsDiv.innerHTML = '<p style="color: red;">Please select a stop.</p>'; return; }
      if (selectedHour === "" || selectedMinute === "") { resultsDiv.innerHTML = '<p style="color: red;">Please ensure hour and minute are set.</p>'; return; }
  
      // --- Construct URL for the stop-schedule endpoint ---
      const findApiUrl = `${scheduleApiBaseUrl}?stop_name=${encodeURIComponent(selectedStopName)}&hour=${selectedHour}&minute=${selectedMinute}`;
      console.log("Fetching schedule data from:", findApiUrl);
  
      // --- Fetch data ---
      fetch(findApiUrl)
        .then((response) => {
          console.log("Stop schedule response status:", response.status);
          if (!response.ok) {
            return response.json().then((errorData) => { throw new Error(errorData.detail || `HTTP error ${response.status}`); })
                   .catch(() => { throw new Error(`HTTP error ${response.status}: Failed to fetch schedule data`); });
          }
          return response.json();
        })
        .then((data) => {
          console.log("Schedule data received:", data);
          // --- Display the results (Using updated field name) ---
          if (data && Array.isArray(data.routes_at_stop)) {
            if (data.routes_at_stop.length === 0) {
               resultsDiv.innerHTML = `<p>No upcoming schedules found for stop '${data.stop_name}' around ${data.requested_time}.</p>`;
               return;
            }
  
            let resultsHtml = `
              <h2>Schedule for ${data.stop_name} at or after ${data.requested_time}</h2>
              <div class="results-grid">
            `;
            data.routes_at_stop.forEach((routeInfo) => {
              // *** Use the new field name here: average_scheduled_delay_at_schedule ***
              const avgSchedDelayText = routeInfo.average_scheduled_delay_at_schedule !== null
                  ? `${routeInfo.average_scheduled_delay_at_schedule} min`
                  : "N/A";
  
              resultsHtml += `
                <div class="result-route-box">
                  <h3>Route: ${routeInfo.route}</h3>
                  <p><strong>Next Bus ID:</strong> ${routeInfo.next_bus_id || "None found"}</p>
                  <p><strong>Next Scheduled:</strong> ${formatDateTime(routeInfo.next_scheduled_arrival) || "None found"}</p>
                  <p><strong>Avg. Scheduled Delay (for this schedule):</strong> ${avgSchedDelayText}</p>
                </div>
              `;
            });
            resultsHtml += `</div>`;
            resultsDiv.innerHTML = resultsHtml;
          } else {
            resultsDiv.innerHTML = "<p>Schedule data received, but format is incorrect.</p>";
            console.error("Received data format unexpected:", data);
          }
        })
        .catch((error) => {
          console.error("Error fetching or displaying schedule data:", error);
          resultsDiv.innerHTML = `<p style="color: red;">Error: ${error.message}</p>`;
        });
    }); // End of filterButton listener
  
    // --- Helper function to format date/time string ---
    function formatDateTime(dateTimeString) {
      if (!dateTimeString) return null;
      try {
        const date = new Date(dateTimeString);
        return date.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", hour12: true });
      } catch (e) {
        console.warn("Could not format date:", dateTimeString, e);
        return dateTimeString;
      }
    }
  
  }); // End of DOMContentLoaded listener
  