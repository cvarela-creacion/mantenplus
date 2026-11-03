# 05 · Publicación en mantenplus.cl con GitHub Pages

El sitio es **estático** (HTML, CSS y JS sin compilación) y el repositorio es **público**, así que GitHub Pages lo publica **gratis**, con HTTPS incluido. No hace falta contratar hosting.

## Paso 1 · Activar GitHub Pages (1 minuto)

1. En GitHub, abrir el repositorio → **Settings** → **Pages** (menú izquierdo).
2. En *Build and deployment → Source*, elegir **Deploy from a branch**.
3. En *Branch*, elegir la rama y la carpeta **`/ (root)`**, y pulsar **Save**:
   - Para revisar **antes** de aprobar el pull request: `claude/mantenplus-web-redesign-cgys0a`.
   - Para el lanzamiento oficial: **`main`** (después de fusionar el pull request).
4. En uno o dos minutos el sitio queda en **https://cvarela-creacion.github.io/mantenplus/**. El avance se ve en la pestaña **Actions** (*pages build and deployment*).

El repositorio incluye un archivo `.nojekyll` para que GitHub publique los archivos tal cual, sin procesarlos.

## Paso 2 · Preparar el DNS de mantenplus.cl

Los dominios **.cl** se administran en **NIC Chile** (clientes.nic.cl), que solo delega el dominio a unos *servidores de nombre* (DNS). Los registros que pide GitHub se crean en ese servicio de DNS:

- Si ya tienes un panel de DNS para el dominio (por ejemplo, donde se configuró el correo), usa ese.
- Si no, **Cloudflare DNS** es gratis (no es hosting, solo DNS): *Add a site* → `mantenplus.cl` → plan Free. Luego, en NIC Chile, reemplaza los servidores de nombre por los dos que entrega Cloudflare.

⚠️ **Correo:** si contacto@mantenplus.cl ya funciona y cambias de proveedor de DNS, copia antes los registros **MX** y **TXT** (SPF/DKIM) del correo en el nuevo DNS. Si no, el correo deja de llegar.

## Paso 3 · Verificar el dominio en GitHub (recomendado)

Evita que otra cuenta de GitHub pueda apropiarse del dominio.

1. Foto de perfil → **Settings** (de la cuenta) → **Pages** → **Add a domain** → `mantenplus.cl`.
2. GitHub muestra un registro **TXT** (`_github-pages-challenge-cvarela-creacion.mantenplus.cl`). Crearlo en el DNS y pulsar **Verify**.

## Paso 4 · Crear los registros DNS

| Tipo | Nombre | Valor |
|---|---|---|
| A | `@` (mantenplus.cl) | `185.199.108.153` |
| A | `@` | `185.199.109.153` |
| A | `@` | `185.199.110.153` |
| A | `@` | `185.199.111.153` |
| AAAA (opcional) | `@` | `2606:50c0:8000::153` · `2606:50c0:8001::153` · `2606:50c0:8002::153` · `2606:50c0:8003::153` |
| CNAME | `www` | `cvarela-creacion.github.io` |

En **Cloudflare**, dejar estos registros en **«DNS only»** (nube gris). Con el proxy activado (nube naranja), GitHub no puede emitir el certificado HTTPS.

## Paso 5 · Conectar el dominio en el repositorio

1. Repositorio → **Settings** → **Pages** → *Custom domain*: escribir `mantenplus.cl` → **Save**. GitHub agrega solo un archivo `CNAME` a la rama publicada.
2. Esperar a que el chequeo de DNS salga en verde. Puede tardar desde minutos hasta 24–48 h si se cambiaron los servidores de nombre.
3. Marcar **Enforce HTTPS** cuando se habilite (el certificado puede tardar hasta una hora más).
4. `www.mantenplus.cl` redirige solo a `mantenplus.cl` gracias al CNAME de `www`.

> **No agregar el archivo `CNAME` antes de tiempo.** Con ese archivo, GitHub redirige `cvarela-creacion.github.io/mantenplus` al dominio. Si el DNS aún no está listo, la vista previa deja de funcionar.

## Paso 6 · Después del lanzamiento

- **Google Search Console:** verificar el dominio (registro TXT) y enviar `https://mantenplus.cl/sitemap.xml`.
- **Google Business Profile:** crear o completar la ficha (alimenta las reseñas y el mapa) y poner su enlace en `[LINK_GOOGLE_RESENAS]`.
- **Vista previa del enlace:** pegar `https://mantenplus.cl` en WhatsApp para comprobarla (usa `assets/img/og-mantenplus.jpg`).
- **Opcional:** GA4 y/o Meta Pixel. El sitio ya envía los eventos de conversión (`hero_agendar`, `servicio_<equipo>`, `cobertura_consulta`, `contacto_formulario`…) si se instalan.

## Lista de control antes del lanzamiento oficial

- [ ] Número de WhatsApp real (`569XXXXXXXX` y `+56 9 XXXX XXXX`).
- [ ] Enlaces de Instagram, Facebook y reseñas de Google.
- [ ] Comunas de cobertura confirmadas.
- [ ] Respuestas de Preguntas frecuentes y promesas del servicio validadas (ver `01-arquitectura.md`).
- [ ] Fotos y videos propios, en especial el **antes/después** y la **foto del equipo**.
- [ ] Sección Opiniones con reseñas reales, u oculta.

> El repositorio es público: además de la web, cualquiera puede ver el código y la carpeta `docs/` en GitHub (y también en `…/docs/` dentro del sitio publicado). No guardar ahí datos privados.

## Alternativa: Cloudflare Pages

También gratis. Workers & Pages → *Create* → *Pages* → *Connect to Git* → repositorio `cvarela-creacion/mantenplus`, rama `main`, sin comando de compilación, carpeta `/`. Luego *Custom domains* → `mantenplus.cl` y `www.mantenplus.cl`.
