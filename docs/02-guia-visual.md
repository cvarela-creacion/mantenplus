# 02 · Guía visual — «Minimalismo luminoso»

**Idea:** la web debe sentirse como una cocina recién limpiada: luz, aire, superficies blancas y un azul cielo que transmite frescura y transparencia. El gris carbón y el rojo del logotipo se conservan como **firma de marca**, no como color de fondo.

## Paleta

| Rol | Token | Hex | Uso |
|---|---|---|---|
| Fondo principal | `--white` | `#FFFFFF` | 70 % de la superficie |
| Fondo alterno | `--gray-25` / `--gray-50` | `#FAFBFC` / `#F4F6F8` | Secciones alternas, tarjetas |
| Cielo muy claro | `--sky-50` / `--sky-100` | `#F3F9FE` / `#E4F2FC` | Degradados del Hero, chips activos, subrayados |
| Cielo medio | `--sky-300` / `--sky-400` | `#9BD0F2` / `#5DB3EA` | Ilustraciones, bordes activos |
| **Acción** | `--sky-600` | `#1478C2` | **Botón primario** (blanco sobre azul: 4,8 : 1, AA) |
| Acción hover | `--sky-700` | `#0F5F9C` | Hover, enlaces, texto sobre fondo celeste |
| Titulares | `--ink` | `#151B23` | H1–H3 |
| Texto | `--gray-700` / `--gray-500` | `#3B4450` / `#6B7682` | Cuerpo / secundario |
| Marca: carbón | `--brand-ink` | `#2E3036` | Isotipo, «MANTEN» |
| Marca: rojo | `--brand-red` | `#C8202F` | **Solo** «PLUS» y detalles mínimos (≤ 2 % de la pantalla) |

Proporción recomendada: **70 % blanco · 20 % grises claros · 8 % azul cielo · 2 % carbón/rojo.**

> ¿Por qué el botón no es rojo como el logo? El rojo en servicios técnicos se asocia a «urgencia/avería». El azul cielo comunica calma y limpieza, y destaca con fuerza sobre un fondo blanco. El rojo queda reservado para la marca.

## Tipografía

| Uso | Fuente | Pesos | Por qué |
|---|---|---|---|
| Titulares, botones, logotipo en HTML | **Plus Jakarta Sans** | 600 · 700 · 800 | Geométrica como el logotipo, moderna y cálida (y su nombre es un guiño a «Plus») |
| Texto | **Inter** | 400 · 500 · 600 | Máxima legibilidad en pantallas pequeñas |

- H1: `clamp(2.25rem → 4.125rem)`, peso 800, interlineado 1,04, tracking −3,5 %.
- Lead: `clamp(1.0625rem → 1.25rem)`, interlineado 1,65, gris 500.
- **Producción:** autoalojar las fuentes en `/assets/fonts` (WOFF2, subconjunto latino) para quitar la dependencia de Google Fonts y ganar ~150 ms.

## Formas, sombras y movimiento

- **Radios:** 10 px (pequeño) · 16 px (tarjetas) · 28 px (imágenes grandes) · **píldora** para todos los botones y chips.
- **Sombras:** suaves y teñidas de azul (`--shadow-lg`), nunca negras ni duras.
- **Vidrio esmerilado** (`backdrop-filter`) solo en header, tarjetas flotantes y barra móvil.
- **Retícula de puntos** muy sutil en el Hero: guiño a «ingeniería» sin recargar.
- **Movimiento:** curva `cubic-bezier(.2,.7,.2,1)`, 200–800 ms. Elementos que «respiran» (tarjetas flotantes, sello giratorio) muy lentos. Todo se desactiva con `prefers-reduced-motion`.

## Botones

| Tipo | Clase | Cuándo |
|---|---|---|
| Primario | `.btn--primary` | Solo «Agendar servicio» (una por vista) |
| Suave | `.btn--soft` | Acción secundaria («Cómo trabajamos») |
| Fantasma | `.btn--ghost` | Terciaria (correo en el header) |

Altura mínima 48 px (58 px en el Hero) → cómodos para el pulgar en iOS y Android.

## Iconografía

Línea de 1,8 px con extremos redondeados (mismo lenguaje que el contorno de la casa del logotipo). Sprite SVG en línea: 0 peticiones extra.

## Logotipo

- `assets/img/logo-mark.svg`: el isotipo **redibujado en vector** (casa + refrigerador + lavadora), nítido a cualquier tamaño y coloreable con `currentColor`.
- En el header, el texto «MANTEN**PLUS**» va en HTML (Plus Jakarta Sans 800) para que sea nítido y liviano.
- `assets/brand/logo-mantenplus-original.png`: el original de referencia.
- El sello circular del Hero reinterpreta el parche **«German Engineering»** de la manga del uniforme: conecta la web con lo que el cliente verá en persona.
