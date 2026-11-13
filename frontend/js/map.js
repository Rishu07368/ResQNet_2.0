const NS = "http://www.w3.org/2000/svg";
const COLORS = {
  hospital: "#6ac9c4", shelter: "#75bd89", ambulance_station: "#51aaf0",
  fire_station: "#ed805b", police_station: "#9383e4", residential: "#d8b15e",
  intersection: "#91a4b8",
};
const SYMBOLS = {
  hospital: "+", shelter: "S", ambulance_station: "A", fire_station: "F",
  police_station: "P", residential: "R", intersection: "",
};
const views = new WeakMap();
let network;
let currentRoute = [];
let currentVisited = [];
let activeNode = null;
let activeRoadPair = null;
let unreachableNodes = new Set();
let flowMap = new Map();
let selectionCallback = () => {};

function svgElement(name, attrs = {}) {
  const node = document.createElementNS(NS, name);
  Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, value));
  return node;
}

function positionLookup(locations) {
  const latitudes = locations.map((item) => item.latitude);
  const longitudes = locations.map((item) => item.longitude);
  const minLat = Math.min(...latitudes), maxLat = Math.max(...latitudes);
  const minLon = Math.min(...longitudes), maxLon = Math.max(...longitudes);
  const result = {};
  locations.forEach((location) => {
    const x = 70 + (location.longitude - minLon) / Math.max(maxLon - minLon, 0.001) * 760;
    const y = 55 + (maxLat - location.latitude) / Math.max(maxLat - minLat, 0.001) * 480;
    result[location.id] = { x, y };
  });
  return result;
}

function draw(svg) {
  if (!network) return;
  const view = views.get(svg) || { scale: 1 };
  views.set(svg, view);
  svg.replaceChildren();
  svg.setAttribute("viewBox", `${(900 - 900 / view.scale) / 2} ${(600 - 600 / view.scale) / 2} ${900 / view.scale} ${600 / view.scale}`);
  const points = positionLookup(network.locations);
  const roadLayer = svgElement("g", { class: "road-layer" });
  network.roads.forEach((road) => {
    const from = points[road.source_id], to = points[road.target_id];
    if (!from || !to) return;
    const key = `${road.source_id}>${road.target_id}`;
    const line = svgElement("line", {
      x1: from.x, y1: from.y, x2: to.x, y2: to.y,
      class: `road-edge${road.is_open ? "" : " closed"}${currentRoute.some((item, index) => index < currentRoute.length - 1 && item === road.source_id && currentRoute[index + 1] === road.target_id) ? " route-edge" : ""}${currentVisited.includes(road.source_id) && currentVisited.includes(road.target_id) ? " visited-edge" : ""}${activeRoadPair?.[0] === road.source_id && activeRoadPair?.[1] === road.target_id ? " active-edge" : ""}`,
      "marker-end": "url(#road-arrow)",
      "data-road": road.id,
      "stroke-width": flowMap.has(key) ? Math.min(7, 2 + flowMap.get(key) / 150) : undefined,
    });
    const title = svgElement("title");
    title.textContent = `${network.locations.find((item) => item.id === road.source_id)?.name} → ${network.locations.find((item) => item.id === road.target_id)?.name} · ${road.distance_km.toFixed(2)} km · ${road.travel_minutes.toFixed(1)} min · Capacity ${road.evacuation_capacity}/period${road.is_open ? "" : " · CLOSED"}`;
    line.append(title);
    if (flowMap.has(key)) line.classList.add("flow-edge");
    roadLayer.append(line);
  });
  svg.append(roadLayer);
  const defs = svgElement("defs");
  const marker = svgElement("marker", { id: "road-arrow", viewBox: "0 0 10 10", refX: "8", refY: "5", markerWidth: "4", markerHeight: "4", orient: "auto-start-reverse" });
  marker.append(svgElement("path", { d: "M 0 0 L 10 5 L 0 10 z", fill: "#8294a5" }));
  defs.append(marker);
  svg.prepend(defs);
  const nodes = svgElement("g", { class: "node-layer" });
  network.locations.forEach((location) => {
    const point = points[location.id];
    const group = svgElement("g", { class: `location-node${currentRoute.includes(location.id) ? " path-node" : ""}${currentVisited.includes(location.id) ? " visited" : ""}${unreachableNodes.has(location.id) ? " unreachable" : ""}${activeNode === location.id ? " active-node" : ""}${location.id === activeNode ? " selected" : ""}`, "data-location": location.id, tabindex: "0", role: "button", "aria-label": `${location.name}, ${location.kind.replaceAll("_", " ")}` });
    group.append(svgElement("circle", { class: "node-bg", cx: point.x, cy: point.y, r: location.kind === "intersection" ? 7 : 10, fill: COLORS[location.kind] || COLORS.intersection }));
    const glyph = SYMBOLS[location.kind];
    if (glyph) {
      const text = svgElement("text", { x: point.x, y: point.y, class: "node-glyph" });
      text.textContent = glyph;
      group.append(text);
    }
    if (location.kind !== "intersection") {
      const label = svgElement("text", { x: point.x, y: point.y + 21, class: "node-label" });
      label.textContent = location.id;
      group.append(label);
    }
    const title = svgElement("title");
    title.textContent = `${location.name} · ${location.kind.replaceAll("_", " ")}`;
    group.append(title);
    network.ambulances?.filter((ambulance) => ambulance.location_id === location.id).forEach((ambulance, index) => {
      const markerX = point.x + 10 + index * 9;
      const markerY = point.y - 17;
      group.append(svgElement("rect", {
        x: markerX - 5, y: markerY - 5, width: 11, height: 11, rx: 3,
        fill: ambulance.status === "available" ? "#47d39b" : "#e57c71",
        stroke: "#0c1520", "stroke-width": 1.5,
      }));
      const unit = svgElement("text", { x: markerX + .5, y: markerY + .5, class: "node-glyph", "font-size": "7" });
      unit.textContent = "A";
      group.append(unit);
      const unitTitle = svgElement("title");
      unitTitle.textContent = `${ambulance.id} · ${ambulance.status}`;
      group.append(unitTitle);
    });
    group.addEventListener("click", () => selectionCallback(location));
    group.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") selectionCallback(location);
    });
    nodes.append(group);
  });
  svg.append(nodes);
}

