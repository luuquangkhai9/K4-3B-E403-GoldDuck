// HTTP contract and asynchronous UI regression tests; no browser dependencies.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'app/viewer/static/app.js'), 'utf8');
const html = fs.readFileSync(path.join(root, 'app/viewer/static/index.html'), 'utf8');
const tick = () => new Promise(resolve => setImmediate(resolve));

class Element {
  constructor() {
    this.children = []; this.dataset = {}; this.value = ''; this.textContent = '';
    this.hidden = false; this.disabled = false; this.listeners = {};
    this.style = {setProperty() {}};
    this.classList = {toggle() {}, add() {}, remove() {}};
  }
  append(...nodes) { this.children.push(...nodes); }
  remove() { this.removed = true; }
  focus() {}
  addEventListener(name, callback) { this.listeners[name] = callback; }
  setAttribute() {}
  querySelectorAll(selector) {
    const all = this.children.flatMap(child => child instanceof Element ? [child, ...child.querySelectorAll('*')] : []);
    if (selector === '*') return all;
    if (selector === '.scope-item[data-day]') return all.filter(child => child.dataset.day);
    if (selector === '.mindmap-node.active') return [];
    return [];
  }
  set innerHTML(text) { this.html = text; this.children = []; }
  get innerHTML() { return this.html || this.textContent; }
}

