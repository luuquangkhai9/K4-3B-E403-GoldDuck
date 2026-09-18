const input = document.getElementById('input');
const sendButton = document.getElementById('send');
const status = document.getElementById('status');
const messages = document.getElementById('messages');
const onlineStatus = document.getElementById('online-status');

// ---- Collapsible scope sidebar (more room for chat + slide) -------------
const aiLayout = document.querySelector('.ai-layout');
const scopeToggle = document.getElementById('scope-toggle');
scopeToggle.addEventListener('click', () => aiLayout.classList.toggle('scope-collapsed'));

// ---- Review scope (which days to ground answers in) ---------------------
const scopeList = document.getElementById('scope-list');
const scopeAllItem = document.getElementById('scope-all');
let selectedScope = []; // empty = whole course

function dayLabel(id) {
  const match = /^Day0*(\d+)$/i.exec(id);
  return match ? `Buổi ${match[1]}: ${id.toUpperCase()}` : id;
}

function updateScopeUI() {
  scopeAllItem.classList.toggle('active', selectedScope.length === 0);
  scopeList.querySelectorAll('.scope-item[data-day]').forEach(item => {
    item.classList.toggle('active', selectedScope.includes(item.dataset.day));
  });
}

scopeAllItem.addEventListener('click', () => { selectedScope = []; updateScopeUI(); });

let availableDays = [];

async function loadDays() {
  try {
    const response = await fetch('/api/days');
    if (!response.ok) return;
    const data = await response.json();
    availableDays = data.days || [];
    for (const day of availableDays) {
      const item = document.createElement('div');
      item.className = 'scope-item';
      item.dataset.day = day;

      const label = document.createElement('span');
      label.className = 'scope-item-label';
      label.textContent = `📖 ${dayLabel(day)}`;
      label.addEventListener('click', () => {
        selectedScope = selectedScope.includes(day)
          ? selectedScope.filter(item => item !== day)
          : [...selectedScope, day];
        updateScopeUI();
      });

      const mapButton = document.createElement('button');
      mapButton.type = 'button';
      mapButton.className = 'mindmap-trigger';
      mapButton.title = `Xem sơ đồ tư duy — ${dayLabel(day)}`;
      mapButton.setAttribute('aria-label', mapButton.title);
      mapButton.textContent = '🧠';
      mapButton.addEventListener('click', event => {
        event.stopPropagation();
        openMindmap(day);
      });

      item.append(label, mapButton);
      scopeList.append(item);
    }
  } catch { /* day picker is a convenience; question answering still works without it */ }
}
loadDays();

// ---- Mindmap (rule-based topic outline per day) --------------------------
const MINDMAP_COLORS = ['#15518e', '#e1252f', '#2a9d62', '#d09a22', '#7d5ba6', '#0f9b8e', '#c2185b', '#546e7a'];
const mindmapOverlay = document.getElementById('mindmap-overlay');
const mindmapTitle = document.getElementById('mindmap-title');
const mindmapBody = document.getElementById('mindmap-body');
const mindmapFeedback = document.getElementById('mindmap-feedback');
document.getElementById('mindmap-close').addEventListener('click', () => { mindmapOverlay.hidden = true; });
mindmapOverlay.addEventListener('click', event => { if (event.target === mindmapOverlay) mindmapOverlay.hidden = true; });

const SVG_NS = 'http://www.w3.org/2000/svg';

function drawMindmapLines(tree, svg, rootEl, branchEls) {
  const box = tree.getBoundingClientRect();
  if (!box.width || !box.height) return; // not laid out yet (e.g. still hidden)
  const point = el => {
    const r = el.getBoundingClientRect();
    return { left: r.left - box.left, right: r.right - box.left, midY: r.top - box.top + r.height / 2 };
  };
  svg.setAttribute('width', box.width);
  svg.setAttribute('height', box.height);
  svg.innerHTML = '';
  const rootP = point(rootEl);
  const curve = (x1, y1, x2, y2, color) => {
    const path = document.createElementNS(SVG_NS, 'path');
    const midX = (x1 + x2) / 2;
    path.setAttribute('d', `M ${x1} ${y1} C ${midX} ${y1}, ${midX} ${y2}, ${x2} ${y2}`);
    path.setAttribute('stroke', color);
    path.setAttribute('stroke-width', '2');
    path.setAttribute('fill', 'none');
    svg.append(path);
  };
  for (const { label, color, leafEls } of branchEls) {
    const branchP = point(label);
    curve(rootP.right, rootP.midY, branchP.left, branchP.midY, color);
    for (const leafEl of leafEls) {
      const leafP = point(leafEl);
      curve(branchP.right, branchP.midY, leafP.left, leafP.midY, color);
    }
  }
}

