import { api, patch, post, put } from "./api.js";
import * as cityMap from "./map.js";

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const state = { network: null, incidents: [], analytics: null, trace: null, traceTimer: null, toastTimer: null };
const pageNames = {
  overview: "Overview", map: "Live City Map", dispatch: "Emergency Dispatch",
  routes: "Route Optimizer", hospitals: "Hospital Allocation", evacuation: "Evacuation Planner",
  lab: "Algorithm Lab", benchmark: "Benchmarking", network: "Network Manager",
  analytics: "Analytics", about: "About ADSA",
};

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[char]);
}

function notify(message, error = false) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.toggle("error", error);
  toast.classList.add("show");
  clearTimeout(state.toastTimer);
  state.toastTimer = setTimeout(() => toast.classList.remove("show"), 3500);
}

async function action(work, successMessage) {
  try {
    const result = await work();
    if (successMessage) notify(successMessage);
    return result;
  } catch (error) {
    notify(error.message, true);
    return null;
  }
}

function setPage(name) {
  if (!pageNames[name]) return;
  $$(".page").forEach((page) => page.classList.toggle("active", page.id === `page-${name}`));
  $$(".nav-link").forEach((link) => link.classList.toggle("active", link.dataset.page === name));
  $("#top-page-name").textContent = pageNames[name];
  if (name === "map" || name === "overview") cityMap.setNetwork(state.network);
}

function statusClass(value) {
  return String(value || "").toLowerCase().replaceAll(" ", "-");
}

function statusPill(value) {
  return `<span class="status ${statusClass(value)}">${escapeHtml(value)}</span>`;
}

function renderKpis(summary, target = "#kpi-grid") {
  const items = [
    ["Network locations", summary.locations, "Vertices in the city graph", "⌖"],
    ["Directed roads", summary.road_connections, `${summary.open_roads} currently open`, "⇢"],
    ["Active incidents", summary.active_incidents, "Pending or in progress", "✚"],
    ["Available ambulances", summary.available_ambulances, `${summary.dispatched_ambulances} assigned`, "A"],
    ["Hospital capacity", summary.available_beds, `${summary.hospitals} accepting facilities`, "＋"],
  ];
  $(target).innerHTML = items.map(([label, value, sub, icon]) => `
    <article class="kpi"><div class="kpi-top"><span class="kpi-label">${label}</span><span class="kpi-icon">${icon}</span></div>
    <div class="kpi-value">${value ?? "—"}</div><div class="kpi-sub">${sub}</div></article>`).join("");
}

function populateLocationSelects() {
  const locations = state.network.locations;
  const options = locations.map((location) =>
    `<option value="${escapeHtml(location.id)}">${escapeHtml(location.id)} · ${escapeHtml(location.name)}</option>`).join("");
  $$(".location-options").forEach((select) => {
    const previous = select.value;
    select.innerHTML = options;
    if (locations.some((item) => item.id === previous)) select.value = previous;
  });
  if ($("#route-source")) $("#route-source").value = "M01";
  if ($("#route-destination")) $("#route-destination").value = "M36";
  if ($("#lab-source")) $("#lab-source").value = "M01";
  if ($("#lab-destination")) $("#lab-destination").value = "M36";
  if ($("#connectivity-source")) $("#connectivity-source").value = "M01";
  const residential = locations.filter((item) => item.kind === "residential");
  $("#zone-options").innerHTML = residential.map((location, index) => `
    <label class="check-option"><input type="checkbox" name="zone" value="${escapeHtml(location.id)}" ${index === 0 ? "checked" : ""}>
    ${escapeHtml(location.name)} <small>Zone ${escapeHtml(location.id)}</small></label>`).join("");
  $("#shelter-options").innerHTML = state.network.shelters.map((shelter, index) => `
    <div class="check-option"><input id="select-${escapeHtml(shelter.id)}" type="checkbox" name="shelter" value="${escapeHtml(shelter.id)}" ${index === 0 ? "checked" : ""}>
    <label for="select-${escapeHtml(shelter.id)}">${escapeHtml(shelter.name)} <small>${shelter.capacity} default</small></label>
    <input class="input shelter-capacity" type="number" min="0" step="1" data-shelter-capacity="${escapeHtml(shelter.id)}" value="${shelter.capacity}" aria-label="${escapeHtml(shelter.name)} intake capacity"></div>`).join("");
  $("#hospital-incident").innerHTML = state.incidents.filter((item) => !["Resolved", "Cancelled"].includes(item.status))
    .map((incident) => `<option value="${incident.id}">#${incident.id} · ${escapeHtml(incident.incident_type)} · ${escapeHtml(incident.location_id)}</option>`).join("")
    || '<option value="">No active incidents</option>';
}

