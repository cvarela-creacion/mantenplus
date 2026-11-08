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

## Actualización del 2 nov 2026

| # | Pedido | Cómo quedó |
|---|---|---|
| 1 | Quitar «Proyectos para empresas» antes de Resultados | Eliminado; Instalación queda solo con «Cotizar instalación» |
| 2 | Foto nueva en Instalación y panelado | Dos técnicos: uno termina el panelado de un refrigerador y otro da la charla de uso junto al lavavajillas panelado |
| 3 | Más casos en Resultados | Siete pestañas: Lavadora, Secadora, Lavavajillas, Horno, Microondas, Encimera y Campana. Los pares nuevos se alinearon por puntos comunes (muebles, cubierta, piso) para que calcen al deslizar; cada caso conserva su formato |
| 4 | Galería con fotos | Portada: 3 instalaciones, 1 reparación y 2 mantenciones. `galeria.html`: 8 fotos por categoría (la de la campana y la de la secadora desarmada solo ahí) |
| 5 | Fotos principales | Portada: técnico revisando la lavadora con la cordillera de fondo. «Cómo trabajamos», paso 1: técnico recibido en la puerta. Los pasos 2 a 4 reutilizan con otro encuadre la placa de horno, la campana de isla y la charla de uso de Instalación |
| 6 | Foto nueva del equipo | Cuatro técnicos con el mismo uniforme y credencial visible, más dos integrantes de atención al cliente (4:3) |
| 7 | Herramientas | Dos fotos en dos columnas: instrumentos de medición, y herramientas de precisión con detector de fugas de gas |

Segunda entrega del 2 nov: foto nueva en Instalación y panelado, foto nueva en el paso 4 «Charla de uso» (técnico explicando a la dueña de casa el uso de sus cafeteras empotradas), foto nueva en el paso 2 «Diagnóstico transparente» (técnico leyendo el código E15 de un lavavajillas en su tablet; la placa de horno queda solo en la galería) y foto nueva del equipo.

Rótulo «Imagen referencial» en las fotos con logos o textos ilegibles: portada, Instalación y panelado, pasos 1, 2 y 4 del proceso, equipo, placa de horno y fuelle de lavadora. En el carrusel del proceso el rótulo va arriba para no tapar detalles de la foto. El comparador mantiene la nota general «Imágenes referenciales del tipo de trabajo que realizamos».

Observaciones pendientes para el cliente:
- En varias fotos el polo lleva un logo «M+» con «Servicio Técnico de Electrodomésticos», distinto del isotipo oficial (casa con refrigerador y lavadora).
- El medidor de consumo de la foto de instrumentos marca 120 V y tiene un enchufe estadounidense; en Chile la red es de 220 V con enchufes tipo L o C.

## Portada, SEO y contacto flotante (2 nov 2026)

| Elemento | Antes | Ahora |
|---|---|---|
| Franja sobre el título | Servicio técnico a domicilio · Santiago | Reparación · Mantención · Instalación |
| H1 | Expertos en el cuidado y reparación de tus electrodomésticos | Servicio técnico de electrodomésticos en Santiago |
| Descripción | Reparación, mantención e instalación… | A domicilio y con diagnóstico transparente: te mostramos la falla y el presupuesto antes de reparar. Especialistas en equipos de alta gama, incluidos encastrables y panelables. Cuidamos tus equipos y tu hogar. |
| Eslogan | Bajo el logo y como H1 | Solo bajo el logo (cabecera y footer) y en la imagen para compartir |

La descripción no repite «reparación, mantención e instalación», que ya están en la franja superior.

SEO revisado: el `<title>` («Servicio técnico de electrodomésticos a domicilio en Santiago») ya era coherente y no cambió. Se actualizaron la metadescripción y el título y la descripción para redes (Open Graph), y se agregó «Instalación y panelado de electrodomésticos encastrables» a `knowsAbout` en los datos estructurados, porque es un servicio que la página ofrece. No cambiaron URLs, dominio ni datos comerciales.

Botones flotantes: «Llámanos» (círculo azul con el ícono de audífonos, enlace `tel:`) sobre «Escríbenos» (círculo verde de WhatsApp), en una pila fija con aro blanco. En el celular se muestran solo los círculos para no tapar el contenido; las etiquetas quedan como nombre accesible. Mientras el número sea provisorio, ambos abren el diálogo para copiar el mensaje.

Fotos reemplazadas: portada (el técnico con el parche «German Engineering» en la manga, 4:3), paso 1 «Llegada pulcra» (otro calzado) y equipo (cambia la integrante de la izquierda).

## Archivos de imagen

| Uso | Archivos |
|---|---|
| Portada | `assets/img/portada-tecnico-lavadora-{720,1440}.webp` |
| Instalación y panelado | `assets/img/instalacion-panelado-{800,1365}.webp` |
| Antes/después | `assets/img/resultados/{lavadora,secadora,lavavajillas,horno,microondas,encimera,campana}-{antes,despues}-*.webp` |
| Galería | `assets/img/galeria/*-{640,1280}.webp` |
| Proceso | `assets/img/proceso/paso-1-llegada-{800,1440}.webp`, `paso-2-diagnostico-{480,688}.webp`, `paso-4-charla-{800,1440}.webp`; el paso 3 usa la campana de isla de la galería |
| Equipo | `assets/img/equipo-mantenplus-{720,1440}.webp` |
| Herramientas | `assets/img/herramientas/{instrumentos-medicion,herramientas-precision}-{640,1280}.webp` |

## Piezas compartidas

`tools/partes.py` genera la cabecera, el botón flotante y el diálogo de ambas páginas. Después de editarlo, ejecutar `python3 tools/partes.py` para actualizar `index.html` y `galeria.html`.
