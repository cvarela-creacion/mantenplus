/* Pruebas de la página MantenPlus en Chromium real (Playwright) + accesibilidad (axe-core).
   Uso: npm ci && npm test   (CHROMIUM_PATH=/ruta/a/chromium si Playwright no trae su navegador) */
const http = require('http');
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const ROOT = path.resolve(__dirname, '..');
const AXE = fs.readFileSync(require.resolve('axe-core/axe.min.js'), 'utf8');
const TYPES = { '.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript', '.svg': 'image/svg+xml', '.webp': 'image/webp', '.jpg': 'image/jpeg', '.png': 'image/png', '.woff2': 'font/woff2', '.xml': 'application/xml', '.txt': 'text/plain' };

const results = [];
const check = (name, ok, detail = '') => { results.push({ name, ok, detail }); console.log(`${ok ? '✓' : '✗'} ${name}${detail ? ` — ${detail}` : ''}`); };

// Servidor estático mínimo: prueba el sitio tal como lo sirve GitHub Pages
const server = http.createServer((req, res) => {
  const file = path.join(ROOT, decodeURIComponent(new URL(req.url, 'http://x').pathname).replace(/\/$/, '/index.html'));
  if (!file.startsWith(ROOT) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'Content-Type': TYPES[path.extname(file)] || 'application/octet-stream' });
  fs.createReadStream(file).pipe(res);
});