function renderIncidents() {
  state.incidents = state.incidents || [];
  const active = state.incidents.filter((item) => !["Resolved", "Cancelled"].includes(item.status));
  $("#overview-incidents").innerHTML = active.length ? `<table class="table"><thead><tr><th>INCIDENT</th><th>LOCATION</th><th>SEVERITY</th><th>STATUS</th></tr></thead><tbody>
    ${active.slice(0, 5).map((incident) => `<tr><td>#${incident.id} ${escapeHtml(incident.incident_type)}</td><td>${escapeHtml(incident.location_id)}</td><td>${statusPill(incident.severity)}</td><td>${statusPill(incident.status)}</td></tr>`).join("")}</tbody></table>`
    : '<div class="empty-state">No active incidents in the simulation.</div>';
  $("#incident-table").innerHTML = state.incidents.length ? `<table class="table"><thead><tr><th>ID / TYPE</th><th>LOCATION</th><th>SEVERITY</th><th>UNIT / HOSPITAL</th><th>STATUS</th><th>ACTIONS</th></tr></thead><tbody>
    ${state.incidents.map((incident) => {
      let actionButtons = "";
      if (incident.status === "Pending") actionButtons = `<button class="button primary small" data-action="preview-dispatch" data-id="${incident.id}">Find unit</button>`;
      else if (incident.status === "Dispatched") actionButtons = `<button class="button secondary small" data-action="status" data-status="On Scene" data-id="${incident.id}">On Scene</button>`;
      else if (incident.status === "On Scene") actionButtons = `<button class="button secondary small" data-action="status" data-status="Transporting" data-id="${incident.id}">Transport</button><button class="button secondary small" data-action="status" data-status="Resolved" data-id="${incident.id}">Resolve</button>`;
      else if (incident.status === "Transporting") actionButtons = `<button class="button secondary small" data-action="status" data-status="Resolved" data-id="${incident.id}">Resolve</button>`;
      if (!["Resolved", "Cancelled"].includes(incident.status)) actionButtons += ` <button class="text-button" data-action="status" data-status="Cancelled" data-id="${incident.id}">Cancel</button>`;
      return `<tr><td>#${incident.id}<br>${escapeHtml(incident.incident_type)}</td><td>${escapeHtml(incident.location_id)}</td><td>${statusPill(incident.severity)}</td>
        <td>${escapeHtml(incident.ambulance_label || "—")}<br><small>${escapeHtml(incident.hospital_name || "")}</small></td>
        <td>${statusPill(incident.status)}</td><td><div class="table-actions">${actionButtons || "—"}</div></td></tr>`;
    }).join("")}</tbody></table>` : '<div class="empty-state">No incidents recorded. Create one above to begin.</div>';
  $("#hospital-incident").innerHTML = active.map((incident) =>
    `<option value="${incident.id}">#${incident.id} · ${escapeHtml(incident.incident_type)} · ${escapeHtml(incident.location_id)}</option>`).join("")
    || '<option value="">No active incidents</option>';
}

function renderAmbulances(ambulances) {
  $("#ambulance-count").textContent = `${ambulances.length} units`;
  $("#ambulance-list").innerHTML = ambulances.map((unit) => `
    <div class="unit-card"><div><div class="unit-name">${escapeHtml(unit.id)}</div><div class="unit-meta">${escapeHtml(unit.location_id)} · ${escapeHtml(unit.capabilities)}</div></div>${statusPill(unit.status)}</div>`).join("");
}

function renderHospitals(hospitals) {
  $("#hospital-list").innerHTML = hospitals.map((hospital) => `
    <div class="hospital-card"><div><div class="unit-name">${escapeHtml(hospital.name)}</div>
    <div class="unit-meta">${escapeHtml(hospital.location_id)} · ${escapeHtml(hospital.specialties.join(", "))}</div></div>
    <span class="status ${hospital.available_beds ? "available" : "critical"}">${hospital.available_beds}/${hospital.total_beds} beds</span></div>`).join("");
}

function renderActivity(events) {
  $("#activity-list").innerHTML = events.length ? events.map((event) => {
    const icon = event.event_type === "dispatch" ? "A" : event.event_type === "road" ? "⇢" : event.event_type === "hospital" ? "＋" : "•";
    return `<div class="activity-item"><span class="activity-icon">${icon}</span><div class="activity-copy">${escapeHtml(event.message)}<small>${escapeHtml(event.created_at)}</small></div></div>`;
  }).join("") : '<div class="empty-state">No activity recorded yet.</div>';
}

async function refreshOperationalData() {
  const [summary, analytics, incidentResponse, ambulanceResponse, hospitalResponse] = await Promise.all([
    api("/dashboard/summary"), api("/analytics/overview"), api("/incidents"),
    api("/ambulances"), api("/hospitals"),
  ]);
  state.analytics = analytics;
  state.incidents = incidentResponse.incidents;
  if (state.network) {
    state.network.ambulances = ambulanceResponse.ambulances;
    cityMap.setNetwork(state.network);
  }
  renderKpis(summary);
  renderIncidents();
  renderAmbulances(ambulanceResponse.ambulances);
  renderHospitals(hospitalResponse.hospitals);
  renderActivity(analytics.activity);
  return summary;
}

function resultMetrics(result) {
  const costLabel = result.metric === "distance" ? "Selected distance" : "Selected travel time";
  const costValue = result.cost === null ? "Unreachable" : `${Number(result.cost).toFixed(2)} ${result.metric === "distance" ? "km" : "min"}`;
  return `<div class="route-summary">
    <div class="metric-box"><strong>${escapeHtml(costValue)}</strong><small>${costLabel}</small></div>
    <div class="metric-box"><strong>${result.total_travel_minutes == null ? "—" : `${result.total_travel_minutes.toFixed(2)} min`}</strong><small>Travel time</small></div>
    <div class="metric-box"><strong>${result.total_distance_km == null ? "—" : `${result.total_distance_km.toFixed(2)} km`}</strong><small>Road distance</small></div>
    <div class="metric-box"><strong>${result.segments ?? 0}</strong><small>Road segments</small></div>
    <div class="metric-box"><strong>${Number(result.stats?.execution_ms || 0).toFixed(3)} ms</strong><small>Backend execution</small></div>
  </div>`;
}

function renderRoute(result, compareResults = []) {
  const routePanel = $("#route-result");
  if (!result.reachable) {
    routePanel.innerHTML = '<div class="disclaimer">No path exists between these locations on the current open-road network.</div>';
    $("#map-route-summary").textContent = "Destination unreachable on current open roads.";
    cityMap.setRoute(result);
    return;
  }
  const path = result.path.map((node) => `<span>${escapeHtml(node)}</span>`).join('<span class="path-arrow">→</span>');
  const compareHtml = compareResults.length ? `<div class="comparison-list"><div class="hint">SAME NETWORK SNAPSHOT · ALGORITHM COMPARISON</div>
    ${compareResults.map((item) => `<div class="comparison-item"><span>${escapeHtml(item.algorithm)}</span><span>${item.cost == null ? "Unreachable" : Number(item.cost).toFixed(3)}</span><span>${Number(item.stats.execution_ms).toFixed(3)} ms</span></div>`).join("")}</div>` : "";
  const alternatives = result.alternative_routes?.length ? `<div class="comparison-list"><div class="hint">ALTERNATIVE OPEN-ROAD ROUTES</div>${result.alternative_routes.map((item) =>
    `<div class="comparison-item"><span>${escapeHtml(item.path.join(" → "))}</span><span>${Number(item.cost).toFixed(2)} ${result.metric}</span><span>${item.segments} roads</span></div>`).join("")}</div>` : "";
  routePanel.innerHTML = `${resultMetrics(result)}<div class="hint">Algorithm: ${escapeHtml(result.stats.algorithm)} · ${result.stats.edge_checks} edge checks · ${result.stats.relaxations} relaxations · ${result.visited.length} visited nodes</div><div class="path-list">${path}</div>${compareHtml}${alternatives}`;
  $("#map-route-summary").innerHTML = `${resultMetrics(result)}<div class="path-list">${path}</div>`;
  cityMap.setRoute(result);
}

