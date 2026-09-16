// Verify every label belongs to the country it names, using the renderer's geometry.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.join(__dirname, '..', 'static');
const d3 = require(path.join(root, 'vendor/d3.min.js'));
const metadata = JSON.parse(fs.readFileSync(path.join(root, 'atlas-countries.json')));
const features = JSON.parse(fs.readFileSync(path.join(root, 'globe-countries.json'))).features;
assert.equal(new Set(features.map(f => f.properties.code)).size, features.length);
assert.deepEqual(features.map(f => f.properties.code).sort(), Object.keys(metadata).sort());
for (const feature of features) {
  const code = feature.properties.code;
  const [x, y] = metadata[code].label;
  const anchor = [x / 2.5 - 180, 90 - y / 2.5];
  assert.ok(d3.geoContains(feature, anchor), `${code}: label is outside its country`);
  assert.ok(d3.geoArea(feature) < 2 * Math.PI, `${code}: inverted country polygon`);
}
console.log(`Verified ${features.length} country label anchors and polygon orientations.`);
