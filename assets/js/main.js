/* MantenPlus · interacciones del sitio (sin dependencias) */
(() => {
  const WA_NUMBER = '569XXXXXXXX'; // TODO: reemplazar por el número de WhatsApp Business (569 + 8 dígitos)
  const WA_READY = /^569\d{8}$/.test(WA_NUMBER);
  const waLink = (text) => `https://wa.me/${WA_NUMBER}?text=${encodeURIComponent(text)}`;

  // Modo revisión (idea de la propuesta Codex): mientras el número sea provisorio, en vez de abrir un WhatsApp
  // que fallaría, se muestra el mensaje para revisarlo, copiarlo o mandarlo por correo. Con el número real, abre WhatsApp directo.
  const dialog = document.querySelector('[data-message-dialog]');
  const sendWhatsApp = (message) => {
    if (WA_READY || !dialog) return void window.open(waLink(message), '_blank', 'noopener');
    dialog.querySelector('[data-message-text]').value = message;
    dialog.querySelector('[data-copy-status]').textContent = '';
    dialog.querySelector('[data-mail-message]').href = `mailto:contacto@mantenplus.cl?subject=${encodeURIComponent('Consulta desde mantenplus.cl')}&body=${encodeURIComponent(message)}`;
    dialog.showModal();
  };
  if (dialog) {
    const area = dialog.querySelector('[data-message-text]');
    const status = dialog.querySelector('[data-copy-status]');
    dialog.querySelector('[data-copy-message]').addEventListener('click', async () => {
      try { await navigator.clipboard.writeText(area.value); status.textContent = 'Mensaje copiado.'; }
      catch { area.select(); status.textContent = 'Selecciona el texto y cópialo desde el menú de tu dispositivo.'; }
    });
    area.addEventListener('input', () => {
      dialog.querySelector('[data-mail-message]').href = `mailto:contacto@mantenplus.cl?subject=${encodeURIComponent('Consulta desde mantenplus.cl')}&body=${encodeURIComponent(area.value)}`;
    });
    dialog.querySelector('[data-close-dialog]').addEventListener('click', () => dialog.close());
    dialog.addEventListener('click', (e) => { if (e.target === dialog) dialog.close(); }); // clic fuera del panel
  }
  if (!WA_READY) {
    document.addEventListener('click', (e) => {
      const a = e.target.closest('a[href*="wa.me/"]');
      if (!a) return;
      e.preventDefault();
      sendWhatsApp(new URL(a.href).searchParams.get('text') || 'Hola MantenPlus, quiero agendar un servicio.');
    });
  }

  // Header: sombra al hacer scroll + barra CTA móvil fuera del Hero, del Contacto y del footer
  const header = document.querySelector('[data-header]');
  const mobileCta = document.querySelector('[data-mobile-cta]');
  const hero = document.querySelector('.hero__ctas');

  const onScroll = () => header.classList.toggle('is-scrolled', window.scrollY > 8);
  onScroll();
  window.addEventListener('scroll', onScroll, { passive: true });

  if (mobileCta && hero && 'IntersectionObserver' in window) {
    const visible = new Set(); // la barra se oculta mientras ya hay una CTA a la vista
    const ctaIo = new IntersectionObserver((entries) => {
      entries.forEach((e) => (e.isIntersecting ? visible.add(e.target) : visible.delete(e.target)));
      mobileCta.classList.toggle('is-visible', visible.size === 0);
    });
    [hero, document.getElementById('contacto'), document.querySelector('.site-footer')].forEach((el) => el && ctaIo.observe(el));
  } else if (mobileCta) {
    mobileCta.classList.add('is-visible');
  }

  // Menú móvil
  const toggle = document.querySelector('[data-menu-toggle]');
  const menu = document.querySelector('[data-mobile-menu]');
  // Mientras el menú está abierto, el resto de la página queda inerte (ni foco ni lector de pantalla)
  const outside = [document.querySelector('main'), document.querySelector('.site-footer'), mobileCta].filter(Boolean);
  const setMenu = (open, { restoreFocus = true } = {}) => {
    toggle.setAttribute('aria-expanded', String(open));
    toggle.querySelector('.visually-hidden').textContent = open ? 'Cerrar menú' : 'Abrir menú';
    menu.hidden = !open;
    document.body.style.overflow = open ? 'hidden' : '';
    outside.forEach((el) => { el.inert = open; });
    if (open) menu.querySelector('a').focus();
    else if (restoreFocus) toggle.focus();
  };
  toggle.addEventListener('click', () => setMenu(menu.hidden));
  menu.addEventListener('click', (e) => { if (e.target.closest('a')) setMenu(false, { restoreFocus: false }); });
  document.addEventListener('keydown', (e) => {
    if (menu.hidden) return;
    if (e.key === 'Escape') return setMenu(false);
    if (e.key !== 'Tab') return;
    // El foco recorre en círculo el botón del menú y los enlaces del panel
    const focusables = [toggle, ...menu.querySelectorAll('a, button')];
    const i = focusables.indexOf(document.activeElement);
    e.preventDefault();
    focusables[(i + (e.shiftKey ? -1 : 1) + focusables.length) % focusables.length].focus();
  });
  matchMedia('(min-width: 1181px)').addEventListener('change', (e) => { if (e.matches && !menu.hidden) setMenu(false, { restoreFocus: false }); });

  // Agendamiento rápido: el equipo (paso 1) y la avería opcional (paso 2) viajan en el mensaje
  const form = document.querySelector('[data-quick-book]');
  if (form) {
    const text = form.querySelector('[data-wa-text]');
    const issues = form.querySelector('[data-issues]');
    const issueChips = form.querySelector('[data-issue-chips]');
    const chip = (value, label, checked) => {
      const wrap = document.createElement('label');
      wrap.className = 'chip';
      const input = Object.assign(document.createElement('input'), { type: 'radio', name: 'averia', value, checked });
      const span = document.createElement('span');
      span.textContent = label;
      wrap.append(input, span);
      return wrap;
    };
    const selected = (name) => form.querySelector(`input[name="${name}"]:checked`);
    const renderIssues = () => {
      const averias = selected('equipo')?.dataset.averias;
      issues.hidden = !averias;
      if (averias) issueChips.replaceChildren(chip('', 'No estoy seguro', true), ...averias.split('|').map((a) => chip(a, a, false)));
    };
    const sync = () => {
      const equipo = selected('equipo')?.value || 'electrodoméstico';
      const averia = selected('averia')?.value;
      text.value = `Hola MantenPlus, quiero agendar un servicio para mi ${equipo}.` + (averia ? ` Problema: ${averia.toLowerCase()}.` : '');
    };
    form.addEventListener('change', (e) => {
      if (e.target.name === 'equipo') renderIssues();
      sync();
    });
    renderIssues();
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      sync();
      track('hero_agendar', { equipo: selected('equipo')?.value, averia: selected('averia')?.value || 'sin especificar' });
      sendWhatsApp(text.value);
    });
  }

  const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Micro-videos en bucle: se cargan al acercarse; en escritorio se reproducen al pasar el mouse, en móvil al verse
  const videos = document.querySelectorAll('video.loop');
  if (videos.length && 'IntersectionObserver' in window) {
    const canHover = matchMedia('(hover: hover)').matches;
    const autoplay = !reduceMotion && !navigator.connection?.saveData;
    const io = new IntersectionObserver((entries) => entries.forEach(({ target: v, isIntersecting }) => {
      if (!isIntersecting) return v.pause();
      if (v.preload === 'none') { v.preload = 'metadata'; v.load(); }
      if (autoplay && !canHover) v.play().catch(() => {});
    }), { threshold: 0.35 });

    videos.forEach((v) => {
      // Si el archivo aún no existe, se retira el <video> y queda el ícono de respaldo
      v.querySelector('source:last-of-type')?.addEventListener('error', () => v.remove());
      v.addEventListener('loadeddata', () => v.classList.add('is-ready'));
      if (autoplay && canHover) {
        const card = v.closest('.service');
        card.addEventListener('mouseenter', () => v.play().catch(() => {}));
        card.addEventListener('mouseleave', () => v.pause());
      }
      io.observe(v);
    });
  }

  // Slider antes/después: arrastre con puntero (mouse y touch) + teclado con el input range accesible
  document.querySelectorAll('[data-ba]').forEach((ba) => {
    const range = ba.querySelector('.ba__range');
    const set = (pct) => {
      const v = Math.min(100, Math.max(0, pct));
      ba.style.setProperty('--pos', `${v}%`);
      range.value = v;
    };
    const fromPointer = (e) => {
      const r = ba.getBoundingClientRect();
      set(((e.clientX - r.left) / r.width) * 100);
    };
    ba.addEventListener('pointerdown', (e) => {
      ba.classList.remove('ba--hint');
      ba.classList.add('is-dragging');
      ba.setPointerCapture(e.pointerId);
      fromPointer(e);
    });
    ba.addEventListener('pointermove', (e) => { if (ba.classList.contains('is-dragging')) fromPointer(e); });
    ['pointerup', 'pointercancel'].forEach((t) => ba.addEventListener(t, () => ba.classList.remove('is-dragging')));
    range.addEventListener('input', () => { ba.classList.remove('ba--hint'); set(Number(range.value)); });
    ba.addEventListener('animationend', () => ba.classList.remove('ba--hint'));
  });

  // Pista de interacción: la primera vez que el slider aparece, el tirador se mueve solo una vez
  const firstBa = document.querySelector('[data-ba]');
  if (firstBa && !reduceMotion && 'IntersectionObserver' in window) {
    const hintIo = new IntersectionObserver(([entry]) => {
      if (!entry.isIntersecting) return;
      firstBa.classList.add('ba--hint');
      hintIo.disconnect();
    }, { threshold: 0.6 });
    hintIo.observe(firstBa);
  }

  // Pestañas de casos (patrón ARIA tabs con flechas del teclado)
  document.querySelectorAll('[data-tabs]').forEach((list) => {
    const tabs = [...list.querySelectorAll('[role="tab"]')];
    const select = (tab) => {
      tabs.forEach((t) => {
        const on = t === tab;
        t.setAttribute('aria-selected', String(on));
        t.tabIndex = on ? 0 : -1;
        document.getElementById(t.getAttribute('aria-controls')).hidden = !on;
      });
    };
    tabs.forEach((tab, i) => {
      tab.addEventListener('click', () => select(tab));
      tab.addEventListener('keydown', (e) => {
        const step = { ArrowRight: 1, ArrowLeft: -1 }[e.key];
        if (!step) return;
        const next = tabs[(i + step + tabs.length) % tabs.length];
        select(next);
        next.focus();
      });
    });
  });

  // Storytelling "Cómo trabajamos": el visitante avanza a su ritmo, sin avance automático (criterio de accesibilidad
  // tomado de la propuesta Codex). Escritorio: lista de pasos + imagen; móvil: carrusel deslizable.
  const story = document.querySelector('[data-story]');
  if (story) {
    const steps = [...story.querySelectorAll('[data-step]')];
    const dots = [...story.querySelectorAll('[data-dot]')];
    const rail = story.querySelector('[data-story-track]');
    const desktop = matchMedia('(min-width: 861px)');
    let current = 0;

    const setActive = (i) => {
      current = (i + steps.length) % steps.length;
      steps.forEach((s, n) => {
        s.classList.toggle('is-active', n === current);
        const btn = s.querySelector('[data-step-btn]');
        if (n === current) btn.setAttribute('aria-current', 'step'); else btn.removeAttribute('aria-current');
      });
      dots.forEach((d, n) => d.setAttribute('aria-current', String(n === current)));
    };
    const goTo = (i) => {
      setActive(i);
      if (!desktop.matches) steps[current].scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'nearest', inline: 'start' });
    };

    steps.forEach((s, n) => s.querySelector('[data-step-btn]').addEventListener('click', () => desktop.matches && setActive(n)));
    dots.forEach((d, n) => d.addEventListener('click', () => goTo(n)));
    story.querySelector('[data-story-prev]').addEventListener('click', () => goTo(current - 1));
    story.querySelector('[data-story-next]').addEventListener('click', () => goTo(current + 1));

    // Móvil: el paso activo es la tarjeta más cercana al inicio del carril (en tablet hay dos visibles a la vez)
    rail.addEventListener('scroll', () => {
      if (desktop.matches) return;
      const start = rail.getBoundingClientRect().left + parseFloat(getComputedStyle(rail).paddingLeft);
      const distances = steps.map((st) => Math.abs(st.getBoundingClientRect().left - start));
      setActive(distances.indexOf(Math.min(...distances)));
    }, { passive: true });
  }

  // Vista explosionada: las piezas se separan al entrar en pantalla, sin dejar la sección fija, y cada pieza
  // se puede seleccionar para ver qué revisamos en ella (explorador tomado de la propuesta Codex)
  const xp = document.querySelector('[data-xp]');
  if (xp) {
    const parts = [...xp.querySelectorAll('[data-part]')];
    const detail = xp.querySelector('[data-part-detail]');
    const prompt = detail.textContent;
    detail.hidden = false;
    parts.forEach((btn) => btn.addEventListener('click', () => {
      const on = btn.getAttribute('aria-pressed') !== 'true';
      parts.forEach((b) => b.setAttribute('aria-pressed', String(on && b === btn)));
      xp.querySelectorAll('[data-xp-callout]').forEach((c) => c.classList.toggle('is-selected', on && c.dataset.xpCallout === btn.dataset.part));
      detail.textContent = on ? `${btn.querySelector('strong').textContent}: ${btn.dataset.detail}` : prompt;
    }));

    if (!reduceMotion) {
      const figure = xp.querySelector('.xp__figure');
      let ticking = false;
      const update = () => {
        ticking = false;
        const r = figure.getBoundingClientRect();
        const vh = window.innerHeight;
        const p = Math.min(1, Math.max(0, (vh * 0.95 - r.top) / (vh * 0.55))); // de entrar por abajo a llegar al tercio superior
        xp.style.setProperty('--p', p.toFixed(3));
        xp.classList.toggle('is-exploded', p === 1);
      };
      const request = () => { if (!ticking) { ticking = true; requestAnimationFrame(update); } };
      xp.classList.add('is-enhanced');
      update();
      window.addEventListener('scroll', request, { passive: true });
      window.addEventListener('resize', request);
    }
  }

  // Cobertura: "¿Llegamos a tu comuna?" compara con las comunas de la lista de zonas (data-comuna)
  const checker = document.querySelector('[data-checker]');
  if (checker) {
    const norm = (str) => str.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
    const aliases = { chicureo: 'Colina', 'santiago centro': 'Santiago', stgo: 'Santiago' };
    const comunas = [...document.querySelectorAll('#comunas-rm option')].map((o) => o.value);
    const chips = [...document.querySelectorAll('[data-comuna]')];
    const covered = new Set(chips.map((c) => c.dataset.comuna));
    const input = checker.querySelector('input');
    const out = checker.querySelector('[data-checker-result]');

    checker.addEventListener('submit', (e) => {
      e.preventDefault();
      const q = norm(input.value);
      const comuna = aliases[q] || comunas.find((c) => norm(c) === q);
      const name = q === 'chicureo' ? 'Chicureo' : comuna;
      chips.forEach((c) => c.classList.toggle('is-match', c.dataset.comuna === comuna));

      const msg = document.createElement('span');
      const link = document.createElement('a');
      if (comuna && covered.has(comuna)) {
        out.className = 'checker__result is-ok';
        msg.textContent = `¡Sí! Atendemos en ${name}.`;
        link.textContent = 'Agendar por WhatsApp';
        link.href = waLink(`Hola MantenPlus, estoy en ${name} y quiero agendar un servicio.`);
      } else if (comuna) {
        out.className = 'checker__result is-maybe';
        msg.textContent = `${name} no está en nuestra zona habitual, pero escríbenos y lo evaluamos.`;
        link.textContent = 'Consultar por WhatsApp';
        link.href = waLink(`Hola MantenPlus, ¿atienden en ${name}?`);
      } else {
        out.className = 'checker__result is-error';
        msg.textContent = 'No encontramos esa comuna. Prueba con el nombre completo, por ejemplo «Las Condes».';
      }
      out.replaceChildren(msg, ...(link.href ? [link] : []));
      if (link.href) link.dataset.track = 'cobertura_agendar';
      track('cobertura_consulta', { comuna: comuna || 'desconocida', cubierta: covered.has(comuna) });
    });
  }

  // Formulario de contacto sin servidor: arma el mensaje y abre WhatsApp (la validación es la nativa del navegador)
  const contactForm = document.querySelector('[data-contact-form]');
  if (contactForm) {
    contactForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const f = new FormData(contactForm);
      const val = (k) => String(f.get(k) || '').trim();
      const lines = [
        `Hola MantenPlus, soy ${val('nombre')}.`,
        `Necesito un servicio para mi ${val('equipo').toLowerCase()} en ${val('comuna')}.`,
      ];
      if (val('marca')) lines.push(`Marca y modelo: ${val('marca')}.`);
      if (val('detalle')) lines.push(`Problema: ${val('detalle')}`);
      track('contacto_formulario', { equipo: val('equipo') });
      sendWhatsApp(lines.join('\n'));
    });
  }

  document.querySelectorAll('[data-year]').forEach((el) => { el.textContent = new Date().getFullYear(); });

  // Medición de conversiones (GA4 / Meta Pixel si están cargados)
  function track(name, params = {}) {
    window.gtag?.('event', name, params);
    window.fbq?.('trackCustom', name, params);
  }
  document.addEventListener('click', (e) => {
    const el = e.target.closest('[data-track]');
    if (el && el.tagName === 'A') track(el.dataset.track);
  });
})();