function renderHospitalRecommendations(result) {
  const container = $("#hospital-results");
  if (result.allocation) {
    container.innerHTML = `<div class="disclaimer">This incident already has a hospital allocation.</div>
      <div class="unit-card" style="margin-top:8px"><div><div class="unit-name">${escapeHtml(result.allocation.name)}</div>
      <div class="unit-meta">${escapeHtml(result.allocation.location_id)} · ${result.allocation.beds_reserved} bed(s) reserved · allocated ${escapeHtml(result.allocation.created_at)}</div></div>
      <span class="status available">Allocated</span></div>`;
    return;
  }
  if (!result.recommendation) {
    container.innerHTML = `<div class="disclaimer">No suitable reachable hospital with available capacity was found.</div>
      <div class="body-copy">${result.rejected.map((item) => `${escapeHtml(item.hospital_id)}: ${escapeHtml(item.reason)}`).join("<br>")}</div>`;
    return;
  }
  const items = [result.recommendation, ...result.alternatives];
  container.innerHTML = `<div class="hint">GREEDY RANKING · ETA FIRST, AVAILABLE BEDS AS TIE-BREAK</div>${items.map((item, index) => `
    <div class="unit-card" style="margin-top:8px"><div><div class="unit-name">${index === 0 ? "★ Recommended · " : ""}${escapeHtml(item.name)}</div>
    <div class="unit-meta">${item.eta_minutes.toFixed(2)} min · ${item.available_beds} beds · route ${item.route.join(" → ")}</div></div>
    <button class="button ${index === 0 ? "primary" : "secondary"} small" data-action="allocate" data-incident="${result.incident_id}" data-hospital="${escapeHtml(item.hospital_id)}">Allocate</button></div>`).join("")}
    <p class="hint">Greedy per-incident ranking; this is not a globally optimal multi-incident allocation.</p>`;
}

function renderEvacuation(result) {
  cityMap.setFlow(result.used_road_capacities);
  const shelterFlow = result.used_capacities.filter((item) => item.target === "__EVAC_SINK__");
  const roadUsage = result.used_road_capacities.filter((item) => item.flow > 0).map((item) =>
    `${escapeHtml(item.source)} → ${escapeHtml(item.target)}: ${item.flow}/${item.capacity}`).join("<br>");
  $("#evacuation-results").innerHTML = `<div class="evac-kpis">
    <div class="evac-value"><strong>${result.maximum_flow.toLocaleString()}</strong><small>Maximum throughput / period</small></div>
    <div class="evac-value"><strong>${result.unserved_demand.toLocaleString()}</strong><small>Unserved population demand</small></div>
    <div class="evac-value"><strong>${result.augmenting_paths.length}</strong><small>Augmenting paths</small></div></div>
    <h3>Augmenting paths</h3>${result.augmenting_paths.map((path) => `<div class="activity-item"><span class="activity-icon">${path.bottleneck}</span><div class="activity-copy">${escapeHtml(path.path.join(" → "))}<small>Bottleneck: ${path.bottleneck}</small></div></div>`).join("") || '<div class="hint">No flow path found.</div>'}
    <h3>Minimum cut</h3><div class="body-copy">${result.min_cut.edges.map((edge) => `${escapeHtml(edge.source)} → ${escapeHtml(edge.target)} (${edge.capacity})`).join("<br>") || "No limiting cut edge reported."}</div>
    <h3>Shelter intake used</h3><div class="body-copy">${shelterFlow.map((item) => `${escapeHtml(item.source)}: ${item.flow}/${item.capacity}`).join("<br>")}</div>
    <h3>Used road capacities</h3><div class="body-copy">${roadUsage || "No evacuation road flow was used."}</div>
    <h3>Edmonds–Karp execution</h3><div class="body-copy">${result.stats.iterations} BFS iterations · ${result.stats.edge_checks} residual-edge checks · ${result.stats.augmentations} augmentations · ${result.stats.execution_ms.toFixed(3)} ms</div>
    <p class="disclaimer">${escapeHtml(result.disclaimer)}</p>`;
}

