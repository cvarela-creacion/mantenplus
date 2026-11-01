"""Piezas compartidas de cabecera, botón de WhatsApp y diálogo para index.html y galeria.html.
Uso: python3 tools/partes.py  (reescribe los bloques marcados en ambas páginas)."""

WA = 'https://wa.me/569XXXXXXXX?text='
TEL = 'tel:+569XXXXXXXX'  # TODO: número móvil definitivo (el mismo de WhatsApp)
AGENDAR = WA + 'Hola%20MantenPlus%2C%20quiero%20agendar%20un%20servicio.'

NAV = [('servicios', 'Servicios'), ('instalacion', 'Instalación'), ('galeria', 'Galería'),
       ('como-trabajamos', 'Cómo trabajamos'), ('empresas', 'Empresas'), ('equipo', 'Equipo'), ('contacto', 'Contacto')]


def header(base=''):
    """base = '' en index.html, 'index.html' en otras páginas."""
    links = '\n'.join(f'          <li><a href="{base}#{i}">{t}</a></li>' for i, t in NAV)
    return f'''  <header class="site-header" data-header>
    <div class="container site-header__inner">
      <a class="brand" href="./" aria-label="MantenPlus, ir al inicio">
        <svg class="brand__mark" viewBox="0 0 680 380" aria-hidden="true" focusable="false">
          <use href="#logo-mark"/>
        </svg>
        <span class="brand__text">
          <span class="brand__word">MANTEN<span class="brand__plus">PLUS</span></span>
          <span class="brand__tagline">Expertos en el cuidado y reparación de tus electrodomésticos</span>
        </span>
      </a>

      <nav class="main-nav" aria-label="Principal">
        <ul class="main-nav__list">
{links}
        </ul>
      </nav>

      <div class="site-header__actions">
        <a class="btn btn--primary btn--sm" href="{AGENDAR}" data-track="header_agendar">
          Agendar
        </a>
        <button class="menu-toggle" type="button" aria-expanded="false" aria-controls="mobile-menu" data-menu-toggle>
          <span class="visually-hidden">Abrir menú</span>
          <span class="menu-toggle__bar menu-toggle__bar--top"></span>
          <span class="menu-toggle__bar menu-toggle__bar--bottom"></span>
        </button>
      </div>
    </div>

    <!-- Menú móvil (hoja a pantalla completa) -->
    <div class="mobile-menu" id="mobile-menu" hidden data-mobile-menu>
      <nav aria-label="Menú móvil">
        <ul class="mobile-menu__list">
{links}
        </ul>
      </nav>
      <div class="mobile-menu__footer">
        <a class="btn btn--primary btn--block" href="{AGENDAR}" data-track="menu_agendar">Agendar servicio</a>
{quick_contact('menu')}
{social()}
      </div>
    </div>
  </header>'''


def quick_contact(origen):
    """WhatsApp directo, llamada al móvil y correo institucional (sin número fijo)."""
    return f'''        <ul class="quick-contact" role="list" aria-label="Contacto directo">
          <li><a class="quick-contact__item quick-contact__item--wa" href="{AGENDAR}" data-track="{origen}_whatsapp"><svg class="icon" aria-hidden="true"><use href="#i-whatsapp"/></svg>WhatsApp</a></li>
          <li><a class="quick-contact__item" href="{TEL}" data-track="{origen}_llamar"><svg class="icon" aria-hidden="true"><use href="#i-phone"/></svg>Llamar</a></li>
          <li><a class="quick-contact__item" href="mailto:contacto@mantenplus.cl" data-track="{origen}_correo"><svg class="icon" aria-hidden="true"><use href="#i-mail"/></svg>Correo</a></li>
        </ul>'''


def social(extra=''):
    """Íconos de redes con sus colores de marca (Facebook azul clásico, degradado de Instagram)."""
    return f'''        <div class="social{extra}">
          <a class="social__link social__link--ig" href="[LINK_INSTAGRAM]" aria-label="Instagram de MantenPlus"><svg class="icon" aria-hidden="true"><use href="#i-instagram"/></svg></a>
          <a class="social__link social__link--fb" href="[LINK_FACEBOOK]" aria-label="Facebook de MantenPlus"><svg class="icon" aria-hidden="true"><use href="#i-facebook"/></svg></a>
        </div>'''


def fab():
    return f'''  <!-- Botón flotante principal de WhatsApp (verde original de la marca) -->
  <a class="wa-fab" href="{AGENDAR}" aria-label="Escríbenos por WhatsApp" data-wa-fab data-track="fab_whatsapp">
    <span class="wa-fab__label" aria-hidden="true">Escríbenos</span>
    <span class="wa-fab__circle" aria-hidden="true"><svg class="wa-fab__icon"><use href="#i-whatsapp"/></svg></span>
  </a>'''


DIALOG = '''  <!-- Modo revisión de WhatsApp (idea de la propuesta Codex): solo se usa mientras el número de main.js sea provisorio -->
  <dialog class="msg-dialog" aria-labelledby="msg-title" data-message-dialog>
    <div class="msg-dialog__inner">
      <button class="msg-dialog__close" type="button" aria-label="Cerrar" data-close-dialog><svg class="icon" aria-hidden="true"><use href="#i-plus"/></svg></button>
      <p class="kicker">Tu consulta</p>
      <h2 class="msg-dialog__title" id="msg-title">Mensaje listo</h2>
      <p class="msg-dialog__lead" data-dialog-lead>Todavía no se envía por WhatsApp: el número definitivo está pendiente. Puedes revisarlo, copiarlo o mandarlo por correo.</p>
      <label class="msg-dialog__label" for="msg-text">Tu mensaje</label>
      <textarea id="msg-text" rows="5" data-message-text></textarea>
      <div class="msg-dialog__actions">
        <button class="btn btn--primary" type="button" data-copy-message>Copiar mensaje</button>
        <a class="btn btn--soft" href="mailto:contacto@mantenplus.cl" data-mail-message data-track="dialogo_correo">Enviar por correo</a>
      </div>
      <p class="msg-dialog__status" role="status" data-copy-status></p>
    </div>
  </dialog>'''


if __name__ == '__main__':
    import re, pathlib
    root = pathlib.Path(__file__).resolve().parent.parent
    for name, base in (('index.html', ''), ('galeria.html', 'index.html')):
        p = root / name
        if not p.exists():
            continue
        s = p.read_text()
        s = re.sub(r'  <header class="site-header" data-header>.*?</header>', lambda m: header(base), s, count=1, flags=re.S)
        s = re.sub(r'  <!-- Botón flotante principal de WhatsApp.*?</a>', lambda m: fab(), s, count=1, flags=re.S)
        s = re.sub(r'  <!-- Modo revisión de WhatsApp.*?</dialog>', lambda m: DIALOG, s, count=1, flags=re.S)
        p.write_text(s)
        print('actualizado', name)
