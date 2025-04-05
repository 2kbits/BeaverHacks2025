// 1. Get the DOM element where the chart will be rendered
var chartDom = document.getElementById("main");

// 2. Initialize an ECharts instance based on the prepared DOM element
var myChart = echarts.init(chartDom);

// 3. Define the URL of your backend API endpoint
const apiUrl = "http://127.0.0.1:8000/api/chart-data"; // Make sure port matches your backend

// 4. Fetch data from the backend API
fetch(apiUrl)
  .then((response) => {
    // Check if the request was successful (status code 200-299)
    if (!response.ok) {
      // If not successful, throw an error to be caught by .catch()
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    // If successful, parse the JSON body of the response
    return response.json(); // This also returns a Promise
  })
  .then((data) => {
    // This .then() receives the actual parsed JSON data
    console.log("Data received from backend:", data); // Good for debugging

    // 5. Specify the configuration items using the fetched data
    var option = {
      title: {
        text: "Chart from Backend Data", // Updated title
      },
      tooltip: {},
      legend: {
        // You might want the backend to provide legend info too,
        // but for this example, we'll assume a single series.
        // data: ['Sales'] // We can derive this or get it from backend
      },
      xAxis: {
        // Use the 'categories' array from the fetched data
        data: data.categories,
      },
      yAxis: {},
      series: [
        {
          name: "Values", // Or get this name from backend if needed
          type: "bar",
          // Use the 'values' array from the fetched data
          data: data.values,
        },
      ],
    };

    // 6. Display the chart using the configuration items and fetched data.
    //    This MUST be inside this .then() block, after data is received.
    myChart.setOption(option);
  })
  .catch((error) => {
    // Handle any errors that occurred during the fetch operation
    console.error("Error fetching or processing data:", error);
    // Optionally display an error message to the user on the page
    chartDom.textContent = "Failed to load chart data. " + error.message;
  });

// Optional: Add responsiveness (resizes chart when window size changes)
// This can stay outside the fetch, as it just needs the myChart instance
window.addEventListener("resize", function () {
  // Need to ensure myChart is initialized before resizing is possible
  // In this setup it is, but in complex apps, you might check.
  if (myChart) {
    myChart.resize();
  }
});