function drawBenchmarkChart(result) {
  const colors = ["#4cc5d0", "#6688ff", "#e7b65b", "#af8ade"];
  if (result.growth_results) {
    const sizes = result.growth_results;
    const names = Object.keys(sizes[0].algorithms);
    const width = 620, height = 220, left = 48, top = 20, plotW = 540, plotH = 155;
    const maxValue = Math.max(0.001, ...sizes.flatMap((item) => names.map((name) => item.algorithms[name].median_ms)));
    const x = (index) => left + (sizes.length <= 1 ? plotW / 2 : index / (sizes.length - 1) * plotW);
    const y = (value) => top + plotH - value / maxValue * plotH;
    let svg = `<svg class="benchmark-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="Measured runtime growth across graph sizes">`;
    for (let tick = 0; tick <= 4; tick++) {
      const tickY = top + tick * plotH / 4;
      svg += `<line x1="${left}" y1="${tickY}" x2="${left + plotW}" y2="${tickY}" stroke="#273544" stroke-width="1"/><text x="3" y="${tickY + 3}" fill="#8090a1" font-size="9">${(maxValue * (1 - tick / 4)).toFixed(2)}</text>`;
    }
    sizes.forEach((item, index) => {
      svg += `<text x="${x(index)}" y="${top + plotH + 17}" text-anchor="middle" fill="#8090a1" font-size="9">${item.size} V</text>`;
    });
    names.forEach((name, algorithmIndex) => {
      const points = sizes.map((item, index) => `${x(index)},${y(item.algorithms[name].median_ms)}`).join(" ");
      svg += `<polyline points="${points}" fill="none" stroke="${colors[algorithmIndex]}" stroke-width="2"/>`;
      sizes.forEach((item, index) => {
        const value = item.algorithms[name].median_ms;
        svg += `<circle cx="${x(index)}" cy="${y(value)}" r="3.5" fill="${colors[algorithmIndex]}"><title>${escapeHtml(name)} · ${item.size} vertices: ${value.toFixed(3)} ms median</title></circle>`;
      });
    });
    svg += `</svg><div class="map-legend">${names.map((name, index) => `<span class="legend-item"><i class="legend-dot" style="background:${colors[index]}"></i>${escapeHtml(name.replaceAll("_", " "))}</span>`).join("")}</div>`;
    $("#benchmark-chart").innerHTML = svg;
    $("#benchmark-details").textContent = `Growth sweep · sizes 25, 50, 100, 250, 500 · degree ${result.average_degree} · seed ${result.seed} · ${result.repetitions} repetitions per size. ${result.note} Timings are measured, and complexity bounds remain theoretical.`;
    return;
  }
  const entries = Object.entries(result.algorithms);
  const width = 620, height = 220, left = 46, top = 20, plotW = 545, plotH = 155;
  const maxValue = Math.max(0.001, ...entries.flatMap(([, value]) => value.samples_ms));
  const x = (index) => left + (entries[0][1].samples_ms.length <= 1 ? plotW / 2 : (index / (entries[0][1].samples_ms.length - 1)) * plotW);
  const y = (value) => top + plotH - (value / maxValue) * plotH;
  let svg = `<svg class="benchmark-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="Measured benchmark sample timings line chart">`;
  for (let tick = 0; tick <= 4; tick++) {
    const tickY = top + tick * plotH / 4;
    svg += `<line x1="${left}" y1="${tickY}" x2="${left + plotW}" y2="${tickY}" stroke="#273544" stroke-width="1"/><text x="3" y="${tickY + 3}" fill="#8090a1" font-size="9">${(maxValue * (1 - tick / 4)).toFixed(2)}</text>`;
  }
  entries[0][1].samples_ms.forEach((_, index) => {
    svg += `<text x="${x(index)}" y="${top + plotH + 17}" text-anchor="middle" fill="#8090a1" font-size="9">Run ${index + 1}</text>`;
  });
  entries.forEach(([name, value], index) => {
    const points = value.samples_ms.map((sample, sampleIndex) => `${x(sampleIndex)},${y(sample)}`).join(" ");
    svg += `<polyline points="${points}" fill="none" stroke="${colors[index]}" stroke-width="2"/>`;
    value.samples_ms.forEach((sample, sampleIndex) => {
      svg += `<circle cx="${x(sampleIndex)}" cy="${y(sample)}" r="3.5" fill="${colors[index]}"><title>${escapeHtml(name)} sample ${sampleIndex + 1}: ${sample.toFixed(3)} ms</title></circle>`;
    });
  });
  svg += `</svg><div class="map-legend">${entries.map(([name], index) => `<span class="legend-item"><i class="legend-dot" style="background:${colors[index]}"></i>${escapeHtml(name.replaceAll("_", " "))}</span>`).join("")}</div>`;
  $("#benchmark-chart").innerHTML = svg;
  $("#benchmark-details").innerHTML = `Seed ${result.seed} · ${result.size} vertices · ${result.edge_count} directed edges · mean degree ${result.average_degree} · ${result.repetitions} repetitions. ${escapeHtml(result.note)} Warm-up and trace-disabled execution are used.`;
}

function renderTheory(data) {
  const html = `<table class="table"><thead><tr><th>ALGORITHM</th><th>TIME COMPLEXITY</th><th>APPLICATION</th></tr></thead><tbody>${data.algorithms.map((item) =>
    `<tr><td>${escapeHtml(item.name)}</td><td class="complexity">${escapeHtml(item.complexity)}</td><td>${escapeHtml(item.feature)}</td></tr>`).join("")}</tbody></table>`;
  $("#complexity-table").innerHTML = html;
  $("#theory-table").innerHTML = html;
}

async function loadNetwork() {
  const network = await api("/network");
  state.network = network;
  cityMap.setNetwork(network);
  populateLocationSelects();
  $("#map-status").textContent = `${network.locations.length} locations · ${network.open_road_count} open / ${network.directed_road_count} directed roads`;
  await Promise.all([renderRoads(), loadAlgorithmsTheory()]);
}

async function loadAlgorithmsTheory() {
  renderTheory(await api("/algorithms/theory"));
}

async function renderRoads() {
  const { roads } = await api("/roads");
  $("#road-count").textContent = `${roads.length} directed roads`;
  $("#road-table").classList.add("network-table");
  $("#road-table").innerHTML = `<table class="table"><thead><tr><th>ID / DIRECTION</th><th>STATUS</th><th>DISTANCE KM</th><th>TIME MIN</th><th>CAPACITY / PERIOD</th><th>MANAGE</th></tr></thead><tbody>
    ${roads.map((road) => `<tr><td>#${road.id}<br>${escapeHtml(road.source_id)} → ${escapeHtml(road.target_id)}</td>
    <td>${road.is_open ? '<span class="status available">Open</span>' : '<span class="status critical">Blocked</span>'}</td>
    <td>${road.distance_km.toFixed(2)}</td><td>${road.travel_minutes.toFixed(1)}</td><td>${road.evacuation_capacity}</td>
    <td><div class="table-actions"><button class="button secondary small" data-action="${road.is_open ? "close-road" : "open-road"}" data-road="${road.id}">${road.is_open ? "Close" : "Reopen"}</button>
    <button class="text-button" data-action="edit-road" data-road="${road.id}" data-distance="${road.distance_km}" data-time="${road.travel_minutes}" data-capacity="${road.evacuation_capacity}">Edit</button></div></td></tr>`).join("")}</tbody></table>`;
}

