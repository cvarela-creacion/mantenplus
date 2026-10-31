# Validación ejecutada — 31 octubre 2026

## Resultados comprobados

- Chromium real mediante Playwright. Versiones del navegador y fecha exacta en `pruebas.json`.
- 8 recorridos completos: A y B × 390, 820, 1440 y 1920 px. Sin desbordamiento horizontal del documento, excepciones JavaScript ni respuestas HTTP de error en esos recorridos.
- Menú: abrir, foco inicial, ciclo con Shift+Tab, Escape, cierre por enlace; A en móvil/tableta y B también en escritorio.
- Flujo: Lavadora → No centrifuga → Las Condes; Lavavajillas → No desagua → Providencia. Mensajes comprobados, sin envío externo.
- Comparador: cambio de caso, flecha de teclado, arrastre de ratón; prueba adicional de eventos táctiles reales emulados por CDP en Chromium.
- Componentes: selección de bomba, estado pulsado y explicación. Los ocho componentes originales siguen presentes.
- Carrusel: selección inicial y avance al paso siguiente en móvil, tableta y escritorio.
- Acordeones de consejos y FAQ, cobertura sin tildes y comuna desconocida; prueba adicional del alias Chicureo.
- Contacto: validación de campos vacíos y resumen completo con nombre/equipo/comuna/problema.
- Pruebas adicionales con movimiento normal para A y B: arrastre táctil, omisión de pasos, preselección desde tarjeta y existencia de destinos de anclas.
- Sin JavaScript: seis tarjetas y ocho componentes presentes; FAQ desplegable. Preparación de mensajes y controles JS requieren JavaScript, indicado en la página.
- Axe 4.10.3, reglas WCAG 2 A/AA y 2.1 AA: cero infracciones detectadas en A y B a 390 y 1440 px. Resultado detallado en `accesibilidad.json`.
- Capturas genuinas de las dos portadas en cuatro anchos; menús disponibles y secciones servicios, proceso, resultados, ingeniería y contacto a 390/1440.

## Errores corregidos durante pruebas

1. En tableta, dos tarjetas visibles del carrusel podían marcar dos pasos activos sucesivamente. Se calcula ahora la tarjeta más próxima al inicio del carril.
2. En escritorio, la imagen absoluta del proceso cubría los controles nuevos. Se limitó su altura y se dio a los controles su propia zona.
3. Axe detectó la región horizontal de opiniones sin acceso por teclado. Se añadió foco y nombre accesible.
4. Medios pendientes generaban peticiones fallidas del prototipo. Se conservan en templates hasta disponer del material definitivo.

## Alcance y límites

La revisión visual comprobó composición y legibilidad en las capturas. La mayor calidad artística de A/B es una propuesta sujeta a evaluación de Carlos y su hermano, no una conclusión estadística. No se midieron conversión, tiempos con usuarios, Lighthouse, Core Web Vitals ni rendimiento en redes móviles reales. No se afirma una certificación WCAG: faltan lector de pantalla, dispositivos físicos y otros motores de navegador. Las pruebas con movimiento reducido usan la preferencia real del navegador; las adicionales cubren movimiento normal.

La fotografía conceptual nueva se usa dentro del HTML, claramente rotulada; las capturas de `capturas/` son del navegador. El material gráfico del kit nunca se ha presentado como captura de una implementación.

## Reproducir

1. `npm ci` (solo dependencias de desarrollo).
2. Instalar Chromium o indicar `CHROMIUM_PATH`.
3. `python3 -m http.server 8080` en otra terminal.
4. `npm test` y `npm run test:a11y`.

La ejecución aquí utilizó Playwright 1.62.1 preinstalado y Chromium del entorno. El manifiesto fija Playwright 1.56.1, disponible públicamente, para reproducción; puede haber pequeñas diferencias de navegador/captura. Ninguna dependencia es necesaria para abrir el sitio.