(async () => {
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  const URL_BASE = `http://127.0.0.1:${server.address().port}/index.html`;
  const browser = await chromium.launch(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {});

  const open = async (viewport, extra = {}) => {
    const mobile = viewport.width < 861;
    const page = await browser.newPage({ viewport, isMobile: mobile, hasTouch: mobile, ...extra });
    const problems = [];
    page.on('pageerror', (e) => problems.push(`JS: ${e.message}`));
    page.on('requestfailed', (r) => problems.push(`fallida: ${r.url()}`));
    page.on('response', (r) => { if (r.status() >= 400) problems.push(`HTTP ${r.status()}: ${r.url()}`); });
    await page.goto(URL_BASE, { waitUntil: 'networkidle' });
    return { page, problems };
  };
  const scrollAll = (page) => page.evaluate(async () => { for (let y = 0; y < document.body.scrollHeight; y += 500) { scrollTo(0, y); await new Promise((r) => setTimeout(r, 30)); } scrollTo(0, 0); });

  // 1. Recorrido base en cuatro anchos
  for (const width of [390, 820, 1440, 1920]) {
    const { page, problems } = await open({ width, height: width < 861 ? 844 : 900 });
    await scrollAll(page);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - innerWidth);
    check(`${width} px: sin scroll horizontal`, overflow <= 0, overflow > 0 ? `${overflow} px de más` : '');
    check(`${width} px: sin errores JS ni peticiones fallidas`, problems.length === 0, problems.join(' | '));
    check(`${width} px: no pide medios pendientes`, await page.evaluate(() => !document.querySelector('video') && performance.getEntriesByType('resource').every((e) => !/assets\/(video|img\/proceso|img\/equipo)/.test(e.name))));
    await page.close();
  }

  // 2. Menú móvil: ocupa la pantalla, todo alcanzable (también en teléfonos bajos), foco dentro, resto inerte
  for (const [width, height] of [[390, 844], [375, 667], [820, 1180]]) {
    const { page } = await open({ width, height });
    await page.click('[data-menu-toggle]');
    await page.waitForTimeout(450); // fin de la animación de apertura
    const m = await page.evaluate(() => {
      const menu = document.querySelector('[data-mobile-menu]');
      menu.scrollTop = menu.scrollHeight;
      const last = [...menu.querySelectorAll('a')].pop().getBoundingClientRect();
      return { bottom: menu.getBoundingClientRect().bottom, h: menu.getBoundingClientRect().height, lastReachable: last.bottom <= innerHeight, focusIn: menu.contains(document.activeElement), inert: document.querySelector('main').inert };
    });
    check(`${width}×${height}: menú a pantalla completa y todo alcanzable`, m.bottom >= height - 2 && m.lastReachable, `alto ${Math.round(m.h)} px`);
    check(`${width} px: foco dentro del menú y página inerte`, m.focusIn && m.inert);
    await page.keyboard.press('Escape');
    check(`${width} px: Escape cierra y devuelve el foco`, await page.evaluate(() => document.querySelector('[data-mobile-menu]').hidden && document.activeElement.matches('[data-menu-toggle]')));
    await page.close();
  }

  // 3. Interacciones en escritorio
  {
    const { page } = await open({ width: 1440, height: 900 });
    // Selector de equipo + avería → diálogo de revisión (número provisorio)
    await page.click('label.chip:has(input[value="refrigerador"])');
    const issues = await page.$$eval('[data-issue-chips] input', (els) => els.map((e) => e.value));
    check('Selector: averías del refrigerador', issues.includes('No enfría'), issues.join(', '));
    await page.click('[data-issue-chips] label.chip:has(input[value="No enfría"])');
    await page.click('[data-quick-book] button[type=submit]');
    const msg = await page.inputValue('[data-message-text]');
    check('Selector: mensaje con equipo y avería en el diálogo', /refrigerador\. Problema: no enfría\./.test(msg), msg);
    await page.keyboard.press('Escape');
    await page.click('label.chip:has(input[value="otro equipo"])');
    check('Selector: «Otro» oculta el paso de avería', await page.isHidden('[data-issues]'));
    // Enlaces de WhatsApp en modo revisión
    await page.click('.service__link >> nth=1');
    check('WhatsApp provisorio: abre el diálogo con el mensaje', /refrigerador/.test(await page.inputValue('[data-message-text]')));
    await page.click('[data-close-dialog]');
    // Comparador y pestañas
    await page.focus('#caso-lavadora .ba__range'); await page.keyboard.press('ArrowRight');
    check('Comparador: teclado mueve el tirador', (await page.$eval('#caso-lavadora [data-ba]', (e) => e.style.getPropertyValue('--pos'))) === '51%');
    await page.click('#tab-campana');
    check('Comparador: pestañas cambian de caso', await page.isVisible('#caso-campana') && await page.isHidden('#caso-lavadora'));
    // Carrusel sin avance automático
    await page.locator('#como-trabajamos').scrollIntoViewIfNeeded(); await page.waitForTimeout(7000);
    const active = () => page.evaluate(() => [...document.querySelectorAll('[data-step]')].findIndex((s) => s.classList.contains('is-active')));
    check('Carrusel: no avanza solo', (await active()) === 0);
    await page.click('[data-dot] >> nth=2');
    check('Carrusel: los pasos numerados seleccionan', (await active()) === 2);
    // Explorador de piezas
    await page.click('[data-part="7"]');
    check('Explorador: selección de pieza y explicación', await page.evaluate(() => document.querySelector('[data-part="7"]').getAttribute('aria-pressed') === 'true' && document.querySelector('[data-xp-callout="7"]').classList.contains('is-selected') && /Bomba/.test(document.querySelector('[data-part-detail]').textContent)));
    // Cobertura
    for (const [q, cls] of [['nunoa', 'is-ok'], ['Chicureo', 'is-ok'], ['Maipú', 'is-maybe'], ['Narnia', 'is-error']]) {
      await page.fill('#checker-comuna', q); await page.click('[data-checker] button');
      check(`Cobertura: «${q}»`, (await page.getAttribute('[data-checker-result]', 'class')).includes(cls));
    }
    // Formulario de contacto
    await page.click('[data-contact-form] button[type=submit]');
    check('Contacto: campos vacíos no avanzan', !(await page.evaluate(() => document.querySelector('[data-message-dialog]').open)));
    await page.fill('#cf-nombre', 'Ana'); await page.fill('#cf-comuna', 'Las Condes'); await page.selectOption('#cf-equipo', 'Horno'); await page.fill('#cf-detalle', 'no calienta');
    await page.click('[data-contact-form] button[type=submit]');
    check('Contacto: mensaje completo', /soy Ana[\s\S]*horno en Las Condes[\s\S]*Problema: no calienta/.test(await page.inputValue('[data-message-text]')));
    await page.close();
  }

  // 4. Carrusel en móvil
  {
    const { page } = await open({ width: 390, height: 844 });
    await page.locator('.story').scrollIntoViewIfNeeded();
    await page.click('[data-story-next]'); await page.waitForTimeout(900);
    check('390 px: carrusel avanza con la flecha', await page.evaluate(() => document.querySelectorAll('[data-step]')[1].classList.contains('is-active')));
    await page.close();
  }

  // 5. Movimiento reducido: despiece abierto y números visibles sin animación
  {
    const { page } = await open({ width: 1440, height: 900 }, { reducedMotion: 'reduce' });
    check('Movimiento reducido: despiece completo visible', await page.evaluate(() => !document.querySelector('[data-xp]').classList.contains('is-enhanced')));
    await page.close();
  }

  // 6. Accesibilidad WCAG 2.1 A/AA (axe-core)
  for (const width of [390, 1440]) {
    const { page } = await open({ width, height: 900 });
    await scrollAll(page); await page.waitForTimeout(500);
    await page.addScriptTag({ content: AXE });
    const v = await page.evaluate(async () => (await axe.run(document, { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa'] } })).violations.map((x) => `${x.id} (${x.nodes.length})`));
    check(`${width} px: axe sin infracciones WCAG A/AA`, v.length === 0, v.join(', '));
    await page.close();
  }

  await browser.close();
  server.close();
  const failed = results.filter((r) => !r.ok).length;
  console.log(`\n${results.length - failed}/${results.length} pruebas superadas`);
  process.exit(failed ? 1 : 0);
})().catch((e) => { console.error(e); server.close(); process.exit(1); });