function drawEducationalGraph(events, index) {
  const svg = $("#education-map");
  const nodes = state.educationalNodes || [];
  const edges = state.educationalEdges || [];
  const positions = { A: [120, 250], B: [350, 115], C: [350, 385], D: [650, 250] };
  const current = events[index] || null;
  const seen = new Set(["A"]);
  const tentative = Object.fromEntries(nodes.map((node) => [node, null]));
  tentative.A = 0;
  events.slice(0, index + 1).forEach((event) => {
    if (event.node) seen.add(event.node);
    if (event.from) seen.add(event.from);
    if (event.type === "distance_updated") tentative[event.node] = event.distance;
  });
  if (current?.type === "negative_cycle_detected") {
    nodes.forEach((node) => { tentative[node] = state.trace.result.distances[node]; });
  }
  svg.replaceChildren();
  svg.setAttribute("viewBox", "0 0 780 500");
  const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
  const marker = document.createElementNS("http://www.w3.org/2000/svg", "marker");
  marker.setAttribute("id", "edu-arrow");
  marker.setAttribute("viewBox", "0 0 10 10");
  marker.setAttribute("refX", "8");
  marker.setAttribute("refY", "5");
  marker.setAttribute("markerWidth", "6");
  marker.setAttribute("markerHeight", "6");
  marker.setAttribute("orient", "auto");
  const arrow = document.createElementNS("http://www.w3.org/2000/svg", "path");
  arrow.setAttribute("d", "M 0 0 L 10 5 L 0 10 z");
  arrow.setAttribute("fill", "#91a4b8");
  marker.append(arrow);
  defs.append(marker);
  svg.append(defs);
  edges.forEach((edge) => {
    let [x1, y1] = positions[edge.source], [x2, y2] = positions[edge.target];
    if (edge.source === "B" && edge.target === "C") { x1 += 13; x2 += 13; }
    if (edge.source === "C" && edge.target === "B") { x1 -= 13; x2 -= 13; }
    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    const active = current?.from === edge.source && current?.node === edge.target;
    const cycle = current?.type === "negative_cycle_detected" && current.path?.some((node, i) =>
      node === edge.source && current.path[i + 1] === edge.target);
    line.setAttribute("x1", x1); line.setAttribute("y1", y1);
    line.setAttribute("x2", x2); line.setAttribute("y2", y2);
    line.setAttribute("marker-end", "url(#edu-arrow)");
    line.setAttribute("class", `education-edge${active ? " active" : ""}${cycle ? " cycle" : ""}`);
    svg.append(line);
    const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
    label.setAttribute("x", (x1 + x2) / 2);
    label.setAttribute("y", (y1 + y2) / 2 - 7);
    label.setAttribute("class", "education-edge-label");
    label.textContent = String(edge.weight);
    svg.append(label);
  });
  nodes.forEach((node) => {
    const [x, y] = positions[node];
    const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    circle.setAttribute("cx", x); circle.setAttribute("cy", y); circle.setAttribute("r", "23");
    circle.setAttribute("class", `education-node${seen.has(node) ? " visited" : ""}${current?.node === node ? " active" : ""}`);
    svg.append(circle);
    const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
    label.setAttribute("x", x); label.setAttribute("y", y + 5);
    label.setAttribute("text-anchor", "middle"); label.setAttribute("fill", "#07131c");
    label.setAttribute("font-size", "15"); label.setAttribute("font-weight", "700");
    label.textContent = node;
    svg.append(label);
    const distance = tentative[node];
    const cost = document.createElementNS("http://www.w3.org/2000/svg", "text");
    cost.setAttribute("x", x); cost.setAttribute("y", y + 42);
    cost.setAttribute("text-anchor", "middle"); cost.setAttribute("fill", seen.has(node) ? "#c8d6e0" : "#6e8192");
    cost.setAttribute("font-size", "12");
    cost.textContent = distance === null || distance === undefined ? "d = ∞" : `d = ${distance}`;
    svg.append(cost);
  });
}

function renderTraceState() {
  const trace = state.trace;
  const events = trace?.events || [];
  const index = trace?.index ?? -1;
  const educationMode = trace?.algorithm === "bellman_ford";
  $("#city-trace-map").style.display = educationMode ? "none" : "";
  $("#education-map").style.display = educationMode ? "" : "none";
  if (educationMode) drawEducationalGraph(events, index);
  $("#step-badge").textContent = `STEP ${Math.max(0, index + 1)} / ${events.length}`;
  $("#trace-previous").disabled = index < 0;
  $("#trace-next").disabled = index >= events.length - 1;
  $("#trace-play").disabled = !events.length;
  $("#trace-play").textContent = state.traceTimer ? "Ⅱ Pause" : "▶ Play";
  if (index >= 0 && events[index]) {
    const event = events[index];
    const visited = events.slice(0, index + 1).filter((item) => item.type === "node_visited").map((item) => item.node);
    if (!educationMode) cityMap.setTrace([...new Set(visited)], event.node || event.from || null,
      event.from && event.node ? [event.from, event.node] : null);
    $("#trace-event").innerHTML = `<b>${escapeHtml(event.type.replaceAll("_", " "))}</b><br>${event.node ? `Location: ${escapeHtml(event.node)}<br>` : ""}${event.from ? `From: ${escapeHtml(event.from)}<br>` : ""}${event.distance != null ? `Tentative cost: ${Number(event.distance).toFixed(3)}<br>` : ""}${event.path ? `Path: ${escapeHtml(event.path.join(" → "))}<br>` : ""}${event.bottleneck != null ? `Bottleneck capacity: ${event.bottleneck}` : ""}`;
    $("#trace-status").textContent = `${trace.algorithm} · event ${index + 1} of ${events.length}`;
  } else {
    if (!educationMode) cityMap.setTrace([], null);
    $("#trace-event").textContent = trace ? "Trace ready. Press Next step or Play." : "Events will be shown here as you step through the execution.";
  }
}