function buildMindmapTree(title, branches) {
  const tree = document.createElement('div');
  tree.className = 'mindmap-tree';

  const svg = document.createElementNS(SVG_NS, 'svg');
  svg.setAttribute('class', 'mindmap-lines');
  tree.append(svg);

  const root = document.createElement('div');
  root.className = 'mindmap-root';
  root.textContent = title;
  tree.append(root);

  if (!branches.length) {
    const empty = document.createElement('div');
    empty.className = 'mindmap-status';
    empty.textContent = 'Chưa có đủ nội dung để tạo sơ đồ.';
    tree.append(empty);
    return tree;
  }

  const branchesCol = document.createElement('div');
  branchesCol.className = 'mindmap-branches';
  const branchEls = [];
  branches.forEach((branch, index) => {
    const color = MINDMAP_COLORS[index % MINDMAP_COLORS.length];
    const row = document.createElement('div');
    row.className = 'mindmap-branch-row';

    const label = document.createElement('div');
    label.className = 'mindmap-branch';
    label.style.setProperty('--branch-color', color);
    label.textContent = branch.label;
    row.append(label);

    const leaves = document.createElement('div');
    leaves.className = 'mindmap-leaves';
    const leafEls = [];
    for (const node of branch.nodes || []) {
      const leaf = document.createElement('button');
      leaf.type = 'button';
      leaf.className = 'mindmap-node';
      leaf.style.setProperty('--branch-color', color);
      leaf.textContent = node.label;
      leaf.title = `${node.filename} — Slide ${node.page_number}`;
      leaf.addEventListener('click', () => {
        tree.querySelectorAll('.mindmap-node.active').forEach(el => el.classList.remove('active'));
        leaf.classList.add('active');
        if (mindmapFeedback) {
          mindmapFeedback.hidden = false;
          mindmapFeedback.textContent = `✓ Đã mở "${node.label}" (Slide ${node.page_number}) ở panel bên phải — đóng sơ đồ để xem.`;
        }
        openCitation({
          filename: node.filename,
          page_number: node.page_number,
          evidence_id: null,
          bbox: node.bbox || null,
        });
      });
      leaves.append(leaf);
      leafEls.push(leaf);
    }
    row.append(leaves);
    branchesCol.append(row);
    branchEls.push({ label, color, leafEls });
  });
  tree.append(branchesCol);

  requestAnimationFrame(() => drawMindmapLines(tree, svg, root, branchEls));
  return tree;
}

async function openMindmap(day) {
  const label = dayLabel(day);
  mindmapTitle.textContent = `Sơ đồ tư duy — ${label}`;
  mindmapFeedback.hidden = true;
  mindmapBody.innerHTML = '<div class="mindmap-status">Đang tạo sơ đồ…</div>';
  mindmapOverlay.hidden = false;
  try {
    const response = await fetch('/api/mindmap?' + new URLSearchParams({ day }));
    if (!response.ok) throw new Error('Không tạo được sơ đồ tư duy cho buổi học này.');
    const data = await response.json();
    mindmapBody.innerHTML = '';
    mindmapBody.append(buildMindmapTree(label, data.branches || []));
  } catch (error) {
    mindmapBody.innerHTML = `<div class="mindmap-status">${escapeHtml(error.message)}</div>`;
  }
}

