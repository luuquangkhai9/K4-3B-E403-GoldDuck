const form = document.getElementById('ask-form');
const button = document.getElementById('ask');
const status = document.getElementById('status');
form.addEventListener('submit', async event => {
  event.preventDefault();
  const question = document.getElementById('question').value.trim();
  if (!question) { status.textContent = 'Vui lòng nhập câu hỏi.'; return; }
  button.disabled = true;
  status.className = '';
  status.textContent = 'Đang tìm bằng chứng và tạo câu trả lời…';
  document.getElementById('result').hidden = true;
  try {
    const response = await fetch('/api/ask', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({question})});
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Câu hỏi không hợp lệ hoặc máy chủ chưa sẵn sàng.');
    document.getElementById('answer').textContent = data.answer;
    const sources = document.getElementById('sources');
    sources.replaceChildren();
    for (const citation of data.citations) {
      const article = document.createElement('article');
      const title = document.createElement('strong');
      title.textContent = `[${citation.evidence_id}] ${citation.filename} — Slide ${citation.page_number}`;
      const role = document.createElement('p');
      role.className = 'muted';
      role.textContent = citation.source_role === 'neighbor' ? 'Nguồn bổ sung từ slide lân cận' : 'Nguồn chính';
      if (citation.vision_used) role.textContent += ' · Có phân tích hình ảnh';
      if (citation.evidence_type === 'visual') role.textContent += ' · Bằng chứng là mô tả hình ảnh do Vision tạo';
      const quote = document.createElement('blockquote');
      quote.textContent = citation.quote;
      const link = document.createElement('a');
      link.textContent = 'Mở nguồn bằng chứng';
      link.href = citation.viewer_url;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      article.append(title, role, quote, link);
      sources.append(article);
    }
    if (!data.citations.length) sources.textContent = 'Không có bằng chứng đủ phù hợp trong kho bài giảng.';
    const debug = document.getElementById('debug');
    debug.hidden = !data.debug && !data.grounding;
    document.getElementById('debug-content').textContent = JSON.stringify({retrieval: data.debug, grounding: data.grounding}, null, 2);
    document.getElementById('result').hidden = false;
    status.textContent = '';
  } catch (error) {
    status.className = 'error';
    status.textContent = error.message || 'Không kết nối được máy chủ.';
  } finally { button.disabled = false; }
});
