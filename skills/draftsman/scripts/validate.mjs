// Parse-check Mermaid text without a browser: node validate.mjs < diagram.mmd
import { JSDOM } from 'jsdom';
import fs from 'node:fs';

const dom = new JSDOM('<!doctype html><html><body></body></html>');
globalThis.window = dom.window;
globalThis.document = dom.window.document;
const { default: mermaid } = await import('mermaid');

const file = process.argv[2];
const text = fs.readFileSync(file && file !== '-' ? file : 0, 'utf8');
try {
  await mermaid.parse(text);
  console.log('mermaid: OK');
} catch (e) {
  console.error('mermaid: ' + String(e.message || e));
  process.exitCode = 1;
}
