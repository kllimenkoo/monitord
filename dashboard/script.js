const baseUrl = "http://localhost:8000";

function formatTimestamps(timestamp) {
  return new Date(timestamp * 1000).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function showError(message) {
  if (document.getElementById("error-banner")) return;

  const banner = document.createElement("div");
  banner.id = "error-banner";
  banner.textContent = message;
  document.body.prepend(banner);
}

function clearError() {
  document.getElementById("error-banner")?.remove();
}

async function fetchApi(baseUrl, endpoint) {
  const response = await fetch(`${baseUrl}/${endpoint}`);
  if (!response.ok) {
    throw new Error(
      `Server returned ${response.status}: ${response.statusText}`,
    );
  }
  return await response.json();
}

async function fetchApiAsc(baseUrl, endpoint) {
  const data = await fetchApi(baseUrl, endpoint);
  return data.reverse();
}

function createChart(canvasId, datasets, yAxisOptions = {}) {
  const ctx = document.getElementById(canvasId);
  return new Chart(ctx, {
    type: "line",
    data: {
      labels: [],
      datasets: datasets.map((dataset) => ({
        tension: 0.4,
        ...dataset,
      })),
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          ticks: {
            maxTicksLimit: 6,
          },
        },
        y: {
          min: 0,
          ...yAxisOptions,
        },
      },
    },
  });
}

function createDynamicChart(canvasId, containerId, datasets, yAxisOptions) {
  const wrapper = document.createElement("div");
  wrapper.classList.add("chart-container");
  const canvas = document.createElement("canvas");
  canvas.id = canvasId;
  wrapper.appendChild(canvas);
  document.getElementById(containerId).appendChild(wrapper);

  return createChart(canvasId, datasets, yAxisOptions);
}

function updateChart(chart, data, ...extractors) {
  chart.data.labels = data.map((metric) => formatTimestamps(metric.timestamp));
  extractors.forEach((fn, i) => {
    chart.data.datasets[i].data = data.map(fn);
  });
  chart.update("none");
}

function renderAlerts(alerts) {
  const container = document.getElementById("alertsList");
  if (!alerts.length) {
    container.innerHTML = '<p class="no-alerts">No alerts.</p>';
    return;
  }
  container.innerHTML = alerts
    .map((line) => `<div class="alert-item">${line.trim()}</div>`)
    .join("");
}

async function refreshAlerts() {
  const { alerts } = await fetchApi(baseUrl, "alerts");
  renderAlerts(alerts);
}

async function main() {
  const [cpuData, ramData, devices, intfs] = await Promise.all([
    fetchApiAsc(baseUrl, "cpu"),
    fetchApiAsc(baseUrl, "ram"),
    fetchApi(baseUrl, "get_device_names"),
    fetchApi(baseUrl, "get_interface_names"),
  ]);

  await refreshAlerts();

  const cpuChart = createChart(
    "cpuChart",
    [
      {
        label: "CPU Usage",
        data: [],
      },
    ],
    {
      ticks: {
        callback: (value) => `${value}%`,
      },
    },
  );
  updateChart(cpuChart, cpuData, (m) => m.usage_percentage);

  const ramChart = createChart(
    "ramChart",
    [
      {
        label: "Memory Usage",
        data: [],
      },
      {
        label: "Swap Usage",
        data: [],
      },
    ],
    {
      ticks: {
        callback: (value) => `${value}%`,
      },
    },
  );
  updateChart(
    ramChart,
    ramData,
    (m) => m.mem_usage_percentage,
    (m) => m.swap_usage_percentage,
  );

  const diskData = await Promise.all(
    devices.map((device) => fetchApiAsc(baseUrl, `disk/${device}`)),
  );

  const diskCharts = [];
  devices.forEach((device, i) => {
    diskCharts.push(
      createDynamicChart(
        `diskChart-${device}`,
        "diskCharts",
        [{ label: `${device} IO Utilization`, data: [] }],
        { ticks: { callback: (value) => `${value}%` } },
      ),
    );
    updateChart(diskCharts[i], diskData[i], (m) => m.io_utilization_percentage);
  });

  const netData = await Promise.all(
    intfs.map((intf) => fetchApiAsc(baseUrl, `net/${intf}`)),
  );

  const netCharts = [];
  intfs.forEach((intf, i) => {
    netCharts.push(
      createDynamicChart(
        `netChart-${intf}`,
        "netCharts",
        [
          {
            label: `${intf} Received`,
            data: [],
          },
          {
            label: `${intf} Transmitted`,
            data: [],
          },
        ],
        {
          ticks: {
            callback: (value) => `${value} KB/s`,
          },
        },
      ),
    );
    updateChart(
      netCharts[i],
      netData[i],
      (m) => m.receive_bytes_per_sec,
      (m) => m.transmit_bytes_per_sec,
    );
  });

  setInterval(async () => {
    try {
      const [newCpuData, newRamData, newDiskData, newNetData] =
        await Promise.all([
          fetchApiAsc(baseUrl, "cpu"),
          fetchApiAsc(baseUrl, "ram"),
          Promise.all(
            devices.map((device) => fetchApiAsc(baseUrl, `disk/${device}`)),
          ),
          Promise.all(intfs.map((intf) => fetchApiAsc(baseUrl, `net/${intf}`))),
        ]);

      clearError();

      await refreshAlerts();

      updateChart(cpuChart, newCpuData, (m) => m.usage_percentage);
      updateChart(
        ramChart,
        newRamData,
        (m) => m.mem_usage_percentage,
        (m) => m.swap_usage_percentage,
      );

      diskCharts.forEach((chart, i) => {
        updateChart(chart, newDiskData[i], (m) => m.io_utilization_percentage);
      });

      netCharts.forEach((chart, i) => {
        updateChart(
          chart,
          newNetData[i],
          (m) => parseFloat((m.receive_bytes_per_sec / 1000).toFixed(2)),
          (m) => parseFloat((m.transmit_bytes_per_sec / 1000).toFixed(2)),
        );
      });
    } catch (error) {
      showError("Connection lost - retrying...");
    }
  }, 2000);
}

const sidebar = document.getElementById("alertsSidebar");
const toggleBtn = document.getElementById("alertsToggle");

toggleBtn.addEventListener("click", () => {
  sidebar.classList.toggle("open");
  toggleBtn.classList.toggle("sidebar-open");
});

main().catch((error) => {
  showError("Could not connect to monitord — is the daemon running?");
  console.error(error);
});
