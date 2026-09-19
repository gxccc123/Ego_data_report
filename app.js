/* The full technical report is visible without JavaScript. */
'use strict';
const $ = (q, root = document) => root.querySelector(q);
const $$ = (q, root = document) => [...root.querySelectorAll(q)];

const menu = $('.menu-toggle'), nav = $('#toc');
function closeMenu() { nav.classList.remove('open'); menu.setAttribute('aria-expanded', 'false'); }
menu.addEventListener('click', () => {
  const open = !nav.classList.contains('open');
  nav.classList.toggle('open', open); menu.setAttribute('aria-expanded', String(open));
});
$$('a', nav).forEach(a => a.addEventListener('click', closeMenu));
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeMenu(); });
const sectionLinks = $$('a[href^="#"]', nav);
const sections = sectionLinks.map(a => document.querySelector(a.hash));
let scheduled = false;
function highlightSection() {
  let selected = sections[0];
  for (const section of sections) if (section.getBoundingClientRect().top <= 150) selected = section;
  sectionLinks.forEach(a => {
    const active = a.hash === '#' + selected.id;
    a.classList.toggle('active', active);
    if (active) a.setAttribute('aria-current', 'location'); else a.removeAttribute('aria-current');
  });
  scheduled = false;
}
window.addEventListener('scroll', () => {
  if (!scheduled) { scheduled = true; requestAnimationFrame(highlightSection); }
}, { passive: true });
highlightSection();

const dialog = $('#image-dialog'), modalImage = $('#dialog-image'), area = $('.dialog-image-area');
let zoom = 1, opener = null;
function fitImage() {
  const w = Math.max(1, area.clientWidth - 40), h = Math.max(1, area.clientHeight - 40);
  const fittedWidth = Math.min(w, h * modalImage.naturalWidth / modalImage.naturalHeight, modalImage.naturalWidth);
  if (Number.isFinite(fittedWidth)) modalImage.style.width = `${fittedWidth * zoom}px`;
  $('#zoom-out').disabled = zoom <= .5; $('#zoom-in').disabled = zoom >= 4;
}
modalImage.addEventListener('load', fitImage);
$$('[data-image]').forEach(button => button.addEventListener('click', () => {
  opener = button; zoom = 1;
  modalImage.src = button.dataset.image; modalImage.alt = button.dataset.caption;
  $('#dialog-caption').textContent = button.dataset.caption;
  $('#original-link').href = button.dataset.image;
  dialog.showModal(); document.body.style.overflow = 'hidden';
  fitImage(); area.scrollTo(0, 0);
}));
$('#close-dialog').addEventListener('click', () => dialog.close());
dialog.addEventListener('close', () => { document.body.style.overflow = ''; if (opener) opener.focus({ preventScroll: true }); });
$('#zoom-in').addEventListener('click', () => { zoom = Math.min(4, zoom + .5); fitImage(); });
$('#zoom-out').addEventListener('click', () => { zoom = Math.max(.5, zoom - .5); fitImage(); });
$('#zoom-reset').addEventListener('click', () => { zoom = 1; fitImage(); area.scrollTo(0, 0); });
window.addEventListener('resize', () => { if (dialog.open) fitImage(); });

let toastTimer;
function toast(message) {
  const element = $('.toast'); element.textContent = message; element.classList.add('visible');
  clearTimeout(toastTimer); toastTimer = setTimeout(() => element.classList.remove('visible'), 3500);
}
$$('[data-copy]').forEach(button => button.addEventListener('click', async () => {
  const element = document.getElementById(button.dataset.copy);
  try {
    if (!navigator.clipboard) throw new Error('Clipboard unavailable');
    await navigator.clipboard.writeText(element.innerText);
    toast('已复制。先替换示例路径并确认环境与相机 profile。');
  } catch {
    const range = document.createRange(); range.selectNodeContents(element);
    const selection = window.getSelection(); selection.removeAllRanges(); selection.addRange(range);
    toast('未获剪贴板权限，已选中代码，可手动复制。');
  }
}));

function renderCoverage() {
  if (!window.PRODUCTION_DATA) return;
  const ns = 'http://www.w3.org/2000/svg', container = $('#coverage-tracks');
  for (const [id, data] of Object.entries(window.PRODUCTION_DATA)) {
    const row = document.createElement('div'); row.className = 'coverage-item';
    const heading = document.createElement('h3');
    heading.innerHTML = `<strong>${id}</strong><span>${data.frame_count.toLocaleString('en-US')} 帧 · 原始 valid_mask</span>`;
    row.append(heading);
    ['左手', '右手'].forEach((hand, i) => {
      const lane = document.createElement('div'); lane.className = 'coverage-lane';
      const label = document.createElement('span'); label.textContent = hand; lane.append(label);
      const svg = document.createElementNS(ns, 'svg');
      svg.setAttribute('viewBox', `0 0 ${data.frame_count} 20`); svg.setAttribute('preserveAspectRatio', 'none');
      svg.setAttribute('role', 'img');
      const ratio = i ? data.right_valid_ratio : data.left_valid_ratio;
      const description = `${id} ${hand}：${data.frame_count} 帧，有效 ${(ratio * 100).toFixed(1)}%；未叠加 QC 过滤。`;
      svg.setAttribute('aria-label', description);
      const title = document.createElementNS(ns, 'title'); title.textContent = description; svg.append(title);
      data.valid_runs[i].forEach(([start, end]) => {
        const rect = document.createElementNS(ns, 'rect');
        rect.setAttribute('x', start); rect.setAttribute('y', 0); rect.setAttribute('width', end - start);
        rect.setAttribute('height', 20); rect.setAttribute('fill', '#537d6d'); svg.append(rect);
      });
      lane.append(svg);
      const value = document.createElement('b'); value.textContent = `${(ratio * 100).toFixed(1)}%`;
      lane.append(value); row.append(lane);
    });
    const axis = document.createElement('div'); axis.className = 'coverage-axis';
    axis.innerHTML = `<span>frame 0</span><span>${data.frame_count - 1}</span>`; row.append(axis); container.append(row);
  }
}
renderCoverage();
