const form = document.getElementById('ask-form');
const button = document.getElementById('ask');
const status = document.getElementById('status');
const daySelect = document.getElementById('day');
async function fetchWithTimeout(url, options = {}, milliseconds = 60000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), milliseconds);
  try {
    const response = await fetch(url, {...options, signal: controller.signal});
    const data = await response.json();
    return {response, data};
  } finally { clearTimeout(timer); }
}
async function loadDays() {
  try {
    const {response, data: catalog} = await fetchWithTimeout('/api/days', {}, 8000);
    if (!response.ok) throw new Error('Không tải được danh sách ngày học.');
    for (const day of catalog.days) {
      const option = document.createElement('option');
      option.value = day.day_id;
      option.textContent = `${day.day_label} (${day.document_count} tài liệu)`;
      daySelect.append(option);
    }
    if (catalog.unassigned_document_count) {
      document.getElementById('day-status').textContent = `${catalog.unassigned_document_count} tài liệu chưa được gán ngày học; có thể tìm trong phạm vi tất cả ngày.`;
    }
  } catch (error) {
    document.getElementById('day-status').textContent = error.name === 'AbortError' ? 'Danh sách ngày học chưa phản hồi. Bạn vẫn có thể hỏi trên toàn kho.' : error.message;
  }
}
loadDays();
form.addEventListener('submit', async event => {
  event.preventDefault();
  const question = document.getElementById('question').value.trim();
  if (!question) { status.textContent = 'Vui lòng nhập câu hỏi.'; return; }
  button.disabled = true;
  daySelect.disabled = true;
  status.className = '';
  status.textContent = 'Đang tìm bằng chứng và tạo câu trả lời…';
  document.getElementById('result').hidden = true;
  try {
    const request = {question};
    if (daySelect.value) request.day_id = daySelect.value;
    const {response, data} = await fetchWithTimeout('/api/ask', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(request)});
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
      if (citation.day_label) role.textContent += ` · ${citation.day_label}`;
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
    status.textContent = error.name === 'AbortError' ? 'Câu hỏi quá thời gian chờ. Vui lòng thử lại; nếu liên tục gặp lỗi, kiểm tra log máy chủ.' : error.message || 'Không kết nối được máy chủ.';
  } finally { button.disabled = false; daySelect.disabled = false; }
});
