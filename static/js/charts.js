/**
 * SpeakPro AI – Chart.js Dashboard & Analytics Initializers
 * Renders glowing neon Radar, Line, Bar, and Pie charts using Chart.js 4+.
 */

document.addEventListener("DOMContentLoaded", function () {
  const chartDataEl = document.getElementById("chartsDataJson");
  if (!chartDataEl) return;

  try {
    const data = JSON.parse(chartDataEl.textContent);
    initRadarChart(data.radar_chart);
    initLineChart(data.line_chart);
    initBarChart(data.bar_chart);
    initPieChart(data.pie_chart);
  } catch (err) {
    console.warn("Could not parse Chart.js dataset JSON:", err);
  }
});

/**
 * 1. Radar Chart – Skill Competencies Breakdown
 */
function initRadarChart(config) {
  const ctx = document.getElementById("radarChartCanvas");
  if (!ctx || !config) return;

  new Chart(ctx, {
    type: "radar",
    data: config,
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        r: {
          min: 40,
          max: 100,
          grid: { color: "rgba(255, 255, 255, 0.1)" },
          angleLines: { color: "rgba(255, 255, 255, 0.1)" },
          pointLabels: {
            color: "#f8fafc",
            font: { size: 13, family: "Outfit, sans-serif", weight: "600" }
          },
          ticks: {
            color: "#64748b",
            backdropColor: "transparent",
            stepSize: 15
          }
        }
      },
      plugins: {
        legend: {
          labels: { color: "#f8fafc", font: { family: "Outfit, sans-serif" } }
        }
      }
    }
  });
}

/**
 * 2. Line Chart – Score Trend Over Sessions
 */
function initLineChart(config) {
  const ctx = document.getElementById("lineChartCanvas");
  if (!ctx || !config) return;

  new Chart(ctx, {
    type: "line",
    data: config,
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          min: 40,
          max: 100,
          grid: { color: "rgba(255, 255, 255, 0.08)" },
          ticks: { color: "#94a3b8" }
        },
        x: {
          grid: { color: "rgba(255, 255, 255, 0.05)" },
          ticks: { color: "#94a3b8" }
        }
      },
      plugins: {
        legend: {
          labels: { color: "#f8fafc", font: { family: "Outfit, sans-serif" } }
        }
      }
    }
  });
}

/**
 * 3. Bar Chart – Category Comparison
 */
function initBarChart(config) {
  const ctx = document.getElementById("barChartCanvas");
  if (!ctx || !config) return;

  new Chart(ctx, {
    type: "bar",
    data: config,
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          min: 40,
          max: 100,
          grid: { color: "rgba(255, 255, 255, 0.08)" },
          ticks: { color: "#94a3b8" }
        },
        x: {
          grid: { display: false },
          ticks: { color: "#f8fafc", font: { weight: "600" } }
        }
      },
      plugins: {
        legend: { display: false }
      }
    }
  });
}

/**
 * 4. Pie Chart – Topic Category Distribution
 */
function initPieChart(config) {
  const ctx = document.getElementById("pieChartCanvas");
  if (!ctx || !config) return;

  new Chart(ctx, {
    type: "doughnut",
    data: config,
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "68%",
      plugins: {
        legend: {
          position: "bottom",
          labels: { color: "#f8fafc", padding: 16, font: { family: "Outfit, sans-serif" } }
        }
      }
    }
  });
}
