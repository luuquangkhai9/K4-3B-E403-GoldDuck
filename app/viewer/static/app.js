const input = document.getElementById('input');
const sendButton = document.getElementById('send');
const status = document.getElementById('status');
const messages = document.getElementById('messages');
const onlineStatus = document.getElementById('online-status');

// ---- Review scope (which lessons to ground answers in) -----------------
const scopeList = document.getElementById('scope-list');
const scopeAllItem = document.getElementById('scope-all');
let selectedScope = []; // empty = whole course

function lessonLabel(id) {
  const match = /^Day0*(\d+)$/i.exec(id);
  return match ? `Buổi ${match[1]}: ${id.toUpperCase()}` : id;
}

function updateScopeUI() {
  scopeAllItem.classList.toggle('active', selectedScope.length === 0);
  scopeList.querySelectorAll('.scope-item[data-lesson]').forEach(item => {
    item.classList.toggle('active', selectedScope.includes(item.dataset.lesson));
  });
}

scopeAllItem.addEventListener('click', () => { selectedScope = []; updateScopeUI(); });

async function loadLessons() {
  try {
    const response = await fetch('/api/lessons');
    if (!response.ok) return;
    const data = await response.json();
    for (const lesson of data.lessons || []) {
      const item = document.createElement('div');
      item.className = 'scope-item';
      item.dataset.lesson = lesson;
      item.textContent = `📖 ${lessonLabel(lesson)}`;
      item.addEventListener('click', () => {
        selectedScope = selectedScope.includes(lesson)
          ? selectedScope.filter(day => day !== lesson)
          : [...selectedScope, lesson];
        updateScopeUI();
      });
      scopeList.append(item);
    }
  } catch { /* lesson picker is a convenience; question answering still works without it */ }
}
loadLessons();

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
  slideSub.textContent = `Trích dẫn ${citation.evidence_id}`;
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
    scopeTag.textContent = `🔎 Phạm vi: ${scope.map(lessonLabel).join(', ')}`;
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
