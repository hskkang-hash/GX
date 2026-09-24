// 세종 PDF 렌더러 — 어느 세션에서든 같은 모양이 나오도록 경로를 인자로 받는다.
// 사용: node render.cjs <입력.html(절대경로)> <출력.pdf> <PNG 접두>
// 요구: playwright + chromium (npm i -g playwright && npx playwright install chromium 또는 세션 기본 설치)
const path = require('path');
let chromium;
try { ({ chromium } = require('playwright')); }
catch (e) { ({ chromium } = require(process.env.PLAYWRIGHT_MODULE || '/home/claude/.npm-global/lib/node_modules/playwright')); }
const src = path.resolve(process.argv[2]), out = process.argv[3], pre = process.argv[4] || 'page';
(async () => {
  const b = await chromium.launch();
  const pg = await b.newPage();
  await pg.goto('file://' + src, { waitUntil: 'networkidle' });
  await pg.waitForTimeout(900);
  const h = await pg.evaluate(() => Array.from(document.querySelectorAll('.page')).map(p => p.scrollHeight));
  console.log('heights:', JSON.stringify(h));            // 전부 1123 이어야 한다 — 아니면 넘침
  const over = await pg.evaluate(() => { const out = []; document.querySelectorAll('.page').forEach((p, i) => { const pr = p.getBoundingClientRect(); p.querySelectorAll('*').forEach(el => { const r = el.getBoundingClientRect(); if (r.width && (r.bottom > pr.bottom + 1 || r.right > pr.right + 1)) out.push((i + 1) + ':' + el.tagName + '.' + el.className); }); }); return out; });
  console.log('overflow:', over.length, over.slice(0, 6));  // 0 이어야 한다
  await pg.pdf({ path: out, width: '794px', height: '1123px', printBackground: true });
  const els = await pg.$$('.page');
  for (let i = 0; i < els.length; i++) await els[i].screenshot({ path: `${pre}_${i + 1}.png` });
  await b.close(); console.log('done');
})();