function stopTrace() {
  if (state.traceTimer) clearInterval(state.traceTimer);
  state.traceTimer = null;
}

async function initialize() {
  $("#clock").textContent = new Date().toLocaleString(undefined, { weekday: "short", hour: "2-digit", minute: "2-digit" });
  const [network] = await Promise.all([loadNetwork(), refreshOperationalData()]);
  if (!network) return;
}

$("#navigation").addEventListener("click", (event) => {
  const link = event.target.closest("[data-page]");
  if (link) setPage(link.dataset.page);
});
document.body.addEventListener("click", (event) => {
  const link = event.target.closest("[data-go]");
  if (link) setPage(link.dataset.go);
});

cityMap.setSelectionHandler((location) => {
  $("#location-details").innerHTML = `<div class="metric-box"><strong>${escapeHtml(location.id)} · ${escapeHtml(location.name)}</strong><small>${escapeHtml(location.kind.replaceAll("_", " "))}</small></div><div class="body-copy">Coordinates: ${location.latitude.toFixed(4)}, ${location.longitude.toFixed(4)}<br>Graph vertex: ${escapeHtml(location.id)}</div>`;
  const mode = $("#map-pick-mode").value;
  if (mode === "source") $("#route-source").value = location.id;
  if (mode === "destination") $("#route-destination").value = location.id;
  if (mode !== "none") {
    $("#map-status").textContent = `Selected ${mode}: ${location.id} · ${location.name}`;
    $("#map-pick-mode").value = "none";
  }
});

$("#incident-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const data = Object.fromEntries(new FormData(form).entries());
  if (!data.required_specialty) delete data.required_specialty;
  const created = await action(() => post("/incidents", data), "Simulation incident created.");
  if (created) {
    form.reset();
    await refreshOperationalData();
    populateLocationSelects();
  }
});

$("#incident-table").addEventListener("click", async (event) => {
  const button = event.target.closest("[data-action]");
  if (!button) return;
  const id = button.dataset.id;
  if (button.dataset.action === "preview-dispatch") {
    const options = await action(() => post(`/incidents/${id}/dispatch-options`, {}));
    if (!options) return;
    const choices = [options.selected, ...options.alternatives].map((item, index) =>
      `${index === 0 ? "Recommended" : `Alternative ${index}`}: ${item.ambulance_id} · ${item.eta_minutes.toFixed(2)} min · ${item.route.join(" → ")}`).join("\n");
    if (!confirm(`${choices}\n\nConfirm dispatch to ${options.selected.ambulance_id}?`)) return;
    const result = await action(() => post(`/incidents/${id}/dispatch`, {}));
    if (result) {
      notify(`${result.selected.ambulance_id} dispatched · ETA ${result.selected.eta_minutes.toFixed(2)} min${result.alternatives.length ? ` · ${result.alternatives.length} alternatives` : ""}`);
      cityMap.setRoute({ path: result.selected.route, visited: [] });
    }
  } else if (button.dataset.action === "status") {
    const result = await action(() => patch(`/incidents/${id}/status`, { status: button.dataset.status }), `Incident #${id} set to ${button.dataset.status}.`);
    if (result) await refreshOperationalData();
  }
  await refreshOperationalData();
});
$("#refresh-incidents").addEventListener("click", () => action(refreshOperationalData, "Incident and unit data refreshed."));

$("#route-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const body = { source: form.get("source"), destination: form.get("destination"), metric: form.get("metric"), algorithm: form.get("algorithm") };
  const compare = form.has("compare");
  const response = await action(() => compare ? post("/routes/compare", body) : post("/routes/shortest-path", body));
  if (!response) return;
  const routes = compare ? response.results : [];
  const selected = compare ? [...routes].sort((a, b) => (a.cost ?? Infinity) - (b.cost ?? Infinity) || a.stats.execution_ms - b.stats.execution_ms)[0] : response;
  if (compare) selected.alternative_routes = response.alternative_routes;
  renderRoute(selected, routes);
});

$("#clear-route").addEventListener("click", () => {
  cityMap.clearHighlights();
  $("#map-route-summary").textContent = "No route calculated.";
  $("#route-result").textContent = "Set route endpoints to get started.";
});
$("#zoom-in").addEventListener("click", () => cityMap.zoom(0.2));
$("#zoom-out").addEventListener("click", () => cityMap.zoom(-0.2));
$("#zoom-reset").addEventListener("click", () => { cityMap.zoom(-2); });

$("#hospital-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const id = $("#hospital-incident").value;
  if (!id) return notify("Create an incident before requesting a hospital recommendation.", true);
  const result = await action(() => post(`/incidents/${id}/hospital-recommendations`, {}));
  if (result) renderHospitalRecommendations(result);
});
$("#hospital-results").addEventListener("click", async (event) => {
  const button = event.target.closest('[data-action="allocate"]');
  if (!button) return;
  const result = await action(() => post(`/incidents/${button.dataset.incident}/allocate-hospital`, { hospital_id: button.dataset.hospital }), "Hospital capacity reserved for the incident.");
  if (result) {
    const recommendations = await action(() => post(`/incidents/${button.dataset.incident}/hospital-recommendations`, {}));
    if (recommendations) renderHospitalRecommendations(recommendations);
    await refreshOperationalData();
  }
});
$("#allocate-hospital-queue").addEventListener("click", async () => {
  const result = await action(() => post("/hospitals/allocate-queue", {}));
  if (!result) return;
  notify(`Processed ${result.results.length} active incidents in severity / creation-time order.`);
  $("#hospital-results").innerHTML = `<div class="body-copy"><b>Greedy scheduling heuristic:</b> ${escapeHtml(result.heuristic)}</div>${result.results.map((item) =>
    `<div class="activity-item"><span class="activity-icon">${item.status === "allocated" ? "＋" : "!"}</span><div class="activity-copy">Incident #${item.incident_id}: ${escapeHtml(item.status)}${item.hospital_name ? ` · ${escapeHtml(item.hospital_name)}` : ` · ${escapeHtml(item.reason)}`}</div></div>`).join("")}`;
  await refreshOperationalData();
});

