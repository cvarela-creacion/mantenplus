/* MantenPlus · interacciones del sitio (sin dependencias, ~1 KB) */
(() => {
  const WA_NUMBER = '569XXXXXXXX'; // TODO: reemplazar por el número de WhatsApp Business

  // Header: sombra al hacer scroll + barra CTA móvil al pasar el Hero
  const header = document.querySelector('[data-header]');
  const mobileCta = document.querySelector('[data-mobile-cta]');
  const hero = document.querySelector('.hero__ctas');

  const onScroll = () => header.classList.toggle('is-scrolled', window.scrollY > 8);
  onScroll();
  window.addEventListener('scroll', onScroll, { passive: true });

  if (mobileCta && hero && 'IntersectionObserver' in window) {
    new IntersectionObserver(([entry]) => {
      mobileCta.classList.toggle('is-visible', !entry.isIntersecting);
    }).observe(hero);
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
  };
  toggle.addEventListener('click', () => setMenu(menu.hidden));
  menu.addEventListener('click', (e) => { if (e.target.closest('a')) setMenu(false); });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !menu.hidden) { setMenu(false); toggle.focus(); } });

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
      window.open(`https://wa.me/${WA_NUMBER}?text=${encodeURIComponent(text.value)}`, '_blank', 'noopener');
    });
  }

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
