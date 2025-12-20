let currentType = "AWS";
let markers = [];

const datePicker = document.getElementById("datePicker");
const statusFilter = document.getElementById("statusFilter");
const awsBtn = document.getElementById("awsBtn");
const argBtn = document.getElementById("argBtn");

datePicker.value = new Date().toISOString().split("T")[0];
datePicker.max = datePicker.value;

let map = L.map("map").setView([25.6, 85.1], 7);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png").addTo(map);

/* Bihar boundary */
fetch(
  "https://raw.githubusercontent.com/datameet/maps/master/Districts/Bihar.geojson"
)
  .then((r) => r.json())
  .then((g) => {
    L.geoJSON(g, { style: { color: "#333", weight: 1, fillOpacity: 0 } }).addTo(
      map
    );
  });

/* MAIN LOAD */
function loadData(type) {
  currentType = type;
  awsBtn.className = type === "AWS" ? "btn-primary" : "btn-outline";
  argBtn.className = type === "ARG" ? "btn-primary" : "btn-outline";

  const date = datePicker.value;
  const status = statusFilter.value;

  /* SUMMARY */
  fetch(`/api/station-summary?type=${type}&date=${date}`)
    .then((r) => r.json())
    .then((d) => {
      document.getElementById("working").innerText = d.working;
      document.getElementById("not-working").innerText = d.not_working;
    });

  /* COMPANY TABLE */
  fetch(`/api/company-summary?type=${type}&date=${date}`)
    .then((r) => r.json())
    .then((data) => {
      const tbody = document.querySelector("#companyTable tbody");
      tbody.innerHTML = "";
      data.forEach((row) => {
        tbody.innerHTML += `
                <tr>
                    <td>${row.company}</td>
                    <td>${row.total}</td>
                    <td style="color:green">${row.working}</td>
                    <td style="color:red">${row.not_working}</td>
                </tr>`;
      });
    });

  /* MAP DATA */
  let url = `/api/map-data?type=${type}&date=${date}`;
  if (status !== "All") url += `&status=${status}`;

  fetch(url)
    .then((r) => r.json())
    .then((data) => {
      markers.forEach((m) => map.removeLayer(m));
      markers = [];
      data.forEach((s) => {
        let m = L.circleMarker([s.lat, s.lon], {
          radius: 3,
          color: s.status === "Working" ? "green" : "red",
          fillOpacity: 0.7,
          className: s.status === "Working" ? "blink-green" : "blink-red",
        })
          .bindPopup(
            `
                District: ${s.district}<br>
                Block: ${s.block}<br>
                Status: ${s.status}
            `
          )
          .addTo(map);
        markers.push(m);
      });
    });
}

/* EVENTS */
awsBtn.onclick = () => loadData("AWS");
argBtn.onclick = () => loadData("ARG");
datePicker.onchange = () => loadData(currentType);
statusFilter.onchange = () => loadData(currentType);

/* INITIAL LOAD */
loadData("AWS");
