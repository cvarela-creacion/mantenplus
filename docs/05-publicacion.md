# 05 · Publicación en mantenplus.cl

El sitio es **estático** (HTML, CSS y JS sin compilación), así que se puede publicar gratis en un servicio de hosting estático.

**Recomendación: Cloudflare Pages + DNS de Cloudflare.** Es gratis, incluye HTTPS automático, CDN global y se actualiza solo cada vez que se fusiona un cambio en `main`.

> Los dominios **.cl** se administran en **NIC Chile** (clientes.nic.cl), que solo delega el dominio a unos *servidores de nombre* (DNS). Por eso el dominio se conecta cambiando esos servidores por los de Cloudflare.

## Antes de empezar: el correo

⚠️ Si **contacto@mantenplus.cl ya funciona** (Google Workspace, Zoho, el correo del hosting, etc.), al cambiar los servidores de nombre hay que **copiar en Cloudflare los registros MX y TXT (SPF/DKIM)** del proveedor de correo. Si no, el correo deja de llegar. Cloudflare suele importarlos al agregar el dominio, pero hay que verificarlos uno a uno antes del paso 4.

## Pasos

1. **Fusionar el pull request** en la rama `main` de GitHub.
2. **Crear el proyecto en Cloudflare Pages** (dash.cloudflare.com → *Workers & Pages* → *Create* → *Pages* → *Connect to Git*):
   - Repositorio: `cvarela-creacion/mantenplus`, rama `main`.
   - Framework preset: **None**. Build command: **vacío**. Build output directory: **`/`**.
   - Se publica en una dirección provisoria `*.pages.dev` para revisar.
3. **Agregar el dominio a Cloudflare** (*Add a site* → `mantenplus.cl`, plan Free). Revisar los registros importados (sobre todo MX/TXT del correo). Cloudflare entrega **dos servidores de nombre** (p. ej. `xxx.ns.cloudflare.com`).
4. **Cambiar los servidores DNS en NIC Chile:** clientes.nic.cl → dominio `mantenplus.cl` → modificar servidores de nombre → reemplazarlos por los dos de Cloudflare. La propagación puede tardar desde minutos hasta 24–48 h.
5. **Conectar el dominio al proyecto:** en el proyecto de Pages → *Custom domains* → agregar `mantenplus.cl` y `www.mantenplus.cl`. El certificado HTTPS se emite solo.
6. **Redirigir `www` al dominio principal** (*Rules* → *Redirect Rules*: `www.mantenplus.cl/*` → `https://mantenplus.cl/$1`, 301), para que Google vea una sola versión (el `canonical` del sitio ya apunta a `https://mantenplus.cl/`).
7. **Después de publicar:**
   - Google Search Console: verificar el dominio (registro TXT en Cloudflare) y enviar `https://mantenplus.cl/sitemap.xml`.
   - Google Business Profile: crear o completar la ficha (es lo que alimenta las reseñas y el mapa) y poner su enlace en `[LINK_GOOGLE_RESENAS]`.
   - Opcional: GA4 y/o Meta Pixel. El sitio ya envía los eventos de conversión (`hero_agendar`, `servicio_<equipo>`, `cobertura_consulta`, `contacto_formulario`…) si se instalan.
   - Probar la vista previa del enlace pegando `https://mantenplus.cl` en WhatsApp (usa `assets/img/og-mantenplus.jpg`).

## Lista de control antes de abrir el dominio al público

- [ ] Número de WhatsApp real (`569XXXXXXXX` y `+56 9 XXXX XXXX`).
- [ ] Enlaces de Instagram, Facebook y reseñas de Google.
- [ ] Comunas de cobertura confirmadas.
- [ ] Respuestas de Preguntas frecuentes y promesas del servicio validadas (ver `01-arquitectura.md`).
- [ ] **Imágenes y videos de stock reemplazados por material propio**, en especial el **antes/después** (mostrar resultados de stock como trabajos propios sería engañoso) y la **foto del equipo** (los clientes esperan ver a las personas que llegarán a su casa).
- [ ] Sección Opiniones con reseñas reales, u oculta.

## Alternativa: GitHub Pages

Como el repositorio es público, también sirve GitHub Pages (Settings → Pages → rama `main`, carpeta `/`). En ese caso: agregar un archivo `CNAME` con `mantenplus.cl` y, en el DNS (igual se necesita un proveedor como Cloudflare), registros A hacia las IP de GitHub Pages y un CNAME `www` → `cvarela-creacion.github.io`.
