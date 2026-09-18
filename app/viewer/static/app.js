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
      const quote = document.createElement('blockquote');
      quote.textContent = citation.quote;
      const link = document.createElement('a');
      link.textContent = 'Mở nguồn bằng chứng';
      link.href = citation.viewer_url;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      article.append(title, quote, link);
      sources.append(article);
    }
    if (!data.citations.length) sources.textContent = 'Không có bằng chứng đủ phù hợp trong kho bài giảng.';
    document.getElementById('result').hidden = false;
    status.textContent = '';
  } catch (error) {
    status.className = 'error';
    status.textContent = error.message || 'Không kết nối được máy chủ.';
  } finally { button.disabled = false; }
});
