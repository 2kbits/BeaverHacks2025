// 1. Get the DOM element where the chart will be rendered
//    'echarts.init' needs the actual DOM element, not just the ID string.
var chartDom = document.getElementById("main");

// 2. Initialize an ECharts instance based on the prepared DOM element
var myChart = echarts.init(chartDom);

// 3. Specify the configuration items and data for the chart
var option = {
  // Title configuration
  title: {
    text: "Simple Bar Chart",
  },
  // Tooltip configuration (shows details on hover)
  tooltip: {},
  // Legend configuration (if you have multiple series)
  legend: {
    data: ["Sales"],
  },
  // X-axis configuration
  xAxis: {
    data: ["Shirts", "Cardigans", "Chiffons", "Pants", "Heels", "Socks"],
  },
  // Y-axis configuration (ECharts figures out the scale automatically)
  yAxis: {},
  // Series configuration (the actual data to be plotted)
  series: [
    {
      name: "Sales", // Matches the legend data
      type: "bar", // Specifies the chart type (bar chart)
      data: [5, 20, 36, 10, 10, 20], // The data points for the x-axis categories
    },
  ],
};

// 4. Display the chart using the configuration items and data just specified.
myChart.setOption(option);

// Optional: Add responsiveness (resizes chart when window size changes)
window.addEventListener("resize", function () {
  myChart.resize();
});
