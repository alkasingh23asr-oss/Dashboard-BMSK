let currentType = "AWS";
let map = L.map("map").setView([25.8727, 85.9162], 8);
let markers = [];
let pieChart = null;
let selectedDistrict = null;
let selectedVendor = null;



datePicker.value = new Date().toISOString().split("T")[0];

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png").addTo(map);

/* ================= STATUS COLOR ================= */
statusFilter.onchange = () => {
  statusFilter.style.borderColor =
    statusFilter.value === "WORKING"
      ? "#198754"
      : statusFilter.value === "NON-WORKING"
      ? "#dc3545"
      : "#0b2c4d";
};

/* ================= LOAD MAIN DATA ================= */
function loadData() {
  const date = datePicker.value;
  const status = statusFilter.value;

  /* ===== SUMMARY + PIE ===== */
  fetch(`/api/summary?type=${currentType}&date=${date}`)
    .then((r) => r.json())
    .then((d) => {
      working.innerText = d.working;
      notWorking.innerText = d.not_working;

      if (pieChart) pieChart.destroy();

      pieChart = new Chart(document.getElementById("pieChart"), {
        type: "pie",
        data: {
          labels: ["Working", "Not Working"],
          datasets: [
            {
              data: [d.working, d.not_working],
              backgroundColor: ["rgb(64, 148, 184)", "red"],
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: true,
          plugins: {
            datalabels: {
              color: "#fff",
              font: { weight: "bold", size: 14 },
              formatter: (value, ctx) => {
                const total = ctx.chart.data.datasets[0].data.reduce(
                  (a, b) => a + b,
                  0
                );
                return parseInt((value / total) * 100) + "%";
              },
            },
            legend: { position: "bottom" },
          },
        },
        plugins: [ChartDataLabels],
      });
    });

  /* ===== MAP ===== */
  fetch(`/api/map?type=${currentType}&date=${date}&status=${status}`)
    .then((r) => r.json())
    .then((data) => {
      markers.forEach((m) => map.removeLayer(m));
      markers = [];

      data.forEach((s) => {
        const m = L.circleMarker([s.lat, s.lon], {
          radius: 2,
          color: s.status === "WORKING" ? "green" : "red",
          fillColor: s.status === "WORKING" ? "green" : "red",
          fillOpacity: 0.9,
          opacity: 1,
          className: s.status === "WORKING" ? "blink-green" : "blink-red",
        })
          .bindPopup(
            `
          Station: ${s.station_id}<br>
          District: ${s.district}<br>
          Block: ${s.block}
        `
          )
          .addTo(map);

        markers.push(m);
      });
    });

  loadVendorTable();
}

/* ================= VENDOR TABLE ================= */
function loadVendorTable() {
  fetch(`/api/vendor-summary?type=${currentType}&date=${datePicker.value}`)
    .then((r) => r.json())
    .then((rows) => {
      const tbody = document.querySelector("#vendorTable tbody");
      tbody.innerHTML = "";

      if (!rows.length) {
        tbody.innerHTML = `<tr><td colspan="4">No data</td></tr>`;
        return;
      }

      rows.forEach((v) => {
        tbody.innerHTML += `
          <tr>
            <td>${v.vendor}</td>
            <td>${v.total}</td>
            <td>
  <span class="count-badge badge-working">${v.working}</span>
</td>
<td>
  <span class="count-badge badge-not-working">${v.not_working}</span>
</td>

          </tr>
        `;
      });
    });
}

/* ================= CLICK HELPERS ================= */
function highlightSelectedRow(tableId, row) {
  document
    .querySelectorAll(`#${tableId} tbody tr`)
    .forEach((tr) => tr.classList.remove("selected-row"));
  row.classList.add("selected-row");
}

function resetDistrictBlock() {
  // hide panels
  document.getElementById("bottomPanel").style.display = "none";
  document.getElementById("blockPanel").style.display = "none";

  // clear tables
  document.querySelector("#districtTable tbody").innerHTML = "";
  document.querySelector("#blockTable tbody").innerHTML = "";

  // reset tag
  document.getElementById("districtStatusTag").innerText = "";
}

document.querySelector("#vendorTable").onclick = (e) => {
  const badge = e.target.closest(".count-badge");
  if (!badge) return;

  const row = badge.closest("tr");
  const vendor = row.children[0].innerText;

  // remove old active
  document
    .querySelectorAll(".count-badge")
    .forEach((b) => b.classList.remove("active"));
  badge.classList.add("active");

  // ✅ SHOW bottom panel
  const bottomPanel = document.getElementById("bottomPanel");
  bottomPanel.style.display = "flex";

  // ✅ SCROLL
  bottomPanel.scrollIntoView({ behavior: "smooth" });

  if (badge.classList.contains("badge-working")) {
    document.getElementById("districtStatusTag").innerText = "WORKING";
    loadDistrict(vendor, "WORKING");
  }

  if (badge.classList.contains("badge-not-working")) {
    document.getElementById("districtStatusTag").innerText = "NON-WORKING";
    loadDistrict(vendor, "NON-WORKING");
  }
};

/* ================= DISTRICT LOAD ================= */

function highlightSelectedRow(tableId, row) {
  document
    .querySelectorAll(`#${tableId} tbody tr`)
    .forEach((tr) => tr.classList.remove("selected"));

  row.classList.add("selected");
}

// function loadDistrict(vendor, status) {
//   const blockPanel = document.getElementById("blockPanel");

//   // clear old block data
//   document.querySelector("#blockTable tbody").innerHTML = "";

//   if (status === "WORKING") {
//     blockPanel.style.display = "none";
//   } else {
//     blockPanel.style.display = "block";
//   }

//   fetch(
//     `/api/vendor-district-summary?type=${currentType}&date=${datePicker.value}&vendor=${vendor}&status=${status}`
//   )
//     .then((r) => r.json())
//     .then((data) => {
//       const tbody = document.querySelector("#districtTable tbody");
//       tbody.innerHTML = "";

//       data.forEach((d, i) => {
//         const tr = document.createElement("tr");

//         tr.innerHTML = `
//           <td>${d.district}</td>
//           <td>${d.total}</td>
//           <td>${d.agency}</td>
//         `;

//         tr.onclick = () => {
//           highlightSelectedRow("districtTable", tr);

//           // ✅ Only NON-WORKING loads block fault
//           if (status === "NON-WORKING") {
//             loadBlockFault(vendor, d.district);
//           }
//         };

//         tbody.appendChild(tr);

//         // ✅ Auto select first district
//         if (i === 0) {
//           highlightSelectedRow("districtTable", tr);

//           if (status === "NON-WORKING") {
//             loadBlockFault(vendor, d.district);
//           }
//         }
//       });
//     });
// }

// function loadDistrict(vendor, status) {
//   const blockPanel = document.getElementById("blockPanel");

//   // clear old block data
//   document.querySelector("#blockTable tbody").innerHTML = "";

//   blockPanel.style.display = status === "WORKING" ? "none" : "block";

//   fetch(
//     `/api/vendor-district-summary?type=${currentType}&date=${datePicker.value}&vendor=${vendor}&status=${status}`
//   )
//     .then((r) => r.json())
//     .then((data) => {
//       const tbody = document.querySelector("#districtTable tbody");
//       tbody.innerHTML = "";

//       data.forEach((d, i) => {
//         const tr = document.createElement("tr");

//         // ✅ Clear & meaningful total display
//         tr.innerHTML = `
//           <td>${d.district}</td>
//           <td>
//             <b>Total:</b> ${d.total_installed}<br>
//             <span style="color:green">✔ Working:</span> ${d.working}<br>
//             <span style="color:red">✖ Non-Working:</span> ${d.non_working}
//           </td>
//           <td>${d.agency}</td>
//         `;

//         tr.onclick = () => {
//           highlightSelectedRow("districtTable", tr);

//           if (status === "NON-WORKING") {
//             loadBlockFault(vendor, d.district);
//           }
//         };

//         tbody.appendChild(tr);

//         // ✅ Auto select first row
//         if (i === 0) {
//           highlightSelectedRow("districtTable", tr);
//           if (status === "NON-WORKING") {
//             loadBlockFault(vendor, d.district);
//           }
//         }
//       });
//     });
// }

function loadDistrict(vendor, status) {
  const blockPanel = document.getElementById("blockPanel");
  selectedVendor = vendor;

  // clear old block data
  document.querySelector("#blockTable tbody").innerHTML = "";

  blockPanel.style.display = status === "WORKING" ? "none" : "block";

  fetch(
    `/api/vendor-district-summary?type=${currentType}&date=${datePicker.value}&vendor=${vendor}&status=${status}`
  )
    .then((r) => r.json())
    .then((data) => {
      const tbody = document.querySelector("#districtTable tbody");
      tbody.innerHTML = "";

      data.forEach((d, i) => {
        const tr = document.createElement("tr");

        tr.innerHTML = `
          <td>${d.district}</td>
          <td>
            <b>Total:</b> ${d.total_installed}<br>
            <span style="color:green">✔ Working:</span> ${d.working}<br>
            <span style="color:red">✖ Non-Working:</span> ${d.non_working}
          </td>
          <td>${d.agency}</td>
        `;

        tr.onclick = () => {
          highlightSelectedRow("districtTable", tr);

          // store selected district
          selectedDistrict = d.district;

          // load block fault only for NON-WORKING
          if (status === "NON-WORKING") {
            loadBlockFault(vendor, d.district);
          }
        };

        tbody.appendChild(tr);

        // Auto select first district
        if (i === 0) {
          highlightSelectedRow("districtTable", tr);
          selectedDistrict = d.district;

          if (status === "NON-WORKING") {
            loadBlockFault(vendor, d.district);
          }
        }
      });
    });
}

function printBlockReport() {
  if (!selectedDistrict) {
    alert("Please select a district first!");
    return;
  }

  const blockTableHTML = document.getElementById("blockTable").outerHTML;
  const reportDate = datePicker.value; // yyyy-mm-dd
  const reportType = currentType; // ARG / AWS
  const reportAgency = selectedVendor;

  const printWindow = window.open("", "", "width=900,height=650");

  printWindow.document.write(`
    <html>
      <head>
        <title>${reportType}_${reportAgency}_${selectedDistrict}_${reportDate} Report</title>
        <style>
          body {
            font-family: Arial, sans-serif;
            padding: 20px;
          }

          .navbar {
                  width: 100%;
                  height: 70px;
                  background: linear-gradient(90deg, #0097b2, #134b7f);
                  box-shadow: 0 3px 10px rgba(0, 0, 0, 0.3);
                  display: flex;
                  align-items: center;
                  justify-content: center;
                  position: sticky;
                  top: 0;
                  z-index: 1000;
          }
          .navElement {
                  width: 98%;
                  display: flex;
                  align-items: center;
                  justify-content: space-between;
          }
          .logo_bihar img,.logo_bmsk img {
                  height: 45px;
                  width: auto;
                  border-radius: 2px;
          }

          .logo_bihar {
              margin-right: 15px;
          }

          .logo_bmsk {
              margin-right: 15px;
          }
          h2{
            text-align: center;
            margin: 5px 0;
          }
          table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
          }
          th, td {
            border: 1px solid #000;
            padding: 6px;
            text-align: center;
          }
          th {
            background: #f2f2f2;
          }
          .meta{
             display: flex;
             align-items: center;
             justify-content: space-between;
          }
        </style>
        
      </head>
      <body>
        <div class="navbar">
          <div class="navElement">
            <div class="logo_bmsk"><img src="../static/image/image.png"></div>
            <div class="navHead">BIHAR MAUSAM SEWA KENDRA </div>
            <div class="logo_bihar"><img src="../static/image/image1.png"></div>
          </div>
        </div>
        <h2>District Block-wise Fault Report</h2>
        <div class="meta">
          <b>Type: ${reportType}</b>
          <h4>District: ${selectedDistrict}</h4>
          <h4>Vender Name: ${reportAgency}</h4>
          <b>Date: ${reportDate} </b>
        </div>
        
        ${blockTableHTML}
      </body>
    </html>
  `);

  printWindow.document.close();
  printWindow.focus();
  printWindow.print();
}

/* ================= BLOCK FAULT ================= */

function toggleBlockColumns(type) {
  const allowedCols =
    type === "ARG"
      ? ["block", "station_id", "rf"]
      : [
          "block",
          "station_id",
          "temp_rh",
          "rf",
          "ws",
          "ap",
          "sm",
          "sr",
          "data_pkt",
          "agency",
        ];

  // header
  document.querySelectorAll("#blockTable th").forEach((th, idx) => {
    const col = th.dataset.col;
    const show = allowedCols.includes(col);
    th.style.display = show ? "" : "none";

    // body cells
    document.querySelectorAll(`#blockTable tbody tr`).forEach((tr) => {
      tr.children[idx].style.display = show ? "" : "none";
    });
  });
}

// function loadBlockFault(vendor, district) {
//   fetch(
//     `/api/block-fault?type=${currentType}&date=${datePicker.value}&vendor=${vendor}&district=${district}`
//   )
//     .then((r) => r.json())
//     .then((rows) => {
//       const tbody = document.querySelector("#blockTable tbody");
//       tbody.innerHTML = "";

//       rows.forEach((r) => {
//         const tr = document.createElement("tr");

//         tr.innerHTML = `
//           <td>${r.block}</td>
//           <td>${r.station_id}</td>
//           <td>${r.temp_rh ?? "x"}</td>
//           <td>${r.rf ?? "x"}</td>
//           <td>${r.ws ?? "x"}</td>
//           <td>${r.ap ?? "x"}</td>
//           <td>${r.sm ?? "x"}</td>
//           <td>${r.sr ?? "x"}</td>
//           <td>${r.data_pkt ?? "x"}</td>
//           <td>${r.agency ?? "x"}</td>
//         `;

//         tbody.appendChild(tr);
//       });

//       // ✅ AFTER data load → column visibility control
//       toggleBlockColumns(currentType);
//     });
// }

function loadBlockFault(vendor, district) {
  fetch(
    `/api/block-fault?type=${currentType}&date=${datePicker.value}&vendor=${vendor}&district=${district}`
  )
    .then(r => r.json())
    .then(rows => {

      const tbody = document.querySelector("#blockTable tbody");
      tbody.innerHTML = "";

      rows.forEach(r => {
        const tr = document.createElement("tr");

        tr.innerHTML = `
          <td>${r.block}</td>
          <td class="station-link" style="cursor:pointer;color:#0b5ed7">
            ${r.station_id}
          </td>
          <td>${r.temp_rh ?? "x"}</td>
          <td>${r.rf ?? "x"}</td>
          <td>${r.ws ?? "x"}</td>
          <td>${r.ap ?? "x"}</td>
          <td>${r.sm ?? "x"}</td>
          <td>${r.sr ?? "x"}</td>
          <td>${r.data_pkt ?? "x"}</td>
          <td>${r.agency ?? "x"}</td>
        `;

        tbody.appendChild(tr);
      });

      toggleBlockColumns(currentType);
    });
}





/* ================= BUTTON EVENTS ================= */
awsBtn.onclick = () => {
  currentType = "AWS";
  awsBtn.className = "btn-primary";
  argBtn.className = "btn-outline";
  resetDistrictBlock(); // ✅ NEW
  loadData();
};

argBtn.onclick = () => {
  currentType = "ARG";
  argBtn.className = "btn-primary";
  awsBtn.className = "btn-outline";
  resetDistrictBlock(); // ✅ NEW
  loadData();
};

datePicker.onchange = () => {
  resetDistrictBlock(); // ✅ NEW
  loadData();
};

statusFilter.onchange = loadData;

/* ================= INIT ================= */
loadData();
