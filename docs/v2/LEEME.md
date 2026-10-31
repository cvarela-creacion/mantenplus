# MantenPlus V2 — entrega de desarrollo

Base inmutable: `3ce90c636f5ee560e552633ff6cd33bf4f70183f` (29 de octubre de 2026), «Prepara la publicación con GitHub Pages».

## Abrir las propuestas

Desde la carpeta del proyecto, ejecutar `python3 -m http.server 8080` y abrir:

- A completa: http://localhost:8080/index.html
- B, portada y navegación alternativas con los mismos módulos: http://localhost:8080/b.html

También se pueden abrir ambos HTML directamente; el servidor local es preferible para copiar mensajes y ejecutar las pruebas. No hay compilación ni dependencias de producción. No se ha creado una vista pública ni cambiado GitHub Pages.

Ramas: `backup/mantenplus-claude-original` fija en el SHA anterior; `codex/mantenplus-v2-a` para A; `codex/mantenplus-v2-b-hero-menu` para B. Ambas tienen como ancestro el commit exacto de Claude. En la rama B, `index.html` abre B directamente. En A, `b.html` permite la comparación local sin cambiar de rama. No existe selector A/B para clientes.

## Auditoría e inventario

Se leyeron los cinco documentos originales, README, HTML, CSS, JS y recursos de marca. El ZIP adjunto contiene siete entradas: instrucciones iniciales, prompt maestro, tarea técnica, PDF, ZIP de prototipo y dos PNG conceptuales. El ZIP interior aporta dos HTML, CSS, JS y siete recursos gráficos. Las imágenes conceptuales NO son capturas del original ni pruebas del nuevo desarrollo.

| Función original | Tratamiento V2 |
|---|---|
| Seis categorías, descripciones y averías | Conservadas completas; tarjetas reordenadas visualmente, selección hacia consulta |
| Selector rápido de equipo | Ampliado con campana, avería y comuna; todos los pasos opcionales |
| Tres comparadores de resultados | Conservados SVG, pestañas, teclado y arrastre; leyenda de referencia visible |
| Cuatro etapas del proceso | Conservadas; navegación deliberada con flechas y puntos numerados |
| Ocho componentes de lavadora | Conservados SVG y textos; botones accesibles, explicación y número resaltado |
| Charlas de uso y FAQ | Conservados los acordeones nativos y contenido |
| Equipo y espacios de opiniones | Conservados como contenido provisional; no se inventaron personas ni testimonios |
| Cobertura | Conservada lista, normalización de tildes y alias; consulta revisable |
| Formulario de contacto | Conservados campos y validación nativa; resumen editable/copiar, sin enviar reserva |
| Analítica opcional original | Conservada; no se instaló ni activó servicio externo |
| Medios pendientes | Conservados en `template[data-pending-media]`, sin solicitudes 404; activar al incorporar archivos reales |

Los documentos originales, imágenes originales y CSS original permanecen sin cambios. Los cambios de HTML y JS existen exclusivamente en las ramas V2. El HTML se serializó al reorganizar componentes; por eso el diff incluye normalización de espacios y atributos.

Cambios intencionados: se sustituye la animación del despiece basada en 240vh de scroll por una vista abierta y selección explícita; toda la información es accesible con movimiento reducido. El carrusel deja de avanzar automáticamente para que el lector controle el ritmo. La barra inferior móvil se sustituye por el contacto fijo en el encabezado, evitando ocupar la parte inferior del formulario. Las tarjetas flotantes y sello del hero se retiran de esa composición; el proceso conserva las explicaciones de atención.

## Sistema visual

- Identidad: carbón `#2E3036`, rojo `#C8202F`; isotipo vectorial original de Claude y marca tipográfica conservados, archivo original intacto.
- Texto: grafito `#172B3C`; secundario `#536472`.
- Acción: azul `#126EAF`, hover `#09598F`. Ajuste del azul original para margen de contraste; `#1478C2` permanece en acentos y foco.
- Superficies: blanco, `#F5F8FA`, azul claro `#EAF3F8`; ingeniería `#142C3F`.
- Inter para lectura; Plus Jakarta Sans para titulares. WOFF2 variables locales y licencias OFL incluidas, sin llamadas a Google Fonts.
- Retícula máxima 1320 px, escala de espaciado original de 4 px, secciones de 52–80 px; tarjetas de 12–20 px y controles de al menos 44–52 px.
- Foco visible de 3 px, etiquetas persistentes, botones con estado, diálogo nativo con cierre Escape, menú con foco cíclico y contenido exterior inerte.
- SVG de línea originales. No se añadieron librerías de interfaz.
- Imagen conceptual nueva, sin marcas ficticias: WebP de 1200 y 600 px con `srcset`, dimensiones explícitas y prioridad alta. No representa personal real ni trabajos realizados. Sustituir por fotografía propia siguiendo el brief original.

## A frente a B

A usa composición dividida con fotografía redondeada, navegación directa en escritorio y fondo claro. B utiliza una fotografía hasta el borde, titular sobre grafito, geometría más marcada y navegación mediante panel lateral también en escritorio. Ambas conservan la misma información y llamada principal, para comparar diseño.

Se recomienda A por la exposición directa del menú y lectura inicial sencilla; es una valoración de diseño, no una prueba de mayor conversión. B aporta contraste a la ingeniería y escenas del proceso de A. No se ha realizado investigación con usuarios.

«Reparamos con precisión. Cuidamos tu hogar.» funciona como titular de portada más breve, con servicio y cuidado explícitos. El eslogan «Expertos en el cuidado y reparación de tus electrodomésticos» permanece en la firma, footer y metadatos: no se cambia la identidad oficial. «Tecnología que cuida tu hogar» se descartó como titular principal porque explica menos claramente la reparación.

## Mensajes y datos provisionales

Las solicitudes se preparan en un diálogo editable. No hay backend ni persistencia y no se envían datos. Los enlaces WhatsApp existentes pasan por el mismo resumen. El número definitivo, cobertura comercial, fotos propias, redes y reseñas siguen pendientes de validación para lanzamiento; no se consideran defectos del prototipo.

Para incorporar medios originales pendientes, añadir los archivos indicados en los cinco documentos y sacar sus `picture`/`video` del `template`. Para activar WhatsApp real, configurar el número y añadir una acción explícita de envío desde el resumen; no habilitarlo durante la revisión. Los metadatos comerciales originales también deben revisarse antes de publicar.

## Pruebas

`tests/browser.cjs` requiere Playwright y Chromium. Con el servidor local activo, ejecutar `node tests/browser.cjs` (puede indicarse `CHROMIUM_PATH`). El script prueba ambas variantes a 390, 820, 1440 y 1920 px, genera capturas auténticas y `pruebas.json`. El directorio `capturas` contiene HTML realmente renderizado, no maquetas.

Ver `PRUEBAS.md` para resultados, correcciones y límites. Ninguna prueba automatizada sustituye una auditoría WCAG completa ni una prueba en dispositivos físicos.
