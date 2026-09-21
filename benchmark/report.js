'use strict';
const menu = document.querySelector('.menu-toggle');
const nav = document.querySelector('#toc');
menu.addEventListener('click', () => {
  const open = nav.classList.toggle('open');
  menu.setAttribute('aria-expanded', String(open));
});
function closeMenu() { nav.classList.remove('open'); menu.setAttribute('aria-expanded', 'false'); }
nav.querySelectorAll('a').forEach(a => a.addEventListener('click', closeMenu));
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeMenu(); });
const links = [...nav.querySelectorAll('a[href^="#"]')];
const sections = links.map(a => document.querySelector(a.hash));
let scheduled = false;
function activeSection() {
  let current = sections[0];
  sections.forEach(s => { if (s.getBoundingClientRect().top <= 150) current = s; });
  links.forEach(a => {
    const active = a.hash === '#' + current.id;
    a.classList.toggle('active', active);
    if (active) a.setAttribute('aria-current', 'location'); else a.removeAttribute('aria-current');
  });
  scheduled = false;
}
window.addEventListener('scroll', () => { if (!scheduled) { scheduled = true; requestAnimationFrame(activeSection); } }, {passive:true});
activeSection();
document.querySelector('#print-report').addEventListener('click', () => window.print());
const methodSelect = document.querySelector('#case-method');
const caseVideo = document.querySelector('#case-video');
methodSelect.addEventListener('change', () => {
  const time = caseVideo.currentTime, playing = !caseVideo.paused;
  caseVideo.pause();
  caseVideo.src = `assets/${methodSelect.value}.mp4`;
  caseVideo.poster = `assets/${methodSelect.value}.jpg`;
  caseVideo.addEventListener('loadedmetadata', async () => {
    caseVideo.currentTime = Math.min(time, Math.max(0, caseVideo.duration - .05));
    if (playing) { try { await caseVideo.play(); } catch { /* Native controls remain usable. */ } }
  }, {once:true});
  document.querySelector('#case-caption').textContent = `${methodSelect.selectedOptions[0].text} · 固定同一源片段的相机系投影。各分支使用其解码出的投影参数；图像贴合不等于相机系深度准确。`;
  caseVideo.load();
});
document.querySelectorAll('[data-sync-group]').forEach(group => {
  const videos = [...group.querySelectorAll('video')];
  group.querySelector('button').addEventListener('click', async () => {
    if (videos.some(v => !v.paused)) { videos.forEach(v => v.pause()); return; }
    videos.forEach(v => { v.currentTime = 0; });
    const outcomes = await Promise.allSettled(videos.map(v => v.play()));
    if (outcomes.some(r => r.status === 'rejected')) videos.forEach(v => v.pause());
  });
});
// Include expandable audit tables when saving the report as a PDF.
let previouslyOpen = [];
window.addEventListener('beforeprint', () => {
  previouslyOpen = [...document.querySelectorAll('details[open]')];
  document.querySelectorAll('details').forEach(d => { d.open = true; });
});
window.addEventListener('afterprint', () => {
  document.querySelectorAll('details').forEach(d => { d.open = previouslyOpen.includes(d); });
});