export function setNetwork(value) {
  network = value;
  document.querySelectorAll(".network-map").forEach(draw);
  renderLegend();
}

function renderLegend() {
  const entries = [
    ["residential", "Residential"], ["hospital", "Hospital"], ["shelter", "Shelter"],
    ["ambulance_station", "Ambulance station"], ["fire_station", "Fire station"],
    ["police_station", "Police station"],
  ];
  document.querySelectorAll("#map-legend, #main-map-legend").forEach((container) => {
    container.innerHTML = entries.map(([type, label]) => `<span class="legend-item"><i class="legend-dot" style="background:${COLORS[type]}"></i>${label}</span>`).join("")
      + '<span class="legend-item"><i class="legend-dot" style="background:#cf5962"></i>Blocked road</span>';
  });
}

export function setSelectionHandler(callback) {
  selectionCallback = callback;
}

export function setRoute(result) {
  currentRoute = result?.path || [];
  currentVisited = result?.visited || [];
  unreachableNodes = new Set(Object.entries(result?.distances || {}).filter(([, value]) => value === null).map(([id]) => id));
  activeRoadPair = null;
  flowMap = new Map();
  document.querySelectorAll(".network-map").forEach(draw);
}

export function setTrace(visited, current, activeEdge = null) {
  currentVisited = visited || [];
  activeNode = current || null;
  activeRoadPair = activeEdge;
  currentRoute = [];
  unreachableNodes = new Set();
  document.querySelectorAll(".network-map").forEach(draw);
}

export function setFlow(roads) {
  flowMap = new Map((roads || []).filter((item) => item.flow > 0).map((item) => [`${item.source}>${item.target}`, item.flow]));
  document.querySelectorAll(".network-map").forEach(draw);
}

export function clearHighlights() {
  currentRoute = [];
  currentVisited = [];
  activeNode = null;
  activeRoadPair = null;
  unreachableNodes = new Set();
  flowMap = new Map();
  document.querySelectorAll(".network-map").forEach(draw);
}

export function zoom(delta) {
  document.querySelectorAll(".network-map").forEach((svg) => {
    const view = views.get(svg) || { scale: 1 };
    view.scale = Math.min(2.2, Math.max(0.7, view.scale + delta));
    views.set(svg, view);
    draw(svg);
  });
}

export function locationById(id) {
  return network?.locations.find((item) => item.id === id);
}

export function getNetwork() {
  return network;
}
