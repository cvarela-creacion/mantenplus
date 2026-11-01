# 07 · Directrices definitivas de marca (1 nov 2026)

Cambios aplicados en `claude/integracion-aportes-codex` según las directrices de MantenPlus.

| # | Directriz | Cómo quedó |
|---|---|---|
| 1 | Logo con eslogan | El eslogan oficial va bajo «MANTENPLUS» en la cabecera, en letra fina separada por una línea (`.brand__tagline`) |
| 2 | Galería real, sin carrusel | Sección `#galeria` con cuadrícula de 6 fotos (instalaciones, reparaciones, mantenimiento) y botón «Ver galería completa», que abre `galeria.html` (18 espacios en tres categorías, con filtro). Las tarjetas muestran «Foto próximamente» hasta cargar las fotos |
| 3 | Antes y después con fotos | Comparador con las fotos entregadas de lavadora, encimera y campana (WebP 800/1408 px). En la foto «después» de la lavadora se quitó una etiqueta ilegible que simulaba una certificación |
| 4 | Sin la lavadora vectorial | Sección `#ingenieria`, explorador de piezas, sus estilos y su JavaScript eliminados |
| 5 | Instalación y panelado | Sección `#instalacion` destacada justo después de Servicios, mención en la portada, en el menú, en el footer y en Preguntas frecuentes |
| 6 | Empresas y edificios (B2B) | Sección `#empresas` para constructoras, inmobiliarias y administraciones de condominios y edificios, con «Solicitar propuesta» por correo y WhatsApp |
| 7 | Técnico recibido por el cliente | Foto de portada; se retiraron las menciones a cubrecalzado (tarjeta de la portada, paso 1 del proceso y documentos) |
| 8 | Contacto y redes | Botón flotante en el verde original de WhatsApp (#25D366, ícono blanco; la etiqueta «Escríbenos» va en una pastilla blanca porque el texto blanco sobre ese verde no alcanza el contraste mínimo). En el menú móvil y en Contacto: WhatsApp directo, llamada al móvil y correo institucional, sin número fijo. Redes con Facebook azul (#1877F2) y degradado de Instagram en Contacto, menú y footer |
| 8b | Equipo y herramientas | Foto del equipo junto a los cuatro pilares, más un bloque «Herramientas y equipos de diagnóstico» con tres espacios para fotos |

## Sobre las imágenes entregadas

Las fotos entregadas tienen rasgos de imagen generada (logotipos y textos ilegibles en polos, maletín y lavadora; productos de marcas de terceros). Por eso se publican con el rótulo **«Imagen referencial»**, y el comparador dice «Imágenes referenciales del tipo de trabajo que realizamos». Presentarlas como trabajos documentados sería engañoso para el cliente (Ley 19.496) y contradice la promesa de transparencia. Cuando existan fotos propias tomadas en terreno, basta con reemplazar los archivos con los mismos nombres y quitar esos rótulos.

## Archivos de imagen

| Uso | Archivos |
|---|---|
| Portada | `assets/img/portada-tecnico-cliente-{800,1408}.webp` |
| Antes/después | `assets/img/resultados/{lavadora,encimera,campana}-{antes,despues}-{800,1408}.webp` |
| Equipo | `assets/img/equipo-mantenplus-{700,1109}.webp` |
| Proceso, paso 3 | `assets/img/proceso/paso-3-ejecucion-{600,1200}.webp` (imagen conceptual de Codex) |
| Galería (pendiente) | `assets/img/galeria/*.webp` (1200×900): reemplazar en cada tarjeta el ícono por la `<img>` comentada |
| Herramientas (pendiente) | `assets/img/equipo/*.webp` (1200×900) |

## Piezas compartidas

`tools/partes.py` genera la cabecera, el botón flotante y el diálogo de ambas páginas. Después de editarlo, ejecutar `python3 tools/partes.py` para actualizar `index.html` y `galeria.html`.