async function setup(handler) {
  const elements = new Map([...html.matchAll(/\bid="([^"]+)"/g)].map(match => [match[1], new Element()]));
  const extra = [];
  const calls = [];
  const document = {
    getElementById(id) { return elements.get(id) || extra.find(element => element.id === id && !element.removed) || null; },
    querySelector(selector) { return selector === '.ai-layout' ? new Element() : null; },
    querySelectorAll() { return []; },
    createElement() { const element = new Element(); extra.push(element); return element; },
    createElementNS() { return new Element(); },
    createTextNode(text) { return text; },
  };
  const context = vm.createContext({
    document, URL, URLSearchParams, AbortController, performance, setTimeout, clearTimeout,
    requestAnimationFrame() {}, console,
    fetch: async (url, options = {}) => {
      calls.push({url, options, body: options.body ? JSON.parse(options.body) : null});
      if (url === '/api/days') return {ok: true, json: async () => ({days: [
        {day_id: 'Day01', document_count: 2}, {day_id: 'Day07', document_count: 3},
      ], unassigned_document_count: 1})};
      const result = await handler(url, options);
      const data = url === '/api/chat' ? {
        answer: 'Đã trả lời', citations: [], status: 'completed', output_format: 'text', ...result.data,
      } : result.data || {};
      return {ok: !result.status || result.status < 400, json: async () => data, blob: async () => new Blob()};
    },
  });
  vm.runInContext(source, context, {filename: 'app.js'});
  await tick();
  return {context, elements, calls, run: code => vm.runInContext(code, context)};
}

async function main() {
  let checks = 0;
  const ui = await setup(async url => {
    if (url === '/api/mindmap/intent') return {data: {day: 'Day07', topic: 'Transformer'}};
    return {data: {title: 'Transformer', branches: []}};
  });
  assert.deepEqual(Array.from(ui.run('availableDays')), ['Day01', 'Day07']);
  assert.equal(ui.elements.get('scope-list').children[1].dataset.day, 'Day07');
  assert.match(ui.elements.get('scope-list').children[1].children[0].textContent, /3 tài liệu/);
  assert.match(ui.elements.get('day-status').textContent, /1 tài liệu/); checks++;

  ui.run("selectedScope = ['Day01', 'Day07']; input.value = 'Tạo mindmap Transformer buổi học số 7';");
  await ui.run('send()');
  const generated = ui.calls.find(call => call.url === '/api/chat');
  assert.deepEqual(generated.body, {question: 'Tạo mindmap Transformer buổi học số 7', scope: ['Day01', 'Day07'], context: null});
  assert.equal(ui.calls.filter(call => call.url.startsWith('/api/mindmap?')).length, 0);
  assert.equal(ui.calls.filter(call => call.url === '/api/mindmap/intent').length, 0);
  assert.equal(ui.elements.get('send').disabled, false); checks++;

  const unknown = await setup(async url => url === '/api/mindmap/intent'
    ? {data: {day: null, topic: 'RAG'}} : {status: 404, data: {detail: 'Không tìm thấy ngày học'}});
  unknown.run("input.value = 'Tạo mindmap RAG buổi 99';");
  await unknown.run('send()');
  assert.equal(unknown.calls.find(call => call.url === '/api/chat').body.question, 'Tạo mindmap RAG buổi 99');
  assert.match(unknown.elements.get('status').textContent, /Không tìm thấy ngày/); checks++;

  const overview = await setup(async url => url === '/api/mindmap/intent'
    ? {data: {day: 'Day07', topic: null}} : {data: {day: 'Day07', branches: []}});
  overview.run("input.value = 'Tạo mindmap buổi 7';");
  await overview.run('send()');
  assert.equal(overview.calls.filter(call => call.url === '/api/chat').length, 1);
  assert.equal(overview.calls.filter(call => call.url === '/api/mindmap/generate').length, 0); checks++;

  let complete;
  const pending = await setup(async () => new Promise(resolve => { complete = resolve; }));
  pending.run("selectedScope = ['Day07']; input.value = 'Transformer là gì?';");
  const first = pending.run('send()');
  pending.run("selectedScope = ['Day01']; input.value = 'Gửi lặp';");
  await pending.run('send()');
  assert.equal(pending.calls.filter(call => call.url === '/api/chat').length, 1);
  assert.deepEqual(pending.calls.find(call => call.url === '/api/chat').body.scope, ['Day07']);
  complete({data: {answer: 'Đã trả lời', citations: []}});
  await first;
  assert.equal(pending.run('busy'), false);
  assert.equal(pending.elements.get('input').disabled, false); checks++;

  const aborted = await setup(async () => { const error = new Error(); error.name = 'AbortError'; throw error; });
  aborted.run("input.value = 'Câu hỏi';");
  await aborted.run('send()');
  assert.match(aborted.elements.get('status').textContent, /Quá thời gian/);
  assert.equal(aborted.run('busy'), false);
  assert.equal(aborted.elements.get('send').disabled, false); checks++;

  const stalled = await setup((url, options) => new Promise((resolve, reject) => {
    options.signal.addEventListener('abort', () => { const error = new Error(); error.name = 'AbortError'; reject(error); });
  }));
  await assert.rejects(stalled.run("fetchWithTimeout('/stall', {}, 20)"), {name: 'AbortError'}); checks++;

  const fallback = await setup(async () => { throw new Error('offline'); });
  const intent = await fallback.run("resolveMindmapIntent('Tạo mindmap về RAG buổi học số 7')");
  assert.equal(intent.day, 'Day07');
  assert.equal(intent.topic, 'RAG'); checks++;

  const range = await setup(async () => ({data: {output_format: 'mindmap', title: 'Day 01 · Day 02 · Day 03', branches: [
      {label: 'Day 01', nodes: []}, {label: 'Day 02', nodes: []}, {label: 'Day 03', nodes: []},
    ]}}));
  range.run("input.value = 'tao mindmap từ day 1 đến day 3';");
  await range.run('send()');
  assert.deepEqual(range.calls.find(call => call.url === '/api/chat').body,
    {question: 'tao mindmap từ day 1 đến day 3', scope: null, context: null});
  assert.equal(range.calls.filter(call => call.url === '/api/mindmap/intent' || call.url === '/api/mindmap/generate').length, 0);
  assert.equal(range.elements.get('status').textContent, ''); checks++;

  const rangeTopic = await setup(async () => ({data: {branches: []}}));
  rangeTopic.run("input.value = 'tạo mindmap về Transformer từ day 1 đến day 3';");
  await rangeTopic.run('send()');
  assert.deepEqual(rangeTopic.calls.find(call => call.url === '/api/chat').body,
    {question: 'tạo mindmap về Transformer từ day 1 đến day 3', scope: null, context: null}); checks++;

  for (const question of ['tạo mindmap day 1 và day 3', 'tạo mindmap day 1, 3']) {
    const parsed = range.run(`parseMindmapIntent(${JSON.stringify(question)})`);
    assert.deepEqual(Array.from(parsed.scope), ['Day01', 'Day03']);
    assert.equal(parsed.topic, '');
  } checks++;

  const invalid = await setup(async () => ({status: 422, data: {detail: 'Phạm vi ngày không hợp lệ'}}));
  invalid.run("input.value = 'mindmap day 3 đến day 1';");
  await invalid.run('send()');
  assert.equal(invalid.calls.filter(call => call.url === '/api/chat').length, 1);
  assert.match(invalid.elements.get('status').textContent, /Phạm vi ngày không hợp lệ/);
  assert.equal(invalid.run('busy'), false); checks++;

  const composite = 'tạo mindmap các file tài liệu tôi cần học tên gì nằm ở day nào để tôi hiểu về tranformers';
  const context = {task: 'study_materials', topic: 'transformers', document_ids: ['doc1']};
  const conversation = await setup(async () => ({data: {context}}));
  conversation.run(`input.value = ${JSON.stringify(composite)};`);
  await conversation.run('send()');
  conversation.run("input.value = 'tạo mindmap các tài liệu đó';");
  await conversation.run('send()');
  const chatCalls = conversation.calls.filter(call => call.url === '/api/chat');
  assert.equal(chatCalls[0].body.question, composite);
  assert.deepEqual(chatCalls[1].body.context, context); checks++;

  const tree = ui.run(`buildMindmapTree('Tài liệu học', [{label: 'Day 01', nodes: [{
    label: 'Day01/tên tài liệu dài & đầy đủ.pdf', filename: 'Day01/tên tài liệu dài & đầy đủ.pdf',
    page_number: 3, day_label: 'Day 01', reason: '<script>unsafe</script>', role: 'core', pages: [3, 4],
    sources: [{evidence_id: 'E2', filename: 'Day01/tên tài liệu dài & đầy đủ.pdf', page_number: 3},
              {evidence_id: 'E5', filename: 'Day01/tên tài liệu dài & đầy đủ.pdf', page_number: 4}]
  }]}])`);
  const descendants = tree.querySelectorAll('*');
  assert.equal(descendants.find(element => element.className === 'mindmap-node').textContent,
    'Day01/tên tài liệu dài & đầy đủ.pdf');
  const reason = descendants.find(element => element.className === 'mindmap-document-reason');
  assert.equal(reason.textContent, '<script>unsafe</script>');
  assert.equal(reason.html, undefined);
  assert.equal(descendants.filter(element => element.className === 'citation-chip').length, 2);
  assert.match(descendants.find(element => element.className === 'mindmap-document-location').textContent, /Slide 3, 4/); checks++;

  const failed = await setup(async () => ({data: {status: 'retrieval_timeout', output_format: 'mindmap', branches: [],
    answer: 'Tìm tài liệu quá thời gian; chưa thể kết luận kho thiếu nội dung.'}}));
  failed.run("input.value = 'mindmap tài liệu về A';");
  await failed.run('send()');
  assert.equal(failed.elements.get('messages').querySelectorAll('*').some(element => element.className === 'mindmap-tree'), false);
  assert.equal(failed.run('busy'), false); checks++;

  console.log(`UI regression checks passed: ${checks}`);
}

main().catch(error => { console.error(error); process.exitCode = 1; });
