// frontend/js/script.js

// Wait for the HTML document to be fully loaded and parsed
document.addEventListener("DOMContentLoaded", function () {
    console.log("DOM fully loaded and parsed.");
  
    // 1. Get the DOM element
    var chartDom = document.getElementById("main");
    if (!chartDom) {
      // If the container doesn't exist, log an error and stop.
      console.error("Chart container element #main not found in the DOM!");
      return;
    } else {
      console.log("Chart container #main found.");
    }
  
    // Check initial container dimensions (for debugging)
    const computedStyle = window.getComputedStyle(chartDom);
    console.log(
      `Initial container dimensions: width=${computedStyle.width}, height=${computedStyle.height}`
    );
    if (
      !computedStyle.width ||
      computedStyle.width === "0px" ||
      !computedStyle.height ||
      computedStyle.height === "0px"
    ) {
      console.warn(
        "Chart container #main has zero width or height. Chart may not be visible."
      );
      // Optionally add a message to the div itself
      // chartDom.textContent = "Chart container has no dimensions.";
    }
  
    // 2. Initialize ECharts instance
    var myChart = null; // Declare outside try block
    try {
      myChart = echarts.init(chartDom);
      console.log("ECharts instance initialized successfully.");
    } catch (initError) {
      console.error("Error initializing ECharts:", initError);
      chartDom.textContent = "Failed to initialize charting library.";
      return; // Stop if initialization fails
    }
  
    // 3. API endpoint URL (make sure this matches the backend route)
    const apiUrl = "http://127.0.0.1:8000/api/bus-data";
  
    // 4. Fetch data from the backend
    console.log("Attempting to fetch data from:", apiUrl);
    fetch(apiUrl)
      .then((response) => {
        console.log("Received response with status:", response.status);
        if (!response.ok) {
          // If response is not OK, try to read the response body as text for more details
          return response.text().then((text) => {
            // Throw an error that includes the status and potentially the server's error message
            throw new Error(
              `HTTP error! status: ${response.status}, message: ${text || "No error message body"}`
            );
          });
        }
        // If response is OK, parse it as JSON
        console.log("Response OK, attempting to parse JSON...");
        return response.json(); // This returns a Promise
      })
      .then((data) => {
        console.log("Successfully parsed JSON data:", data);
  
        // --- Data Validation ---
        if (
          !data ||
          typeof data !== "object" ||
          !Array.isArray(data.routes) ||
          !Array.isArray(data.avg_delays)
        ) {
          throw new Error(
            "Invalid data structure received from backend. Expected object with 'routes' and 'avg_delays' arrays."
          );
        }
        if (data.routes.length !== data.avg_delays.length) {
          throw new Error(
            "Data mismatch: The number of routes does not match the number of average delays."
          );
        }
        console.log("Data structure seems valid.");
  
        // --- 5. Specify chart configuration (Horizontal Bar Chart) ---
        var option = {
          title: {
            text: "Average Scheduled Delay per Bus Route",
            left: "center",
          },
          tooltip: {
            trigger: "axis",
            axisPointer: { type: "shadow" },
            formatter: function (params) {
              if (!params || params.length === 0) return "";
              var routeName = params[0].name; // Category from Y axis
              var avgDelay = params[0].value; // Value from X axis
              return `${routeName}<br/>Avg Scheduled Delay: ${avgDelay.toFixed(2)} min`; // Format value
            },
          },
          grid: {
            left: "15%", // Increased left padding for route names
            right: "5%",
            bottom: "3%",
            containLabel: true,
          },
          xAxis: { // Value axis (Horizontal)
            type: "value",
            name: "Average Scheduled Delay (minutes)",
            nameLocation: "middle",
            nameGap: 25,
            axisLabel: {
                formatter: '{value} min'
            }
          },
          yAxis: { // Category axis (Vertical)
            type: "category",
            name: "Bus Route",
            nameLocation: "middle",
            nameGap: 85, // Adjust needed space for route names
            data: data.routes, // Use the 'routes' array
            axisLabel: {
                interval: 0, // Show all labels
            }
          },
          series: [
            {
              name: "Avg Delay (min)",
              type: "bar",
              data: data.avg_delays, // Use the 'avg_delays' array
              emphasis: {
                focus: "series",
              },
              itemStyle: {
                borderRadius: [0, 3, 3, 0], // Rounded right corners
              },
              // Optional: Show labels on bars
              // label: {
              //     show: true,
              //     position: 'right', // Adjust position based on value (positive/negative) if needed
              //     formatter: '{c}' // {c} represents the data value
              // }
            },
          ],
          // Optional: DataZoom for vertical scrolling
          // dataZoom: [
          //     { type: 'inside', yAxisIndex: 0, start: 0, end: 100 },
          //     { type: 'slider', yAxisIndex: 0, start: 0, end: 100 }
          // ],
        };
        console.log("ECharts option object created:", option);
  
        // --- 6. Display the chart using the configuration ---
        if (myChart) {
          try {
            myChart.setOption(option, true); // Use true to clear previous options if any
            console.log("myChart.setOption call SUCCEEDED.");
          } catch (renderError) {
            console.error("ERROR during myChart.setOption:", renderError);
            // Display error message in the chart container
            chartDom.textContent = "Error rendering chart: " + renderError.message;
          }
        } else {
          console.error("Cannot setOption because myChart instance is not valid.");
        }
      })
      .catch((error) => {
        // Catch errors from fetch, JSON parsing, or data validation
        console.error("Error in fetch/processing chain:", error);
        // Display error message in the chart container
        chartDom.textContent = "Failed to load or process chart data: " + error.message;
      });
  
    // --- Optional: Add responsiveness ---
    window.addEventListener("resize", function () {
      if (myChart) {
        // Use a timeout (debounce) to avoid excessive resize calls during rapid resizing
        setTimeout(function () {
          try {
            myChart.resize();
            console.log("Chart resized.");
          } catch (resizeError) {
              console.error("Error during chart resize:", resizeError);
          }
        }, 200);
      }
    });
  
  }); // End of DOMContentLoaded listener
  