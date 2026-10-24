// Reproduce the reference/component-types.json fixture from the saved public
// MIT GWT bundle. The outer file is a data-delivery call; its inner app code is
// captured as text, never executed. Only quoted string literals are decoded.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'reference', 'ode-cache.js'), 'utf8');
let decoded;
vm.runInNewContext(source, {ode: {onScriptDownloaded: parts => decoded = parts.join('')}}, {timeout: 5000});
const target = decoded.indexOf('"name":"SystemTime"');
if (target < 0) throw new Error('Clock metadata not found');
const start = decoded.lastIndexOf('\nfunction ', target) + 1;
const end = decoded.indexOf('\nfunction ', target);
const body = decoded.slice(start, end);
const strings = [...body.matchAll(/a\.a\+='(?:\\.|[^'\\])*'/g)]
  .map(match => vm.runInNewContext(match[0].slice(5), {}, {timeout: 1000}));
const data = JSON.parse(strings.join(''));
if (!Array.isArray(data) || !data.some(x => x.name === 'Canvas')) throw new Error('Invalid metadata');
fs.writeFileSync(path.join(root, 'reference', 'component-types.json'), JSON.stringify(data, null, 2));
console.log(`Extracted ${data.length} component definitions`);
