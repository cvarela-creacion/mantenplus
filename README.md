# MantenPlus · mantenplus.cl

> Expertos en el cuidado y reparación de tus electrodomésticos.

Sitio web de **MantenPlus** (Servicios Integrales Varela), servicio técnico premium de electrodomésticos a domicilio en Santiago, Chile.

## Estructura

```
index.html                 Header + Hero (fase 1)
assets/css/styles.css      Sistema visual (tokens, botones, header, hero, responsive)
assets/js/main.js          Menú móvil, header al hacer scroll, agendamiento rápido por WhatsApp, medición
assets/img/logo-mark.svg   Isotipo redibujado en vector
assets/brand/              Logotipo original y fotos de referencia del uniforme
docs/
  01-arquitectura.md            Mapa del sitio, embudo de conversión, decisiones técnicas
  02-guia-visual.md             Paleta, tipografía, botones, movimiento
  03-tecnicas-interactivas.md   Slider antes/después, carrusel storytelling, micro-videos, vista explosionada
  04-brief-fotografico.md       Dirección de arte para la foto del Hero y la del equipo
```

## Ver en local

Sitio estático, sin dependencias de compilación:

```bash
python3 -m http.server 8080   # luego abre http://localhost:8080
```

## Pendientes antes de publicar

- Número de WhatsApp: reemplazar `569XXXXXXXX` en `index.html` y `assets/js/main.js`.
- Redes sociales: reemplazar `[LINK_INSTAGRAM]` y `[LINK_FACEBOOK]`.
- Foto del Hero: `assets/img/hero-tecnico-puerta.{avif,webp,jpg}` (ver `docs/04-brief-fotografico.md`).
