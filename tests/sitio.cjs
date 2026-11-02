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
  const ORIGIN = `http://127.0.0.1:${server.address().port}`;
  const browser = await chromium.launch(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {});

  const open = async (viewport, extra = {}, file = 'index.html') => {
    const mobile = viewport.width < 861;
    const page = await browser.newPage({ viewport, isMobile: mobile, hasTouch: mobile, ...extra });
    const problems = [];
    page.on('pageerror', (e) => problems.push(`JS: ${e.message}`));
    page.on('requestfailed', (r) => problems.push(`fallida: ${r.url()}`));
    page.on('response', (r) => { if (r.status() >= 400) problems.push(`HTTP ${r.status()}: ${r.url()}`); });
    await page.goto(`${ORIGIN}/${file}`, { waitUntil: 'networkidle' });
    return { page, problems };
  };
  const scrollAll = (page) => page.evaluate(async () => { for (let y = 0; y < document.body.scrollHeight; y += 500) { scrollTo(0, y); await new Promise((r) => setTimeout(r, 30)); } scrollTo(0, 0); });

  // 1. Recorrido base de las dos páginas en cuatro anchos
  for (const file of ['index.html', 'galeria.html']) {
    for (const width of [390, 820, 1440, 1920]) {
      const { page, problems } = await open({ width, height: width < 861 ? 844 : 900 }, {}, file);
      await scrollAll(page);
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - innerWidth);
      check(`${file} ${width} px: sin scroll horizontal`, overflow <= 0, overflow > 0 ? `${overflow} px de más` : '');
      check(`${file} ${width} px: sin errores JS ni peticiones fallidas`, problems.length === 0, problems.join(' | '));
      check(`${file} ${width} px: no pide videos pendientes`, await page.evaluate(() => !document.querySelector('video') && performance.getEntriesByType('resource').every((e) => !/assets\/video\//.test(e.name))));
      // Fuerza la carga de las fotos diferidas y comprueba que todos los archivos existan
      await page.evaluate(() => document.querySelectorAll('img[loading="lazy"]').forEach((i) => { i.loading = 'eager'; }));
      const fotosOk = await page.waitForFunction(() => [...document.images].filter((i) => i.offsetParent).every((i) => i.complete && i.naturalWidth > 0), null, { timeout: 8000 }).then(() => true, () => false);
      check(`${file} ${width} px: todas las fotos visibles cargan`, fotosOk);
      check(`${file} ${width} px: íconos SVG del sitio apuntan al sprite de la misma página`, await page.evaluate(() => [...document.querySelectorAll('use')].every((u) => /^#/.test(u.getAttribute('href')) && document.getElementById(u.getAttribute('href').slice(1)))));
      check(`${file} ${width} px: logo con eslogan y botón verde de WhatsApp visibles`, await page.evaluate(() => {
        const tag = document.querySelector('.brand__tagline'); const fab = document.querySelector('[data-wa-fab]');
        return tag.offsetHeight > 0 && /cuidado y reparación/.test(tag.textContent) && fab.offsetHeight > 0 && getComputedStyle(fab.querySelector('.wa-fab__circle')).backgroundColor === 'rgb(37, 211, 102)';
      }));
      await page.close();
    }
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
    // Estructura acordada: sin lavadora vectorial; con instalación, galería y empresas
    check('Estructura: sin la sección de la lavadora desarmada', await page.evaluate(() => !document.querySelector('#ingenieria, [data-xp]')));
    check('Estructura: secciones de instalación, galería y empresas', await page.evaluate(() => ['instalacion', 'galeria', 'empresas'].every((id) => document.getElementById(id))));
    check('Galería: 6 fotos en cuadrícula y enlace a la galería completa', await page.evaluate(() => document.querySelectorAll('#galeria .g-tile img').length === 6 && !!document.querySelector('#galeria a[href="galeria.html"]')));
    check('Instalación: sin el botón «Proyectos para empresas»', await page.evaluate(() => !/Proyectos para empresas/.test(document.getElementById('instalacion').textContent)));
    check('Herramientas: dos fotos', await page.evaluate(() => document.querySelectorAll('.tools .g-tile img').length === 2));
    // Resultados: siete casos; cada pestaña muestra sus dos fotos
    const tabs = await page.$$eval('[data-tabs] [role="tab"]', (els) => els.map((e) => e.id));
    check('Resultados: siete pestañas', tabs.join() === 'tab-lavadora,tab-secadora,tab-lavavajillas,tab-horno,tab-microondas,tab-encimera,tab-campana', tabs.join());
    let allCases = true;
    for (const id of tabs) {
      await page.click(`#${id}`);
      const panel = await page.getAttribute(`#${id}`, 'aria-controls');
      await page.locator(`#${panel} [data-ba]`).scrollIntoViewIfNeeded();
      await page.waitForFunction((pid) => [...document.querySelectorAll(`#${pid} img`)].every((i) => i.complete && i.naturalWidth > 0), panel, { timeout: 5000 }).catch(() => { allCases = false; });
    }
    check('Resultados: las 7 pestañas cargan antes y después', allCases);
    await page.click('#tab-lavadora');
    check('Antes/después: fotos (no ilustraciones)', await page.evaluate(() => [...document.querySelectorAll('[data-ba] img')].every((i) => /\.webp$/.test(i.currentSrc || i.src))));
    // Contacto: WhatsApp, llamada al móvil y correo; redes con colores de marca
    check('Contacto: WhatsApp, llamada y correo', await page.evaluate(() => ['wa.me/', 'tel:+569', 'mailto:contacto@mantenplus.cl'].every((h) => document.querySelector(`#contacto .channel[href*="${h}"]`))));
    check('Redes: Facebook azul e Instagram con degradado', await page.evaluate(() => getComputedStyle(document.querySelector('.site-footer .social__link--fb')).backgroundColor === 'rgb(24, 119, 242)' && getComputedStyle(document.querySelector('.site-footer .social__link--ig')).backgroundImage.includes('gradient')));
    await page.click('#contacto .channel[href^="tel:"]');
    check('Llamada con número provisorio: avisa en el diálogo', /número móvil definitivo está pendiente/.test(await page.textContent('[data-dialog-lead]')));
    await page.click('[data-close-dialog]');
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

  // 5. Galería completa: filtro por categoría, sin carrusel
  {
    const { page } = await open({ width: 1440, height: 900 }, {}, 'galeria.html');
    const visibles = () => page.evaluate(() => [...document.querySelectorAll('[data-gallery-group]')].filter((g) => !g.hidden).map((g) => g.dataset.galleryGroup).join(','));
    check('Galería completa: tres categorías', (await visibles()) === 'instalacion,reparacion,mantenimiento');
    await page.click('[data-gallery-filter="mantenimiento"]');
    check('Galería completa: el filtro muestra solo mantenimiento', (await visibles()) === 'mantenimiento');
    await page.click('[data-gallery-filter="todas"]');
    check('Galería completa: «Todas» vuelve a mostrar todo', (await visibles()) === 'instalacion,reparacion,mantenimiento');
    await page.close();
  }

  // 6. Accesibilidad WCAG 2.1 A/AA (axe-core)
  for (const file of ['index.html', 'galeria.html']) {
    for (const width of [390, 1440]) {
      const { page } = await open({ width, height: 900 }, {}, file);
      await scrollAll(page); await page.waitForTimeout(500);
      await page.addScriptTag({ content: AXE });
      const v = await page.evaluate(async () => (await axe.run(document, { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa'] } })).violations.map((x) => `${x.id} (${x.nodes.length})`));
      check(`${file} ${width} px: axe sin infracciones WCAG A/AA`, v.length === 0, v.join(', '));
      await page.close();
    }
  }

  await browser.close();
  server.close();
  const failed = results.filter((r) => !r.ok).length;
  console.log(`\n${results.length - failed}/${results.length} pruebas superadas`);
  process.exit(failed ? 1 : 0);
})().catch((e) => { console.error(e); server.close(); process.exit(1); });
