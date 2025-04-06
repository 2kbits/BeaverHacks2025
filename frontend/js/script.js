// frontend/js/script.js

// Wait for the HTML document to be fully loaded and parsed
document.addEventListener("DOMContentLoaded", function () {
  // console.log("DOM fully loaded and parsed for chart page.");

  // 1. Get the DOM element for the chart
  var chartDom = document.getElementById("main");
  if (!chartDom) {
    console.error("Chart container element #main not found in the DOM!");
    return;
  } else {
    // console.log("Chart container #main found.");
  }

  // Check initial container dimensions (for debugging)
  const computedStyle = window.getComputedStyle(chartDom);
  // console.log(
  //   `Initial container dimensions: width=${computedStyle.width}, height=${computedStyle.height}`
  // );
  if (
    !computedStyle.width ||
    computedStyle.width === "0px" ||
    !computedStyle.height ||
    computedStyle.height === "0px"
  ) {
    console.warn(
      "Chart container #main has zero width or height. Chart may not be visible."
    );
    chartDom.textContent =
      "Chart container has no dimensions. Ensure CSS is loaded and #main has height/width.";
  }

  // 2. Initialize ECharts instance
  var myChart = null;
  try {
    myChart = echarts.init(chartDom);
    // console.log("ECharts instance initialized successfully.");
  } catch (initError) {
    console.error("Error initializing ECharts:", initError);
    chartDom.textContent =
      "Failed to initialize charting library. Check if ECharts script loaded correctly.";
    return; // Stop if initialization fails
  }

  // 3. API endpoint URL (points to the backend endpoint for chart data)
  const apiUrl = "http://127.0.0.1:8000/api/bus-data"; // Adjust port if needed

  // 4. Fetch data from the backend
  // console.log("Attempting to fetch chart data from:", apiUrl);
  myChart.showLoading(); // Show loading animation

  fetch(apiUrl)
    .then((response) => {
      // console.log("Received response with status:", response.status);
      if (!response.ok) {
        // Try to get error details from backend response
        return response
          .json()
          .then((errData) => {
            throw new Error(errData.detail || `HTTP error ${response.status}`);
          })
          .catch(() => {
            // Fallback if response isn't JSON
            throw new Error(
              `HTTP error ${response.status}: Failed to fetch chart data`
            );
          });
      }
      // console.log("Response OK, attempting to parse JSON...");
      return response.json();
    })
    .then((data) => {
      myChart.hideLoading(); // Hide loading animation
      // console.log("Successfully parsed JSON data:", data);

      // --- Data Validation (MODIFIED) ---
      // Check for the NEW structure: 'stop_names' and 'avg_delays'
      if (
        !data ||
        typeof data !== "object" ||
        !Array.isArray(data.stop_names) || // CHANGED from data.routes
        !Array.isArray(data.avg_delays)
      ) {
        // CHANGED error message
        throw new Error(
          "Invalid data structure received from backend. Expected object with 'stop_names' and 'avg_delays' arrays."
        );
      }
      // CHANGED check to compare stop_names length
      if (data.stop_names.length !== data.avg_delays.length) {
        throw new Error(
          "Data mismatch: The number of stop names does not match the number of average delays."
        );
      }
      // CHANGED check for empty stop_names
      if (data.stop_names.length === 0) {
        console.warn(
          "Received empty data arrays for chart. Displaying empty chart."
        );
        // Optionally display a message in the chart area
        chartDom.textContent = "No data available to display the chart.";
        // Set empty data to ECharts to clear any previous chart
        myChart.setOption(
          {
            // CHANGED title
            title: {
              text: "Average Scheduled Delay per Stop Name",
              left: "center",
            },
            xAxis: { name: "Average Scheduled Delay (minutes)" },
            // CHANGED yAxis name and provide empty data
            yAxis: { name: "Stop Name", data: [] },
            series: [{ name: "Avg Delay (min)", type: "bar", data: [] }], // Empty data
          },
          true
        );
        return; // Stop further processing if data is empty
      }
      // console.log("Data structure seems valid.");

      // --- 5. Specify chart configuration (Horizontal Bar Chart) (MODIFIED) ---
      var option = {
        title: {
          // CHANGED title text
          text: "Average Scheduled Delay per Stop Name",
          left: "center",
        },
        tooltip: {
          trigger: "axis",
          axisPointer: { type: "shadow" },
          formatter: function (params) {
            if (!params || params.length === 0) return "";
            // CHANGED variable name for clarity
            var stopName = params[0].name; // Category from Y axis
            var avgDelay = params[0].value; // Value from X axis
            // CHANGED tooltip text
            return `${stopName}<br/>Avg Scheduled Delay: ${avgDelay.toFixed(
              2
            )} min`;
          },
        },
        grid: {
          // Adjusted left padding for potentially long stop names
          left: "20%", // Might need more space than routes did
          right: "5%",
          bottom: "3%",
          containLabel: true, // Ensures labels fit within the grid area
        },
        xAxis: {
          // Value axis (Horizontal)
          type: "value",
          name: "Average Scheduled Delay (minutes)",
          nameLocation: "middle",
          nameGap: 25, // Space between axis name and axis line
          axisLabel: {
            formatter: "{value} min", // Add 'min' suffix to labels
          },
        },
        yAxis: {
          // Category axis (Vertical)
          type: "category",
          // CHANGED axis name
          name: "Stop Name",
          nameLocation: "middle",
          // CHANGED nameGap - might need adjustment based on longest stop name
          nameGap: 120,
          // CHANGED data source to use stop_names
          data: data.stop_names,
          axisLabel: {
            interval: 0, // Show all labels. Use 'auto' or a function if too crowded.
            // Optional: Rotate labels if they overlap
            // rotate: 30,
            // Optional: Truncate long labels
            // formatter: function (value) {
            //     return value.length > 25 ? value.substring(0, 22) + '...' : value;
            // }
          },
        },
        series: [
          {
            name: "Avg Delay (min)", // Matches legend/tooltip
            type: "bar",
            // Data source remains avg_delays (this key didn't change)
            data: data.avg_delays,
            emphasis: {
              focus: "series", // Highlight bars on hover
            },
            itemStyle: {
              borderRadius: [0, 3, 3, 0], // Slightly rounded right corners
            },
            // Optional: Show labels directly on bars
            // label: { show: true, position: 'right', formatter: '{c}' }
          },
        ],
        // Optional: Add dataZoom for scrolling if many stops
        // dataZoom: [
        //     { type: 'inside', yAxisIndex: 0, filterMode: 'none' }, // filterMode 'none' is often better for category axis zooming
        //     { type: 'slider', yAxisIndex: 0, filterMode: 'none' }
        // ],
      };
      // console.log("ECharts option object created:", option);

      // --- 6. Display the chart using the configuration ---
      if (myChart) {
        try {
          // Use true to clear previous options and overwrite
          myChart.setOption(option, true);
          // console.log("myChart.setOption call SUCCEEDED.");
        } catch (renderError) {
          console.error("ERROR during myChart.setOption:", renderError);
          chartDom.textContent = "Error rendering chart: " + renderError.message;
        }
      } else {
        // Should not happen if initialization succeeded, but good practice
        console.error("Cannot setOption because myChart instance is not valid.");
      }
    })
    .catch((error) => {
      myChart.hideLoading(); // Hide loading animation on error too
      console.error("Error in fetch/processing chain for chart:", error);
      // Display error message in the chart container
      chartDom.textContent =
        "Failed to load or process chart data: " + error.message;
    });

  // --- Optional: Add responsiveness ---
  let resizeTimer;
  window.addEventListener("resize", function () {
    if (myChart) {
      // Debounce resize event to avoid excessive calls
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(function () {
        try {
          myChart.resize();
          // console.log("Chart resized.");
        } catch (resizeError) {
          console.error("Error during chart resize:", resizeError);
        }
      }, 200); // Adjust delay as needed
    }
  });
}); // End of DOMContentLoaded listener