$("#evacuation-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const population = Number($("#population-demand").value);
  if (!Number.isInteger(population) || population <= 0) return notify("Population demand must be a positive whole number.", true);
  const zones = $$('input[name="zone"]:checked').map((input) => ({ location_id: input.value, population }));
  const shelter_ids = $$('input[name="shelter"]:checked').map((input) => input.value);
  const shelter_capacities = Object.fromEntries(shelter_ids.map((id) =>
    [id, Number($(`[data-shelter-capacity="${id}"]`).value)]));
  const result = await action(() => post("/evacuation/simulate", { zones, shelter_ids, shelter_capacities }));
  if (result) renderEvacuation(result);
});

function updateLabDestinationVisibility() {
  $(".route-lab-only").style.display = ["dijkstra_heap", "dijkstra_array", "astar"].includes($("#lab-algorithm").value) ? "" : "none";
  $(".bf-lab-only").style.display = $("#lab-algorithm").value === "bellman_ford" ? "" : "none";
}
$("#lab-algorithm").addEventListener("change", updateLabDestinationVisibility);
updateLabDestinationVisibility();
$("#lab-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  stopTrace();
  const algorithm = $("#lab-algorithm").value;
  const source = $("#lab-source").value;
  let events = [];
  let result;
  if (["dijkstra_heap", "dijkstra_array", "astar"].includes(algorithm)) {
    result = await action(() => post("/algorithms/visualize", {
      source, destination: $("#lab-destination").value, algorithm, metric: "time",
    }));
    if (!result) return;
    events = result.trace || [];
  } else if (algorithm === "bellman_ford") {
    const cyclic = $("#bf-scenario").value === "cycle";
    const nodes = ["A", "B", "C", "D"];
    const edges = cyclic
      ? [{ source: "A", target: "B", weight: 2 }, { source: "B", target: "C", weight: -4 }, { source: "C", target: "B", weight: 1 }, { source: "C", target: "D", weight: 2 }]
      : [{ source: "A", target: "B", weight: 4 }, { source: "A", target: "C", weight: 5 }, { source: "B", target: "C", weight: -2 }, { source: "C", target: "D", weight: 3 }];
    result = await action(() => post("/algorithms/bellman-ford", {
      nodes, edges, source: "A", destination: "D", trace: true,
    }));
    if (!result) return;
    events = result.trace || [];
    state.educationalNodes = nodes;
    state.educationalEdges = edges;
  } else {
    result = await action(() => post("/algorithms/connectivity", { source, algorithm }));
    if (!result) return;
    events = result.visited.map((node) => ({ type: "node_visited", node }));
    state.educationalNodes = null;
    state.educationalEdges = null;
  }
  state.trace = { algorithm, events, index: -1, result };
  const stats = result.stats || {
    visited_nodes: result.visited?.length ?? events.filter((item) => item.type === "node_visited").length,
    iterations: result.iterations ?? result.visited?.length ?? events.length,
    edge_checks: result.edge_checks ?? 0,
    relaxations: result.relaxations ?? 0,
    execution_ms: result.execution_ms ?? 0,
    component_count: result.component_count,
  };
  $("#trace-stats").innerHTML = Object.entries(stats).filter(([key, value]) => !key.startsWith("_") && typeof value !== "object")
    .map(([key, value]) => `<div class="stats-row"><span>${escapeHtml(key.replaceAll("_", " "))}</span><b>${typeof value === "number" ? Number(value).toFixed(key.includes("ms") ? 3 : 0) : escapeHtml(value)}</b></div>`).join("");
  if (result.path?.length) $("#trace-stats").insertAdjacentHTML("beforeend", `<div class="stats-row"><span>final path</span><b>${escapeHtml(result.path.join(" → "))}</b></div>`);
  if (result.has_negative_cycle) $("#trace-stats").insertAdjacentHTML("beforeend", `<div class="stats-row"><span>negative cycle</span><b>${escapeHtml(result.negative_cycle.join(" → "))}</b></div>`);
  $("#trace-status").textContent = `${algorithm} · ${events.length} captured events · trace disabled during benchmarks`;
  renderTraceState();
});
$("#trace-next").addEventListener("click", () => {
  if (!state.trace || state.trace.index >= state.trace.events.length - 1) return;
  state.trace.index += 1;
  renderTraceState();
});
$("#trace-previous").addEventListener("click", () => {
  if (!state.trace || state.trace.index < 0) return;
  state.trace.index -= 1;
  renderTraceState();
});
$("#trace-play").addEventListener("click", () => {
  if (state.traceTimer) {
    stopTrace();
    renderTraceState();
    return;
  }
  if (!state.trace?.events.length) return;
  state.traceTimer = setInterval(() => {
    if (state.trace.index >= state.trace.events.length - 1) {
      stopTrace();
      renderTraceState();
      return;
    }
    state.trace.index += 1;
    renderTraceState();
  }, Number($("#trace-speed").value));
  renderTraceState();
});
$("#trace-reset").addEventListener("click", () => {
  stopTrace();
  if (state.trace) state.trace.index = -1;
  renderTraceState();
});
$("#trace-speed").addEventListener("change", () => {
  if (state.traceTimer) {
    stopTrace();
    $("#trace-play").click();
  }
});

$("#benchmark-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const body = Object.fromEntries(form.entries());
  ["size", "average_degree", "repetitions", "seed"].forEach((key) => { body[key] = Number(body[key]); });
  body.growth = form.has("growth");
  const result = await action(() => post("/algorithms/benchmark", body), "Benchmark completed using measured runtime.");
  if (result) drawBenchmarkChart(result);
});

