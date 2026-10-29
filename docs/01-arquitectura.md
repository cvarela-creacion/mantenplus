# 01 · Arquitectura y estrategia de conversión — mantenplus.cl

## Concepto rector: «La visita técnica más pulcra de tu vida»

El cliente medio-alto de Santiago no compra «una reparación». Compra **tranquilidad**: que alguien de confianza entre a su casa, cuide su cocina de diseño y deje su Bosch o su Miele funcionando como nuevo. Toda la web está pensada para responder, en este orden, a sus tres miedos:

1. **«¿Puedo dejar entrar a esta persona a mi casa?»** → uniforme, credencial, cubrecalzado, equipo real.
2. **«¿Me van a cobrar de más?»** → diagnóstico transparente *antes* de reparar y garantía por escrito.
3. **«¿Saben de equipos de alta gama?»** → despiece técnico, especialización en ingeniería alemana.

Cada sección responde una objeción y termina invitando a **Agendar servicio** (WhatsApp).

## Mapa del sitio (fase 1: landing de una página + páginas SEO)

| # | Sección (ancla) | Objetivo | Recurso clave |
|---|---|---|---|
| 0 | Header fijo | Navegar sin perder la CTA | Header translúcido + botón «Agendar» |
| 1 | **Hero** | Captar y convertir en 5 segundos | Eslogan oficial, foto en la puerta, selector de equipo → WhatsApp |
| 2 | Franja de marcas | Autoridad inmediata | Bosch, Siemens, Miele, Neff, Gaggenau, AEG (en texto) |
| 3 | `#servicios` | «Reparan lo que tengo» | Tarjetas por equipo con **micro-video en bucle** |
| 4 | `#resultados` | Prueba visual | **Slider antes/después** interactivo |
| 5 | `#como-trabajamos` | Quitar el miedo a la visita | **Carrusel storytelling** de 4 pasos |
| 6 | `#ingenieria` | Rigor técnico, alta gama | **Vista explosionada** animada con el scroll |
| 7 | `#charlas-de-uso` | **Diferencial único** | Bloque editorial + 3 consejos de muestra + «incluida en cada visita» |
| 8 | `#equipo` | Solidez y confianza | Foto institucional: 4 técnicos + 2 administrativas (sin fundador) |
| 9 | `#opiniones` | Prueba social | Reseñas reales de Google (widget o texto curado) |
| 10 | `#cobertura` | «¿Llegan a mi comuna?» | Chips de comunas: Las Condes, Vitacura, Lo Barnechea, Providencia, Ñuñoa, La Reina… |
| 11 | `#faq` | Resolver objeciones finales | Acordeón: costo de visita, garantía, repuestos, plazos |
| 12 | `#contacto` | Cierre | WhatsApp, contacto@mantenplus.cl, redes `[LINK_INSTAGRAM]` |
| — | Barra CTA móvil | CTA siempre a mano del pulgar | Aparece al pasar el Hero |

**Fase 2 (SEO local):** páginas `/reparacion-lavadoras`, `/reparacion-refrigeradores`, `/reparacion-encimeras`, `/servicio-tecnico-bosch`, `/servicio-tecnico-miele`… y por comuna (`/servicio-tecnico-las-condes`). Es lo que de verdad posiciona en Google para búsquedas como «técnico lavadora Bosch Vitacura».

## Embudo de conversión

```
Visita → Hero (selecciona equipo) → WhatsApp con mensaje pre-llenado
                                     «Hola MantenPlus, quiero agendar un servicio para mi lavadora.»
```

- **Una sola acción principal** en todo el sitio: *Agendar servicio*. El correo es secundario.
- El **selector de equipo** del Hero es un micro-compromiso: el usuario ya «empezó» a agendar, y el mensaje llega pre-calificado al equipo de atención.
- Eventos medibles ya implementados (`data-track`): `header_agendar`, `hero_agendar` (con el equipo elegido), `menu_agendar`, `sticky_agendar`. Se envían a GA4 (`gtag`) y Meta Pixel (`fbq`) si están instalados.

## Decisiones técnicas