// ---- Chat-triggered mindmap ("tạo mindmap day 2", "vẽ sơ đồ tư duy về RAG") ----
const MINDMAP_TRIGGER = /(mindmap|sơ đồ tư duy)/i;
const DAY_REFERENCE = /\b(?:day|buổi|ngày)\s*0*([0-9]{1,2})\b/i;
// Includes Vietnamese sentence-final particles ("làm đi", "vẽ giúp mình cái
// mindmap đi nhé") that carry no topic meaning — left in, they get sent as
// the "topic" and retrieval matches their unrelated literal sense instead
// (e.g. "đi" as in "nước đi" / a chess move) producing a nonsense mindmap.
// "nào" is deliberately NOT in this list: it's a filler only in bare
// exclamations ("làm đi nào"), but it's also the real question word in
// "ngày nào" / "cái nào" — stripping it blindly mangled genuine questions
// like "tài liệu nằm ở ngày nào?" into "nằm ở ngày ?".
//
// Uses (?:^|\s)...(?=\s|$) instead of \b: JS's \b is defined in terms of
// \w, which only covers ASCII letters, so it does not see a boundary
// between a Vietnamese diacritic vowel and whitespace (e.g. "về ", "vẽ ",
// "nhé ") — \b(về)\b silently fails to match "về" at all, leaving these
// words stuck in the extracted topic.
const MINDMAP_FILLER_WORDS = /(?:^|\s)(?:làm ơn|tạo|vẽ|làm|xem|hãy|giúp(?: tôi| mình)?|cho tôi|cho mình|dùm|giùm|về|của|kiến thức|nội dung|đi|nhé|nha|ạ|thử|coi|xíu|chút|nhỉ|luôn|với|cái)(?=\s|$)/gi;
// Defense in depth: catches a leftover filler word the regex above missed,
// so an empty/near-empty topic never silently reaches retrieval.
const MINDMAP_TRIVIAL_TOPICS = new Set(['', 'đi', 'nhé', 'nha', 'ạ', 'ừ', 'ờ', 'thế', 'vậy', 'này', 'đó', 'ấy', 'nhỉ', 'luôn', 'coi', 'thử']);

function parseMindmapIntent(text) {
  if (!MINDMAP_TRIGGER.test(text)) return null;
  const dayMatch = DAY_REFERENCE.exec(text);
  const day = dayMatch ? `Day${dayMatch[1].padStart(2, '0')}` : null;
  let topic = text
    .replace(MINDMAP_TRIGGER, ' ')
    .replace(DAY_REFERENCE, ' ')
    .replace(MINDMAP_FILLER_WORDS, ' ')
    // Orphaned punctuation left where the trigger phrase used to be, e.g.
    // "Vẽ sơ đồ tư duy: X" → "Vẽ : X" once "sơ đồ tư duy" is removed.
    .replace(/[,:;]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
  if (MINDMAP_TRIVIAL_TOPICS.has(topic.toLowerCase())) topic = '';
  return { day, topic };
}

function addMindmapMessage(title, branches) {
  const msg = document.createElement('div');
  msg.className = 'msg ai mindmap-msg';
  const mini = document.createElement('div');
  mini.className = 'mini-ai';
  mini.textContent = '🤖';
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  const intro = document.createElement('div');
  intro.textContent = branches.length
    ? `🧠 Sơ đồ tư duy: ${title}`
    : `Chưa đủ nội dung trong bài giảng để tạo sơ đồ tư duy cho "${title}".`;
  bubble.append(intro);
  if (branches.length) {
    const wrap = document.createElement('div');
    wrap.className = 'mindmap-inline';
    wrap.append(buildMindmapTree(title, branches));
    bubble.append(wrap);
  }
  msg.append(mini, bubble);
  messages.append(msg);
  scrollToBottom();
}

async function resolveMindmapIntent(question) {
  // Regex-based extraction breaks on any phrasing it wasn't written for
  // ("buổi học số 7", a whole rambling question instead of a short topic).
  // Ask the LLM to read the message like a person would; fall back to the
  // regex parse only when the model is unavailable or gives nothing usable.
  try {
    const response = await fetch('/api/mindmap/intent', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: question }),
    });
    if (response.ok) {
      const data = await response.json();
      if (data && (data.day || data.topic)) return { day: data.day || null, topic: data.topic || '' };
    }
  } catch { /* fall through to the regex parser below */ }
  return parseMindmapIntent(question) || { day: null, topic: '' };
}

