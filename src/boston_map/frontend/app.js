const statusMessage = document.querySelector('#map-status');
const retry = document.querySelector('#retry');
const reset = document.querySelector('#reset-view');
const selector = document.querySelector('#tract-select');
const details = document.querySelector('#tract-details');
const streets = document.querySelector('#streets');
const basemapStatus = document.querySelector('#basemap-status');
const opacitySlider = document.querySelector('#density-opacity');
const opacityValue = document.querySelector('#opacity-value');
const hiddenTracts = new Set(['25025990101']);
const colors = ['#edf8e9', '#c7e9c0', '#a1d99b', '#74c476', '#31a354', '#006d2c'];
const limits = [1000, 5000, 10000, 20000, 30000];
const noDataColor = '#b4b9bd';
const labels = ['0–<1,000', '1,000–<5,000', '5,000–<10,000', '10,000–<20,000', '20,000–<30,000', '30,000+', 'No data'];
const number = (value, digits = 0) => Number.isFinite(value) ? value.toLocaleString('en-US', {maximumFractionDigits: digits}) : 'Not available';
const countShare = (group) => `${number(group.estimate)}${Number.isFinite(group.percent) ? ` (${number(group.percent, 2)}%)` : ' (share unavailable)'}`;
let map;
let bounds;
let records = new Map();
let popup;
labels.forEach((label, i) => {
  const li = document.createElement('li');
  const swatch = document.createElement('span');
  swatch.className = 'swatch';
  swatch.style.background = colors[i] || noDataColor;
  li.append(swatch, document.createTextNode(label));
  document.querySelector('#legend').append(li);
});
function showDetails(id) {
  const feature = records.get(id);
  if (!feature) {
    if (map?.getLayer('selected')) map.setFilter('selected', ['==', ['get', 'geoid'], '']);
    details.textContent = 'Click a tract to explore its estimates.';
    return;
  }
  selector.value = id;
  const p = feature.properties;
  const split = p.white_alone_vs_everyone_else;
  const heading = document.createElement('h2');
  heading.textContent = `Tract ${p.tract}`;
  const identifier = document.createElement('p');
  identifier.className = 'muted';
  identifier.textContent = `GEOID ${p.geoid} · ACS ${p.period}`;
  const list = document.createElement('dl');
  const values = [
    ['Population', number(p.population_estimate)], ['Population MOE', Number.isFinite(p.population_moe) ? `±${number(p.population_moe)}` : 'Not available'],
    ['Land area', `${number(p.land_area_km2, 4)} km²`],
    ['Density', p.density_status === 'available' ? `${number(p.population_density_km2)} / km²` : 'No land area / no data'],
    ['White alone', countShare(split.white_alone)],
    ['White alone MOE', Number.isFinite(split.white_alone.moe) ? `±${number(split.white_alone.moe)}` : 'Not available'],
    ['Everyone else', countShare(split.everyone_else)],
  ];
  for (const [label, value] of values) {
    const term = document.createElement('dt'); term.textContent = label;
    const entry = document.createElement('dd'); entry.textContent = value;
    list.append(term, entry);
  }
  details.replaceChildren(heading, identifier, list);
  map.setFilter('selected', ['==', ['get', 'geoid'], id]);
}
function toggleStreets() {
  if (!map?.getLayer('streets')) return;
  basemapStatus.textContent = '';
  map.setLayoutProperty('streets', 'visibility', streets.checked ? 'visible' : 'none');
}
async function loadMap() {
  retry.disabled = true; reset.disabled = true; selector.disabled = true;
  statusMessage.dataset.state = 'loading'; statusMessage.textContent = 'Loading tract data…';
  selector.replaceChildren(new Option('Choose a tract or click the map', ''));
  details.textContent = 'Click a tract to explore its estimates.';
  records = new Map();
  basemapStatus.textContent = '';
  if (map) { map.remove(); map = null; }
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch('/api/tracts', {signal: controller.signal});
    if (!response.ok) throw new Error('Data unavailable');
    const data = await response.json();
    if (data.type !== 'FeatureCollection' || !data.features?.length) throw new Error('Invalid GeoJSON');
    // Display-only exclusion: preserve the full county snapshot in the API/download.
    data.features = data.features.filter(feature => !hiddenTracts.has(feature.properties.geoid));
    if (!data.features.length) throw new Error('No visible tracts');
    bounds = new maplibregl.LngLatBounds();
    function extend(coordinates) {
      if (typeof coordinates[0] === 'number') bounds.extend(coordinates);
      else coordinates.forEach(extend);
    }
    for (const feature of data.features) {
      records.set(feature.properties.geoid, feature);
      extend(feature.geometry.coordinates);
      selector.add(new Option(`Tract ${feature.properties.tract} · ${feature.properties.geoid}`, feature.properties.geoid));
    }
    map = new maplibregl.Map({container: 'map', style: {version: 8, sources: {}, layers: [{id: 'background', type: 'background', paint: {'background-color': '#e8eeed'}}]}, center: [-71.04, 42.34], zoom: 10, attributionControl: true});
    map.addControl(new maplibregl.NavigationControl({showCompass: false}));
    map.on('error', event => {
      if (event.sourceId === 'streets') basemapStatus.textContent = 'Street basemap unavailable. Census polygons remain available.';
    });
    await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error('Map initialization timed out')), 15000);
      map.once('load', () => {clearTimeout(timeout); resolve();});
    });
    map.fitBounds(bounds, {padding: 25, duration: 0});
    map.addSource('streets', {type: 'raster', tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'], tileSize: 256, maxzoom: 19, attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'});
    map.addLayer({id: 'streets', type: 'raster', source: 'streets', layout: {visibility: streets.checked ? 'visible' : 'none'}});
    map.addSource('tracts', {type: 'geojson', data, attribution: 'U.S. Census Bureau · ACS 2020–2024 / TIGER 2024'});
    const step = ['step', ['get', 'population_density_km2'], colors[0]];
    limits.forEach((limit, i) => step.push(limit, colors[i + 1]));
    map.addLayer({id: 'density', type: 'fill', source: 'tracts', paint: {'fill-color': ['case', ['==', ['get', 'population_density_km2'], null], noDataColor, step], 'fill-opacity': Number(opacitySlider.value) / 100}});
    map.addLayer({id: 'outlines', type: 'line', source: 'tracts', paint: {'line-color': '#405e50', 'line-width': 0.6}});
    map.addLayer({id: 'selected', type: 'line', source: 'tracts', filter: ['==', ['get', 'geoid'], ''], paint: {'line-color': '#d17217', 'line-width': 3}});
    popup = new maplibregl.Popup({closeButton: false, closeOnClick: false});
    map.on('mousemove', 'density', event => {
      map.getCanvas().style.cursor = 'pointer';
      const p = records.get(event.features[0].properties.geoid).properties;
      const content = document.createElement('div');
      content.textContent = `Tract ${p.tract}: ${Number.isFinite(p.population_density_km2) ? number(p.population_density_km2) + ' people/km²' : 'No density data'}. Click for details.`;
      popup.setLngLat(event.lngLat).setDOMContent(content).addTo(map);
    });
    map.on('mouseleave', 'density', () => {map.getCanvas().style.cursor = ''; popup.remove();});
    map.on('click', 'density', event => showDetails(event.features[0].properties.geoid));
    statusMessage.textContent = `${data.features.length} displayed tracts · ACS 2020–2024 · Click a tract to explore`;
    statusMessage.dataset.state = 'success';
    reset.disabled = false; selector.disabled = false;
  } catch {
    statusMessage.dataset.state = 'error';
    statusMessage.textContent = 'Could not load the map. Check the server and WebGL support, then retry. The GeoJSON download is also available below.';
  } finally {clearTimeout(timer); retry.disabled = false;}
}
selector.addEventListener('change', () => showDetails(selector.value));
retry.addEventListener('click', loadMap);
reset.addEventListener('click', () => map.fitBounds(bounds, {padding: 25}));
streets.addEventListener('change', toggleStreets);
opacitySlider.addEventListener('input', () => {
  opacityValue.textContent = `${opacitySlider.value}%`;
  if (map?.getLayer('density')) map.setPaintProperty('density', 'fill-opacity', Number(opacitySlider.value) / 100);
});
loadMap();