- **HTML + CSS + JS sin frameworks** en esta fase: 0 dependencias, ~1 KB de JS, carga instantánea. Cuando el sitio crezca (páginas SEO, blog de Charlas de uso) la migración natural es **Astro** reutilizando este mismo CSS.
- **Metas de Core Web Vitals:** LCP < 2,0 s en 4G, CLS < 0,05, INP < 150 ms.
  - Foto del Hero en AVIF/WebP con `fetchpriority="high"` y `preload` (dejado comentado hasta tener la foto).
  - Todas las imágenes con `width`/`height` → sin saltos de diseño.
  - Videos en bucle: `muted playsinline loop preload="none"` y carga diferida con `IntersectionObserver`.
- **Accesibilidad:** contraste AA, foco visible, «saltar al contenido», menú con `aria-expanded`, `prefers-reduced-motion` respetado.
- **SEO:** `lang="es-CL"`, metadatos Open Graph, datos estructurados `HomeAndConstructionBusiness`.
- **iOS / Android:** `viewport-fit=cover` + `env(safe-area-inset-bottom)` para el notch y la barra de gestos; objetivos táctiles ≥ 44 px.

## Nota legal sobre marcas

Bosch, Siemens, Miele, Neff, Gaggenau y AEG son marcas de terceros. Se muestran **en texto** (no con sus logotipos) y con la fórmula «Especialistas en», que describe experiencia sin dar a entender que MantenPlus es servicio técnico **oficial/autorizado**. Si en algún momento obtienen una certificación oficial, se puede cambiar el texto y usar los logos con permiso.

## Datos pendientes de reemplazar

| Marcador | Dónde |
|---|---|
| `569XXXXXXXX` | `index.html` (todos los enlaces `wa.me`) y `assets/js/main.js` (`WA_NUMBER`) |
| `+56 9 XXXX XXXX` | `index.html`, tarjeta de WhatsApp en Contacto (número visible) |
| `[LINK_INSTAGRAM]`, `[LINK_FACEBOOK]` | `index.html` (menú móvil, Contacto y footer) |
| `[LINK_GOOGLE_RESENAS]` | `index.html`, botones de Opiniones (ficha de Google Business) |
| `assets/img/hero-tecnico-puerta.{avif,webp,jpg}` | Foto del Hero (ver `04-brief-fotografico.md`) |
| `assets/img/og-mantenplus.jpg` | Imagen 1200×630 para compartir en redes/WhatsApp |

## Contenido a validar con el equipo antes de publicar

El sitio no inventa cifras, plazos ni reseñas. Aun así, estos textos describen la forma de trabajar y deben confirmarse:

| Qué | Dónde | Por qué |
|---|---|---|
| **Comunas de cobertura** | `#cobertura` (atributos `data-comuna`) | Lista propuesta (sector oriente, centro/sur oriente, Huechuraba y Chicureo). El comprobador «¿Llegamos a tu comuna?» lee esta lista: basta con agregar o quitar `<li data-comuna="…">`. |
| **Reseñas** | `#opiniones` | Hoy son espacios reservados. Pegar **solo reseñas reales** de Google (formato en el comentario del HTML). Si al publicar aún no hay, ocultar la sección con `hidden`. |
| Respuestas de **Preguntas frecuentes** | `#faq` | Valor de la visita informado al agendar, presupuesto antes de reparar, garantía por escrito, explicación del repuesto antes de usarlo, mantenciones preventivas. |
| Promesas del servicio | Hero, Cómo trabajamos, Equipo | Cubrecalzado, credencial, aviso cuando el técnico va en camino, charla de uso incluida. |
| Consejos técnicos | `#charlas-de-uso` | Son recomendaciones generales correctas; revisar que coincidan con lo que enseñan los técnicos. |

**Pregunta sugerida para agregar cuando se confirme:** «¿Son servicio técnico oficial de estas marcas?». Responder solo con lo que sea cierto (independiente o certificado).

## Conversión implementada en la fase final

- **Comprobador de cobertura:** acepta nombres sin tildes («nunoa» → Ñuñoa) y el alias «Chicureo». Si la comuna está cubierta, ofrece «Agendar por WhatsApp» con la comuna ya escrita; si no, «Consultar por WhatsApp». Registra el evento `cobertura_consulta`.
- **Formulario de contacto sin servidor:** valida con el navegador y abre WhatsApp con un mensaje ordenado (nombre, equipo, comuna, marca/modelo y problema). No guarda datos. Evento `contacto_formulario`.
- **Barra fija móvil:** se oculta mientras se ve el Hero, la sección Contacto o el footer, para no duplicar botones.