async function handleMindmapChat(question) {
  const intent = await resolveMindmapIntent(question);
  if (!intent.day && !intent.topic) {
    status.textContent = 'Bạn muốn xem sơ đồ tư duy về chủ đề gì hoặc buổi học nào? Ví dụ: "tạo mindmap về RAG" hoặc "tạo mindmap buổi 3".';
    return;
  }
  onlineStatus.textContent = 'Đang tạo sơ đồ tư duy…';
  addTypingIndicator();
  try {
    let title, branches;
    if (intent.day && availableDays.includes(intent.day)) {
      title = dayLabel(intent.day);
      const response = await fetch('/api/mindmap?' + new URLSearchParams({ day: intent.day }));
      const data = await response.json();
      if (!response.ok) throw new Error('Không tạo được sơ đồ tư duy cho buổi học này.');
      branches = data.branches || [];
    } else {
      title = intent.topic || 'Chủ đề';
      const scope = selectedScope.length ? selectedScope : null;
      const response = await fetch('/api/mindmap/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic: title, scope }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Không tạo được sơ đồ tư duy.');
      branches = data.branches || [];
    }
    removeTypingIndicator();
    addMindmapMessage(title, branches);
  } catch (error) {
    removeTypingIndicator();
    status.textContent = error.message || 'Không tạo được sơ đồ tư duy.';
  } finally {
    onlineStatus.textContent = 'Đang sẵn sàng hỗ trợ bạn học';
  }
}

// ---- Slide panel (right side) ------------------------------------------
const slideTitle = document.getElementById('slide-title');
const slideSub = document.getElementById('slide-sub');
const slideControls = document.getElementById('slide-controls');
const slideEmpty = document.getElementById('slide-empty');
const slideStatus = document.getElementById('slide-status');
const pageWrap = document.getElementById('page-wrap');
const image = document.getElementById('slide-image');
const highlight = document.getElementById('highlight');
const pageLabel = document.getElementById('page-label');
const prevButton = document.getElementById('prev');
const nextButton = document.getElementById('next');
const originalLink = document.getElementById('original-link');

let current = null; // {file, page, evidencePage, bbox, evidenceId}
let objectURL;
let requestNumber = 0;

async function renderSlide() {
  if (!current) return;
  const requestId = ++requestNumber;
  const { file, page } = current;
  slideEmpty.hidden = true;
  slideControls.hidden = false;
  pageLabel.textContent = `Slide ${page}`;
  prevButton.disabled = page <= 1;
  originalLink.href = '/pdf/' + file.split('/').map(encodeURIComponent).join('/') + '#page=' + page;
  pageWrap.hidden = true;
  highlight.hidden = true;
  slideStatus.textContent = 'Đang tải trang…';
  try {
    const response = await fetch('/api/page?' + new URLSearchParams({ file, page }));
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.detail || 'Không tải được trang. Hãy mở PDF gốc.');
    }
    const blob = await response.blob();
    if (requestId !== requestNumber) return;
    if (objectURL) URL.revokeObjectURL(objectURL);
    objectURL = URL.createObjectURL(blob);
    image.onload = () => {
      if (requestId !== requestNumber) return;
      pageWrap.hidden = false;
      const onEvidencePage = page === current.evidencePage && current.bbox;
      if (onEvidencePage) {
        const [x0, y0, x1, y1] = current.bbox;
        Object.assign(highlight.style, {
          left: `${x0 * 100}%`, top: `${y0 * 100}%`,
          width: `${(x1 - x0) * 100}%`, height: `${(y1 - y0) * 100}%`,
        });
        highlight.hidden = false;
        slideStatus.textContent = `Vùng tô vàng là bằng chứng ${current.evidenceId || ''}.`;
      } else {
        slideStatus.textContent = '';
      }
    };
    image.onerror = () => { slideStatus.textContent = 'Không hiển thị được ảnh. Hãy mở PDF gốc.'; };
    image.src = objectURL;
  } catch (error) {
    if (requestId === requestNumber) slideStatus.textContent = error.message;
  }
}

function openCitation(citation) {
  slideTitle.textContent = `${citation.filename} — Slide ${citation.page_number}`;
  slideSub.textContent = citation.evidence_id ? `Trích dẫn ${citation.evidence_id}` : 'Mở từ sơ đồ tư duy';
  current = {
    file: citation.filename,
    page: citation.page_number,
    evidencePage: citation.page_number,
    bbox: citation.bbox,
    evidenceId: citation.evidence_id,
  };
  renderSlide();
}

prevButton.onclick = () => { if (current && current.page > 1) { current.page--; renderSlide(); } };
nextButton.onclick = () => { if (current) { current.page++; renderSlide(); } };

// ---- Chat thread ---------------------------------------------------------
function scrollToBottom() {
  messages.scrollTop = messages.scrollHeight;
}

