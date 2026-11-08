# MantenPlus · mantenplus.cl

> Expertos en el cuidado y reparación de tus electrodomésticos.

Sitio web de **MantenPlus** (Servicios Integrales Varela), servicio técnico premium de electrodomésticos a domicilio en Santiago, Chile.

## Estructura

```
index.html                 Landing: Hero → Servicios → Instalación y panelado → Antes/después → Galería →
                           Cómo trabajamos → Charlas de uso → Equipo → Empresas → Opiniones → Cobertura →
                           Preguntas frecuentes → Contacto + footer
galeria.html               Galería completa por categoría (instalaciones, reparaciones, mantenimiento)
assets/css/styles.css      Sistema visual (tokens, botones, header, hero, responsive)
assets/js/main.js          Menú móvil, WhatsApp, slider, pestañas, carrusel, micro-videos, filtro de galería,
                           comprobador de cobertura, formulario de contacto y medición
assets/img/logo-mark.svg   Isotipo redibujado en vector
assets/img/                Fotos en WebP: portada, instalación, equipo, resultados/, galeria/, proceso/, herramientas/
assets/fonts/              Inter y Plus Jakarta Sans autoalojadas (licencia SIL OFL)
assets/brand/              Logotipo original y fotos de referencia del uniforme
robots.txt, sitemap.xml    Indexación en Google para https://mantenplus.cl
.nojekyll                  GitHub Pages publica los archivos tal cual
tests/sitio.cjs            Pruebas en Chromium + accesibilidad (npm test)
tools/partes.py            Cabecera, botones flotantes (llamada y WhatsApp) y diálogo compartidos por las dos páginas
docs/
  01-arquitectura.md            Mapa del sitio, embudo de conversión, decisiones técnicas
  02-guia-visual.md             Paleta, tipografía, botones, movimiento
  03-tecnicas-interactivas.md   Slider antes/después, carrusel storytelling, micro-videos
  04-brief-fotografico.md       Dirección de arte para la foto del Hero y la del equipo
  05-publicacion.md             Conexión de mantenplus.cl (Cloudflare + NIC Chile), GitHub Pages y correo Zoho
  06-integracion-codex.md       Qué se tomó de la propuesta Codex, qué se conservó y por qué
  07-directrices-marca.md       Directrices definitivas del 1 nov 2026 y estado de las imágenes
```

## Ver en local

Sitio estático, sin dependencias de compilación:

```bash
python3 -m http.server 8080   # luego abre http://localhost:8080
```

Pruebas automáticas (opcionales): `npm ci && npm test`.

## Pendientes antes de publicar

- Número de WhatsApp y móvil: reemplazar `569XXXXXXXX` en `index.html`, `galeria.html`, `assets/js/main.js` y `tools/partes.py`. Mientras sea provisorio, los botones de WhatsApp y de llamada abren un diálogo para revisar y copiar el mensaje; con el número real funcionan directo.
- Número visible en Contacto: reemplazar «Número definitivo pendiente».
- Redes sociales y reseñas: reemplazar `[LINK_INSTAGRAM]`, `[LINK_FACEBOOK]` y `[LINK_GOOGLE_RESENAS]`.
- Confirmar comunas de cobertura, reseñas reales y respuestas de Preguntas frecuentes (detalle en `docs/01-arquitectura.md`).
- Las fotos con rótulo «Imagen referencial» (logos ilegibles) conviene reemplazarlas por fotos propias con el uniforme oficial (ver `docs/07-directrices-marca.md`).
- Micro-videos de servicios: esperan en `<template data-pending-media>`; al subir cada archivo, sacar su `<video>` del template.
