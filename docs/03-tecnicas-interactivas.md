# 03 · Técnicas visuales de alta conversión — propuesta de implementación

Las cuatro técnicas se implementan sin librerías pesadas (JS nativo + CSS), con carga diferida y respetando `prefers-reduced-motion`.

---

## 1. Slider «Antes y Después» (Split Slider) — `#resultados`

**Objetivo:** que el usuario *toque* la diferencia entre un equipo sucio/desgastado y el resultado MantenPlus. La interacción física genera más recuerdo que una foto estática.

**UX**
- Tarjeta grande con 3 casos en pestañas: *Lavadora (goma y cajón de detergente)*, *Encimera vitrocerámica*, *Filtro de campana*.
- Tirador circular blanco con flechas ‹ ›, etiquetas «Antes» / «Después» en píldoras.
- En móvil: arrastre con el dedo; en escritorio también con teclado (← →).
- Pista inicial: el tirador se desliza solo del 50 % al 35 % y vuelve una vez, para invitar a tocar.

**Implementación** (accesible gracias a un `input range` real)

```html
<div class="ba" style="--pos:50%">
  <img src="antes.webp" alt="Goma de lavadora con moho antes del servicio" width="1200" height="800" loading="lazy">
  <img class="ba__after" src="despues.webp" alt="Goma de lavadora limpia después del servicio" width="1200" height="800" loading="lazy">
  <input class="ba__range" type="range" min="0" max="100" value="50" aria-label="Comparar antes y después">
  <span class="ba__handle" aria-hidden="true"></span>
</div>
```
```css
.ba { position: relative; overflow: hidden; border-radius: var(--radius-lg); }
.ba img { width: 100%; }
.ba__after { position: absolute; inset: 0; clip-path: inset(0 0 0 var(--pos)); }
.ba__range { position: absolute; inset: 0; width: 100%; opacity: 0; cursor: ew-resize; }
.ba__handle { position: absolute; top: 0; bottom: 0; left: var(--pos); width: 2px; background: #fff; }
```
```js
document.querySelectorAll('.ba').forEach(el => el.querySelector('.ba__range')
  .addEventListener('input', e => el.style.setProperty('--pos', e.target.value + '%')));
```

**Producción fotográfica:** mismo trípode, mismo encuadre, misma luz antes y después (si no, el efecto se rompe). Solo fotos reales de clientes y con su autorización.

---

## 2. Storytelling en carrusel (paso a paso) — `#como-trabajamos`

**Objetivo:** que el cliente «viva» la visita antes de agendar y desaparezca la incertidumbre.

| Paso | Título | Texto | Imagen |
|---|---|---|---|
| 01 | Llegada pulcra | Puntuales, uniformados, con credencial y cubrecalzado. Protegemos el piso antes de empezar. | Técnico poniéndose cubrecalzado en la entrada |
| 02 | Diagnóstico transparente | Te mostramos la falla y el presupuesto **antes** de tocar nada. Tú decides. | Técnico mostrando una tablet/pieza al cliente |
| 03 | Ejecución impecable | Repuestos de calidad, herramientas ordenadas sobre un paño. Dejamos todo más limpio que como lo encontramos. | Manos con guantes, herramientas alineadas |
| 04 | Charla de uso | Te enseñamos a cuidar tu equipo para que dure años. Garantía por escrito. | Técnico explicando el panel al cliente |

**UX**
- Escritorio: lista de pasos a la izquierda (con barra de progreso) + imagen grande a la derecha que cambia con *crossfade*. Avance automático cada 6 s, pausa al pasar el mouse.
- Móvil: carrusel horizontal nativo con `scroll-snap-type: x mandatory` (fluido en iOS y Android, sin librerías), indicadores de puntos y tarjetas al 85 % del ancho para insinuar que hay más.
- Accesibilidad: `role="region" aria-roledescription="carrusel"`, botones anterior/siguiente, nunca avanzar solo si el usuario prefiere menos movimiento.

---

## 3. Micro-video en bucle (Loop / Cinemagraph) — tarjetas de `#servicios`

**Objetivo:** transmitir **precisión** en 3 segundos: el anillo azul de una encimera de inducción encendiéndose, el tambor de una lavadora girando perfecto, el agua cayendo en un lavavajillas.

**Implementación**
```html
<video class="loop" muted playsinline loop preload="none" poster="encimera-poster.webp"
       width="640" height="800" aria-hidden="true">
  <source src="encimera.webm" type="video/webm">
  <source src="encimera.mp4" type="video/mp4">
</video>
```
```js
const io = new IntersectionObserver(entries => entries.forEach(({ target: v, isIntersecting }) => {
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  isIntersecting ? v.play() : v.pause();
}), { threshold: .4 });
document.querySelectorAll('video.loop').forEach(v => io.observe(v));
```

**Especificación de los videos:** 3–5 s, bucle perfecto (primer y último cuadro iguales), sin audio, 720 p, **< 600 KB** (H.264 + WebM/VP9), macro con fondo claro. En escritorio el video arranca al pasar el mouse sobre la tarjeta; en móvil, al entrar en pantalla. Se muestra el *poster* (imagen fija) si el usuario prefiere menos movimiento o tiene ahorro de datos (`navigator.connection.saveData`).

---

## 4. Vista explosionada (despiece técnico) — `#ingenieria`

**Objetivo:** el recurso más «alta gama» del sitio. Muestra que entendemos el interior de una lavadora alemana pieza por pieza: rigor, orden, ingeniería.

**Concepto:** ilustración vectorial isométrica de una lavadora de carga frontal, en línea fina gris carbón y acentos azul cielo, sobre fondo blanco. Al hacer scroll, las piezas se separan en el eje Z: **panel frontal → puerta y vidrio → fuelle (goma) → tambor → cuba → motor inverter → bomba de desagüe → placa electrónica**. Etiquetas con líneas guía aparecen junto a cada pieza («Motor inverter: diagnóstico de escobillas y rodamientos»).

**Implementación**
- SVG con cada pieza en un `<g>` propio. Cada grupo recibe un desplazamiento proporcional al progreso del scroll:
  ```css
  .explode g { transform: translate(calc(var(--p) * var(--dx)), calc(var(--p) * var(--dy))); }
  ```
  ```js
  // --p va de 0 a 1 según cuánto se ha recorrido la sección (sticky de 200vh)
  ```
- Progresivo: en navegadores modernos se puede usar `animation-timeline: view()` (solo CSS); como respaldo, un pequeño `requestAnimationFrame` + `IntersectionObserver`.
- Móvil: versión vertical, las piezas se separan hacia abajo; en movimiento reducido se muestra directamente el despiece abierto.
- **Producción:** encargar a un ilustrador técnico (o modelar en Blender y exportar a SVG con Freestyle). **No** reproducir diseños patentados exactos de una marca: lavadora genérica «de estilo europeo».

---

## Diferencial único: «Charlas de uso» — `#charlas-de-uso`

Sección editorial (fondo `--sky-50`), con el titular **«No solo lo reparamos. Te enseñamos a cuidarlo.»** y:

- 3 tarjetas-consejo descargables (ej.: «Por qué tu lavadora huele mal y cómo evitarlo en 2 minutos», «La temperatura correcta de tu refrigerador», «Cómo limpiar una encimera de inducción sin rayarla»).
- Sello «Incluida en cada visita».
- Futuro: captura de correo/WhatsApp con «Recibe la guía de cuidado de tu equipo» → base de clientes para mantenciones preventivas (ingreso recurrente).
