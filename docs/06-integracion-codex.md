# 06 · Integración de la propuesta Codex

Rama: `claude/integracion-aportes-codex`, creada desde `claude/mantenplus-web-redesign-cgys0a` (la que publica GitHub Pages). La propuesta Codex (`codex/mantenplus-v2-a`, PR #2, y la variante B en `codex/mantenplus-v2-b-hero-menu`) se trató como un aporte, no como un reemplazo. Sus ramas quedan intactas como referencia.

## Qué se tomó de Codex

| Aporte | Cómo quedó en la integración |
|---|---|
| **Imagen conceptual de portada** (técnico con polo negro, cordillera de fondo) | En nuestra portada, con `srcset` 600/1200 px, precarga y rótulo visible «Imagen conceptual · fotografía definitiva pendiente». Reemplazar por la foto propia del brief |
| **Tipografías autoalojadas** (WOFF2 variables + licencias OFL) | `assets/fonts`, precargadas; sin Google Fonts |
| **Contraste** (grises y azul más oscuros) | Tokens `--gray-400/500`, `--sky-600/700`; axe pasa de 10–13 infracciones a 0 |
| **Foco visible** de 3 px con contorno | `:focus-visible` global con `--focus` |
| **Navegación de 7 enlaces** (agrega Resultados y Cobertura) | Escritorio y menú móvil |
| **Menú accesible**: página inerte detrás, foco cíclico, cierre al pasar a escritorio | `main.js`, reescrito sin código muerto |
| **Selector equipo → avería** | Integrado en los chips de la portada: al elegir el equipo aparecen sus averías típicas (paso 2, opcional). Se agregó Campana |
| **Diálogo para revisar el mensaje** | «Modo revisión» automático: se usa solo mientras el número de WhatsApp sea provisorio (agrega «Enviar por correo», que ya funciona). Con el número real, WhatsApp abre directo |
| **Carrusel sin avance automático**, pasos numerados y corrección de tablet | Flechas y pasos 1–4 también en escritorio |
| **Explorador de piezas** con explicaciones | Botones con `aria-pressed`, pieza marcada en rojo de marca y texto de lo que se revisa |
| **Medios pendientes en `<template>`** | Sin peticiones a archivos que aún no existen |
| **«Número definitivo pendiente»** en Contacto | En lugar de un número ficticio |
| **Opiniones accesibles por teclado** | `tabindex` y nombre accesible en el carrusel |
| **Pruebas reproducibles** | `tests/sitio.cjs` (40 comprobaciones + axe), adaptadas a la página integrada |

## Qué se conservó de la versión original y por qué

- **Eslogan oficial como titular** (requisito del brief). Codex lo había cambiado por «Reparamos con precisión. Cuidamos tu hogar.».
- **Estética luminosa en todas las secciones.** Codex usaba fondos azul marino en Ingeniería y en el proceso, y la variante B una portada oscura; el brief pide «nada de diseños oscuros».
- **Botones en píldora**, coherentes con los chips.
- **Barra fija inferior en móvil** (zona del pulgar), que ya se oculta en Contacto y footer. Codex la reemplazaba por un botón en el encabezado.
- **Tarjeta «Técnico identificado» y sello «German Engineering»** sobre la foto (en móvil el sello se oculta).
- **Animación del despiece**, ahora sin dejar la sección fija varias pantallas.
- **Variante B no adoptada:** portada oscura y menú escondido tras un botón también en escritorio. El propio Codex recomendaba A.

## Errores encontrados y corregidos

1. **Menú móvil recortado a 56 px** (error de la versión original, heredado por Codex): el `backdrop-filter` del encabezado convertía al menú fijo en hijo del encabezado. El vidrio pasa a una capa `::before`. **También corregido en la página publicada** (commit `70d5625`).
2. **Ícono del menú** que no formaba la «X» (`nth-of-type` contaba el texto oculto). Corregido también en la publicada.
3. **Menú en teléfonos bajos** (iPhone SE): con 7 enlaces el panel no cabía; ahora se desplaza.
4. Codex dejó un CSS comprimido que pisaba los tokens con `!important` y código desactivado (`if (false && …)`); por eso sus aportes se reescribieron dentro de la estructura existente en vez de copiar sus archivos.

## Pruebas

```bash
npm ci        # solo herramientas de prueba; el sitio no las necesita
npm test      # levanta un servidor local y prueba 390, 375, 820, 1440 y 1920 px
```

Si Playwright no encuentra su navegador: `CHROMIUM_PATH=/ruta/a/chromium npm test`. Resultado en la entrega: **40/40**, axe sin infracciones WCAG 2.1 A/AA a 390 y 1440 px, sin errores JS ni peticiones fallidas. No reemplaza una prueba con lector de pantalla ni en dispositivos físicos.

## Publicación

GitHub Pages publica desde `claude/mantenplus-web-redesign-cgys0a` (verificado en el historial de despliegues; `main` no publica). Para publicar la integración aprobada: fusionar `claude/integracion-aportes-codex` en esa rama y verificar el despliegue en *Actions → pages build and deployment*.
