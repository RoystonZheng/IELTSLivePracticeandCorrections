const assert = require('node:assert/strict');
const {test} = require('node:test');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const {renderMarkedText, validRecords} = require('../app/annotations.js');

test('renders three highlight colors without changing passage text', () => {
  for (const color of ['yellow', 'green', 'pink']) {
    const html = renderMarkedText('one two', [{id:'a', type:'highlight', color, start:4, end:7}]);
    assert.match(html, new RegExp(`annot-${color}`));
    assert.match(html, />two<\/span>/);
    assert.match(html, /^one /);
  }
});

test('a note and highlight can share the same word safely', () => {
  const html = renderMarkedText('a <word>', [
    {id:'h', type:'highlight', color:'pink', start:3, end:7},
    {id:'n', type:'note', text:'Check <evidence>', start:3, end:7}
  ]);
  assert.match(html, /data-annot-highlight="h"/);
  assert.match(html, /data-annot-note="n"/);
  assert.match(html, /&lt;/);
  assert.match(html, />word<\/span>/);
  assert.match(html, /Check &lt;evidence&gt;/);
  assert.doesNotMatch(html, /<evidence>/);
});

test('discard stale or invalid offsets instead of breaking rendering', () => {
  const records = validRecords([
    {id:'bad', type:'highlight', color:'blue', start:0, end:2},
    {id:'stale', type:'note', start:2, end:20},
    {id:'good', type:'highlight', color:'green', start:0, end:2}
  ], 3);
  assert.equal(records.length, 1);
  assert.equal(renderMarkedText('abc', records).includes('annot-green'), true);
});

test('imported reading practice annotates reference, question, and options', () => {
  const paper = {
    id:'sample', title:'Sample', skill:'reading', pageCount:1,
    referenceText:'Coastal habitat\nBirds live here.',
    questions:[{number:1, page:1, prompt:'What lives here?', options:['A. Birds','B. Cars'], answer:'A'}],
    answers:{}, submittedAt:null
  };
  const handlers = {};
  const main = {innerHTML:'', addEventListener(name, handler) { handlers[name] = handler; }};
  const annotated = [];
  const window = {IELTS_ANNOTATIONS_INSTANCE:{
    textHtml(kind, key, value) { annotated.push([kind, key, value]); return `<i data-key="${key}">${value}</i>`; },
    notesHtml() { return '<aside>notes</aside>'; }
  }};
  const context = {window, document:{getElementById() { return main; }},
    localStorage:{getItem() { return JSON.stringify([paper]); }, setItem() {}}, setTimeout, clearTimeout};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../app/pdf-import.js'),'utf8'), context);
  handlers.click({target:{closest() { return {dataset:{pdfAction:'open', pdfId:'sample'}}; }}});
  assert.match(main.innerHTML, /data-key="ref:1"/);
  assert.match(main.innerHTML, /data-key="q:1"/);
  assert.match(main.innerHTML, /data-key="q:1:opt:A"/);
  assert.deepEqual(annotated.map(item => item[0]), ['pdf','pdf','pdf','pdf','pdf']);
});
