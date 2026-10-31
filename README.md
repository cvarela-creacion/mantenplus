# MantenPlus · mantenplus.cl

> Expertos en el cuidado y reparación de tus electrodomésticos.

Sitio web de **MantenPlus** (Servicios Integrales Varela), servicio técnico premium de electrodomésticos a domicilio en Santiago, Chile.

## Estructura

```
index.html                 Landing completa: Hero → Servicios → Resultados → Cómo trabajamos → Ingeniería →
                           Charlas de uso → Equipo → Opiniones → Cobertura → Preguntas frecuentes → Contacto + footer
assets/css/styles.css      Sistema visual (tokens, botones, header, hero, responsive)
assets/js/main.js          Menú móvil, WhatsApp, slider, pestañas, carrusel, micro-videos, vista explosionada,
                           comprobador de cobertura, formulario de contacto y medición
assets/img/logo-mark.svg   Isotipo redibujado en vector
assets/img/resultados/     Ilustraciones referenciales del slider antes/después (reemplazar por fotos reales)
assets/brand/              Logotipo original y fotos de referencia del uniforme
robots.txt, sitemap.xml    Indexación en Google para https://mantenplus.cl
.nojekyll                  GitHub Pages publica los archivos tal cual
docs/
  01-arquitectura.md            Mapa del sitio, embudo de conversión, decisiones técnicas
  02-guia-visual.md             Paleta, tipografía, botones, movimiento
  03-tecnicas-interactivas.md   Slider antes/después, carrusel storytelling, micro-videos, vista explosionada
  04-brief-fotografico.md       Dirección de arte para la foto del Hero y la del equipo
  05-publicacion.md             Publicación gratis con GitHub Pages y conexión de mantenplus.cl
```

## Ver en local

Sitio estático, sin dependencias de compilación:

```bash
python3 -m http.server 8080   # luego abre http://localhost:8080
```

## Pendientes antes de publicar

- Número de WhatsApp: reemplazar `569XXXXXXXX` en `index.html` y `assets/js/main.js`.
- Número visible en Contacto: reemplazar `+56 9 XXXX XXXX`.
- Redes sociales y reseñas: reemplazar `[LINK_INSTAGRAM]`, `[LINK_FACEBOOK]` y `[LINK_GOOGLE_RESENAS]`.
- Confirmar comunas de cobertura, reseñas reales y respuestas de Preguntas frecuentes (detalle en `docs/01-arquitectura.md`).
- Foto del Hero: `assets/img/hero-tecnico-puerta.{avif,webp,jpg}` (ver `docs/04-brief-fotografico.md`).
- Fotos del antes/después, del carrusel «Cómo trabajamos» y los micro-videos de servicios (lista exacta de archivos en `docs/03-tecnicas-interactivas.md`).
- Foto institucional del equipo: `assets/img/equipo-mantenplus.{avif,webp,jpg}` (ver `docs/04-brief-fotografico.md`, Foto 2).