$("#mst-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const weight = new FormData(event.currentTarget).get("weight");
  const result = await action(() => post("/algorithms/mst", { weight }));
  if (!result) return;
  cityMap.setFlow(result.edges.map((edge) => ({ source: edge.source, target: edge.target, flow: 200 })));
  $("#mst-result").innerHTML = `<div class="route-summary"><div class="metric-box"><strong>${result.total_weight.toFixed(2)}</strong><small>Total ${escapeHtml(weight)}</small></div>
    <div class="metric-box"><strong>${result.component_count}</strong><small>Forest components</small></div><div class="metric-box"><strong>${result.edges.length}</strong><small>Selected edges</small></div></div>
    <div class="body-copy">${result.components.map((component) => `Component (${component.length}): ${escapeHtml(component.join(", "))}`).join("<br>")}</div>
    <details class="body-copy"><summary>Show selected and excluded connections</summary><b>Selected:</b><br>${result.edges.map((edge) => `${escapeHtml(edge.source)} — ${escapeHtml(edge.target)} (${edge.weight.toFixed(2)})`).join("<br>")}
    <br><br><b>Excluded:</b><br>${result.excluded_edges.map((edge) => `${escapeHtml(edge.source)} — ${escapeHtml(edge.target)} (${edge.weight.toFixed(2)})`).join("<br>")}</details>`;
});

$("#connectivity-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const body = Object.fromEntries(new FormData(event.currentTarget).entries());
  const result = await action(() => post("/algorithms/connectivity", body));
  if (!result) return;
  cityMap.setTrace(result.visited, null);
  $("#connectivity-result").innerHTML = `<div class="route-summary"><div class="metric-box"><strong>${result.visited.length}</strong><small>Reachable from start</small></div><div class="metric-box"><strong>${result.component_count}</strong><small>Undirected components</small></div><div class="metric-box"><strong>${result.isolated_locations.length}</strong><small>Isolated locations</small></div></div>
    <div class="body-copy"><b>Traversal order (${escapeHtml(result.algorithm)}):</b><br>${escapeHtml(result.visited.join(" → "))}<br><br><b>Isolated:</b> ${escapeHtml(result.isolated_locations.join(", ") || "None")}</div>`;
});

$("#road-table").addEventListener("click", async (event) => {
  const button = event.target.closest("[data-action]");
  if (!button) return;
  const id = button.dataset.road;
  if (button.dataset.action === "close-road" || button.dataset.action === "open-road") {
    const actionName = button.dataset.action === "close-road" ? "close" : "open";
    const result = await action(() => post(`/network/roads/${id}/${actionName}`, {}), `Directed road #${id} ${actionName === "close" ? "blocked" : "reopened"}. Routes recalculate against current roads.`);
    if (result) { await loadNetwork(); await refreshOperationalData(); }
  } else if (button.dataset.action === "edit-road") {
    const values = {
      distance_km: Number(prompt("Road distance (km)", button.dataset.distance)),
      travel_minutes: Number(prompt("Travel time (minutes)", button.dataset.time)),
      evacuation_capacity: Number(prompt("Evacuation capacity per period", button.dataset.capacity)),
    };
    if (Object.values(values).some(Number.isNaN)) return notify("Road update cancelled or invalid.", true);
    const result = await action(() => put(`/network/roads/${id}`, values), `Road #${id} updated.`);
    if (result) { await loadNetwork(); await refreshOperationalData(); }
  }
});

$("#refresh-roads").addEventListener("click", () => action(async () => { await loadNetwork(); }, "Road data refreshed."));
$("#refresh-analytics").addEventListener("click", () => action(async () => {
  const summary = await api("/analytics/overview");
  state.analytics = summary;
  renderKpis(summary, "#analytics-kpis");
  renderStatusChart(summary.incidents_by_status);
  renderDispatchHistory(summary.dispatches);
}, "Analytics refreshed."));

function renderStatusChart(statuses) {
  const values = statuses || [];
  const max = Math.max(1, ...values.map((item) => item.count));
  $("#status-chart").innerHTML = values.length ? values.map((item) => `<div class="bar-row"><span>${escapeHtml(item.status)}</span><div class="bar-track"><div class="bar-fill" style="width:${item.count / max * 100}%"></div></div><b>${item.count}</b></div>`).join("")
    : '<div class="empty-state">No incident records.</div>';
}
function renderDispatchHistory(dispatches) {
  $("#dispatch-history").innerHTML = dispatches.length ? `<table class="table"><thead><tr><th>AMBULANCE</th><th>INCIDENT</th><th>ETA</th><th>CREATED</th></tr></thead><tbody>${dispatches.map((item) =>
    `<tr><td>${escapeHtml(item.ambulance_id)}</td><td>${escapeHtml(item.incident_type)}</td><td>${Number(item.eta_minutes).toFixed(2)} min</td><td>${escapeHtml(item.created_at)}</td></tr>`).join("")}</tbody></table>`
    : '<div class="empty-state">No dispatch has been recorded.</div>';
}

$("#reset-demo").addEventListener("click", async () => {
  if (!confirm("Reset all incidents, assignments, road changes, and simulation history to the deterministic Metroville demo?")) return;
  const result = await action(() => post("/demo/reset", {}), "Demo data reset to the deterministic initial scenario.");
  if (result) {
    cityMap.clearHighlights();
    await loadNetwork();
    await refreshOperationalData();
    $("#evacuation-results").textContent = "Configure one or more zones and shelters.";
    $("#route-result").textContent = "Set route endpoints to get started.";
    $("#mst-result").textContent = "Generate an infrastructure plan.";
  }
});

async function refreshAnalyticsInitial() {
  const result = await api("/analytics/overview");
  renderKpis(result, "#analytics-kpis");
  renderStatusChart(result.incidents_by_status);
  renderDispatchHistory(result.dispatches);
}

try {
  await initialize();
  await refreshAnalyticsInitial();
} catch (error) {
  notify(`Unable to initialize ResQNet: ${error.message}`, true);
  $("#kpi-grid").innerHTML = `<div class="loading-card">Application initialization failed: ${escapeHtml(error.message)}</div>`;
}
