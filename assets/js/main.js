/* MantenPlus · interacciones del sitio (sin dependencias) */
(() => {
  const WA_NUMBER = '569XXXXXXXX'; // TODO: reemplazar por el número de WhatsApp Business
  const waLink = (text) => `https://wa.me/${WA_NUMBER}?text=${encodeURIComponent(text)}`;

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
  const setMenu = (open) => {
    toggle.setAttribute('aria-expanded', String(open));
    toggle.querySelector('.visually-hidden').textContent = open ? 'Cerrar menú' : 'Abrir menú';
    menu.hidden = !open;
    document.body.style.overflow = open ? 'hidden' : '';
    document.querySelector('main').inert = open;
    document.querySelector('.site-footer').inert = open;
    if (open) menu.querySelector('a').focus();
    else toggle.focus();
  };
  toggle.addEventListener('click', () => setMenu(menu.hidden));
  menu.addEventListener('click', (e) => { if (e.target.closest('a')) setMenu(false); });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !menu.hidden) { setMenu(false); toggle.focus(); } });

  document.addEventListener('keydown', e => {
    if (menu.hidden || e.key !== 'Tab') return;
    const all = [toggle, ...menu.querySelectorAll('a,button')];
    const i = all.indexOf(document.activeElement);
    e.preventDefault(); all[(i + (e.shiftKey ? -1 : 1) + all.length) % all.length].focus();
  });
  matchMedia('(min-width: 1151px)').addEventListener('change', () => { if (!menu.hidden) setMenu(false); });
  // Agendamiento rápido: el equipo elegido viaja en el mensaje de WhatsApp
  const form = document.querySelector('[data-quick-book]');
  if (form) {
    const text = form.querySelector('[data-wa-text]');
    const sync = () => {
      const equipo = form.querySelector('input[name="equipo"]:checked')?.value || 'electrodoméstico';
      text.value = `Hola MantenPlus, quiero agendar un servicio para mi ${equipo}.`;
    };
    form.addEventListener('change', sync);
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      sync();
      track('hero_agendar', { equipo: form.querySelector('input[name="equipo"]:checked')?.value });
      window.prepareMessage(text.value);
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

  // Storytelling "Cómo trabajamos": en escritorio avanza solo (barra de progreso); en móvil es un carrusel deslizable
  const story = document.querySelector('[data-story]');
  if (story) {
    const steps = [...story.querySelectorAll('[data-step]')];
    const dots = [...story.querySelectorAll('[data-dot]')];
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
      const idx = (i + steps.length) % steps.length;
      if (desktop.matches) return setActive(idx);
      setActive(idx);
      steps[idx].scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'nearest', inline: 'start' });
    };

    steps.forEach((s, n) => s.querySelector('[data-step-btn]').addEventListener('click', () => desktop.matches && setActive(n)));
    dots.forEach((d, n) => d.addEventListener('click', () => goTo(n)));
    story.querySelector('[data-story-prev]').addEventListener('click', () => goTo(current - 1));
    story.querySelector('[data-story-next]').addEventListener('click', () => goTo(current + 1));

    // Escritorio: al completarse la barra de progreso pasa al siguiente paso
    story.addEventListener('animationend', (e) => {
      if (false && e.animationName === 'story-progress' && desktop.matches && !reduceMotion) setActive(current + 1);
    });
    const pause = (on) => story.classList.toggle('is-paused', on);
    story.addEventListener('mouseenter', () => pause(true));
    story.addEventListener('mouseleave', () => pause(false));
    story.addEventListener('focusin', () => pause(true));
    story.addEventListener('focusout', () => pause(false));

    if ('IntersectionObserver' in window) {
      // Fuera de pantalla no avanza
      new IntersectionObserver(([entry]) => story.classList.toggle('is-offscreen', !entry.isIntersecting)).observe(story);
      // Móvil: los puntos siguen a la tarjeta visible
      const rail = story.querySelector('[data-story-track]');
      rail.addEventListener('scroll', () => {
        if (desktop.matches) return;
        const left = rail.getBoundingClientRect().left;
        const distances = steps.map(step => Math.abs(step.getBoundingClientRect().left - left));
        setActive(distances.indexOf(Math.min(...distances)));
      }, { passive: true });
    }
  }

  // Vista explosionada: el scroll separa las piezas (--p: 0 ensamblado → 1 explosionado) y luego enciende cada etiqueta
  const xp = document.querySelector('[data-xp]');
  if (xp && !reduceMotion && !document.querySelector('[data-part]')) {
    const figure = xp.querySelector('.xp__figure');
    const items = [...xp.querySelectorAll('[data-xp-item]')];
    const callouts = items.map((_, i) => xp.querySelector(`[data-xp-callout="${i + 1}"]`)); // el SVG las tiene en orden de dibujo
    const sticky = matchMedia('(min-width: 861px) and (min-height: 620px)');
    let ticking = false;

    const update = () => {
      ticking = false;
      const vh = window.innerHeight;
      let p;
      if (sticky.matches) {
        const r = xp.getBoundingClientRect();
        p = -r.top / (r.height - vh); // recorrido de la escena fija
      } else {
        const r = figure.getBoundingClientRect();
        p = (vh * 0.9 - r.top) / (vh * 0.6); // de entrar por abajo a llegar al tercio superior
      }
      p = Math.min(1, Math.max(0, p));
      xp.style.setProperty('--p', Math.min(1, p / 0.6).toFixed(3)); // las piezas terminan de separarse al 60 %
      items.forEach((li, i) => {
        const on = p >= 0.6 + (0.38 * i) / items.length; // luego se encienden las etiquetas, una a una
        li.classList.toggle('is-on', on);
        callouts[i]?.classList.toggle('is-on', on);
      });
    };
    const request = () => { if (!ticking) { ticking = true; requestAnimationFrame(update); } };

    xp.classList.add('is-enhanced');
    update();
    window.addEventListener('scroll', request, { passive: true });
    window.addEventListener('resize', request);
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
      window.prepareMessage(lines.join('\n'));
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
