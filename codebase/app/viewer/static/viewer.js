const params = new URLSearchParams(location.search);
const file = params.get('file') || '';
let page = Number(params.get('page')) || 1;
const evidencePage = page;
const box = (params.get('bbox') || '').split(',').map(Number);
const validBox = box.length === 4 && box.every(v => Number.isFinite(v) && v >= 0 && v <= 1) && box[0] < box[2] && box[1] < box[3];
const image = document.getElementById('slide');
const highlight = document.getElementById('highlight');
const message = document.getElementById('status');
let objectURL;
let requestNumber = 0;
document.getElementById('title').textContent = file;
async function render() {
  const currentRequest = ++requestNumber;
  const currentPage = page;
  document.getElementById('page-label').textContent = `Slide ${page}`;
  document.getElementById('previous').disabled = page <= 1;
  document.getElementById('original').href = '/pdf/' + file.split('/').map(encodeURIComponent).join('/') + '#page=' + page;
  image.hidden = true;
  highlight.hidden = true;
  message.textContent = 'Đang tải trang…';
  try {
    const response = await fetch('/api/page?' + new URLSearchParams({file, page: currentPage}));
    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.detail || 'Không tải được trang. Hãy mở PDF gốc.');
    }
    const blob = await response.blob();
    if (currentRequest !== requestNumber) return;
    if (objectURL) URL.revokeObjectURL(objectURL);
    objectURL = URL.createObjectURL(blob);
    image.onload = () => {
      if (currentRequest !== requestNumber) return;
      image.hidden = false;
      message.textContent = currentPage === evidencePage && validBox ? `Vùng tô vàng là bằng chứng ${params.get('evidence') || ''}.` : '';
      if (currentPage === evidencePage && validBox) {
        Object.assign(highlight.style, {left: `${box[0]*100}%`, top: `${box[1]*100}%`, width: `${(box[2]-box[0])*100}%`, height: `${(box[3]-box[1])*100}%`});
        highlight.hidden = false;
      }
    };
    image.onerror = () => { message.textContent = 'Không hiển thị được ảnh. Hãy mở PDF gốc.'; };
    image.src = objectURL;
  } catch(error) { if (currentRequest === requestNumber) message.textContent = error.message; }
}
document.getElementById('previous').onclick = () => { if(page > 1) { page--; render(); } };
document.getElementById('next').onclick = () => { page++; render(); };
render();