function removeWelcome() {
  document.getElementById('welcome')?.remove();
}

function escapeHtml(str) {
  return str.replace(/[&<>"']/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' })[m]);
}

function addUserMessage(text) {
  const msg = document.createElement('div');
  msg.className = 'msg user';
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.textContent = text;
  msg.append(bubble);
  messages.append(msg);
  scrollToBottom();
}

function addTypingIndicator() {
  const msg = document.createElement('div');
  msg.className = 'msg ai';
  msg.id = 'typing-indicator';
  const mini = document.createElement('div');
  mini.className = 'mini-ai';
  mini.textContent = '🤖';
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.innerHTML = '<span class="typing-dots"><span></span><span></span><span></span></span>';
  msg.append(mini, bubble);
  messages.append(msg);
  scrollToBottom();
}

function removeTypingIndicator() {
  document.getElementById('typing-indicator')?.remove();
}

function renderAnswerText(container, text, citations) {
  const byId = new Map(citations.map(c => [c.evidence_id, c]));
  const pattern = /\[E\d+\]/g;
  let last = 0;
  let match;
  while ((match = pattern.exec(text))) {
    if (match.index > last) container.append(document.createTextNode(text.slice(last, match.index)));
    const id = match[0].slice(1, -1);
    const citation = byId.get(id);
    if (citation) {
      const chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'citation-chip';
      chip.textContent = match[0];
      chip.title = `${citation.filename} — Slide ${citation.page_number}`;
      chip.addEventListener('click', () => openCitation(citation));
      container.append(chip);
    } else {
      container.append(document.createTextNode(match[0]));
    }
    last = pattern.lastIndex;
  }
  if (last < text.length) container.append(document.createTextNode(text.slice(last)));
}

function addAiMessage(answer, citations, scope) {
  const msg = document.createElement('div');
  msg.className = 'msg ai';
  const mini = document.createElement('div');
  mini.className = 'mini-ai';
  mini.textContent = '🤖';
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  if (scope) {
    const scopeTag = document.createElement('div');
    scopeTag.className = 'source';
    scopeTag.textContent = `🔎 Phạm vi: ${scope.map(dayLabel).join(', ')}`;
    bubble.append(scopeTag, document.createElement('br'));
  }
  const textSpan = document.createElement('span');
  renderAnswerText(textSpan, answer, citations);
  bubble.append(textSpan);
  if (citations.length) {
    const row = document.createElement('div');
    row.className = 'source-row';
    for (const citation of citations) {
      const tag = document.createElement('button');
      tag.type = 'button';
      tag.className = 'citation-chip';
      tag.textContent = `📄 ${citation.evidence_id} · Slide ${citation.page_number}`;
      tag.title = citation.filename;
      tag.addEventListener('click', () => openCitation(citation));
      row.append(tag);
    }
    bubble.append(row);
  }
  msg.append(mini, bubble);
  messages.append(msg);
  scrollToBottom();
  if (citations.length) openCitation(citations[0]);
}

async function send() {
  const question = input.value.trim();
  if (!question) return;
  removeWelcome();
  addUserMessage(question);
  input.value = '';
  sendButton.disabled = true;
  status.textContent = '';

  if (MINDMAP_TRIGGER.test(question)) {
    await handleMindmapChat(question);
    sendButton.disabled = false;
    input.focus();
    return;
  }

  onlineStatus.textContent = 'Đang tìm bằng chứng…';
  addTypingIndicator();
  try {
    const scope = selectedScope.length ? selectedScope : null;
    const response = await fetch('/api/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, scope }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Câu hỏi không hợp lệ hoặc máy chủ chưa sẵn sàng.');
    removeTypingIndicator();
    addAiMessage(data.answer, data.citations || [], scope);
  } catch (error) {
    removeTypingIndicator();
    status.textContent = error.message || 'Không kết nối được máy chủ.';
  } finally {
    sendButton.disabled = false;
    onlineStatus.textContent = 'Đang sẵn sàng hỗ trợ bạn học';
    input.focus();
  }
}

sendButton.addEventListener('click', send);
input.addEventListener('keydown', event => { if (event.key === 'Enter') send(); });
document.querySelectorAll('.suggestion[data-ask]').forEach(button => {
  button.addEventListener('click', () => { input.value = button.dataset.ask; send(); });
});
