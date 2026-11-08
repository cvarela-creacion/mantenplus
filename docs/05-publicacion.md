# 05 · Publicación en mantenplus.cl y correo corporativo

Cómo dejar funcionando **https://mantenplus.cl** (la web en GitHub Pages) y **contacto@mantenplus.cl** (Zoho Mail), con Cloudflare como administrador gratuito del DNS.

## Situación de partida

| Pieza | Estado |
|---|---|
| Web | Publicada gratis en GitHub Pages desde la rama `claude/mantenplus-web-redesign-cgys0a`: https://cvarela-creacion.github.io/mantenplus/ |
| Dominio `mantenplus.cl` | Registrado en **NIC Chile**, que solo anota qué *servidores de nombre* administran el dominio. No permite crear registros (A, CNAME, MX, TXT) |
| Correo | Plan anual de **Zoho Mail** pagado; Zoho pide verificar el dominio con un registro TXT para crear el buzón |

**Solución:** Cloudflare (plan Free) administra los registros del dominio. No es un hosting: la web sigue en GitHub y el correo en Zoho.

## Resumen del orden

1. Crear la cuenta en Cloudflare y agregar `mantenplus.cl` (paso 1).
2. Cargar en Cloudflare los registros de la web y del correo (paso 2).
3. Revisar DNSSEC y cambiar los servidores de nombre en NIC Chile (paso 3).
4. Esperar a que Cloudflare marque el dominio como *Active*.
5. Activar el correo en Zoho: verificar, crear el buzón, DKIM (paso 4).
6. Conectar el dominio en GitHub y activar HTTPS (pasos 5 y 6).
7. Probar web y correo (paso 7).

Los registros que se cargan en Cloudflare **empiezan a valer cuando NIC Chile apunta el dominio a Cloudflare**. Ese cambio tarda desde minutos hasta unas horas (en casos raros, 24–48 h). Hasta entonces, Zoho y GitHub no podrán verificar.

---

## Paso 1 · Cuenta en Cloudflare

1. Crear la cuenta en cloudflare.com y **activar la verificación en dos pasos** (quien controla el DNS controla la web y el correo).
2. *Add a site* (o *Add a domain*) → `mantenplus.cl` → plan **Free**.
3. Cloudflare busca registros existentes. Lo normal es que no encuentre ninguno; si encuentra alguno que no reconoces, se puede borrar.
4. Anotar los **dos servidores de nombre** que entrega Cloudflare (del tipo `nombre.ns.cloudflare.com`). **Todavía no** cambiarlos en NIC Chile.

## Paso 2 · Cargar los registros en Cloudflare

En Cloudflare → `mantenplus.cl` → **DNS → Records → Add record**. En *Name*, `@` significa el dominio raíz (`mantenplus.cl`).

### Web (GitHub Pages)

| Tipo | Name | Contenido | Proxy |
|---|---|---|---|
| A | `@` | `185.199.108.153` | DNS only |
| A | `@` | `185.199.109.153` | DNS only |
| A | `@` | `185.199.110.153` | DNS only |
| A | `@` | `185.199.111.153` | DNS only |
| AAAA (opcional) | `@` | `2606:50c0:8000::153` · `2606:50c0:8001::153` · `2606:50c0:8002::153` · `2606:50c0:8003::153` (cuatro registros) | DNS only |
| CNAME | `www` | `cvarela-creacion.github.io` | DNS only |

Dejar estos registros en **«DNS only» (nube gris)**. Con el proxy activado (nube naranja), GitHub no puede emitir el certificado HTTPS.

### Correo (Zoho Mail)

Copiar los valores **exactamente como los muestra Zoho** en su asistente de configuración: cambian según la región de la cuenta (`zoho.com`, `zoho.eu`, etc.). Los ejemplos son los de la región de EE. UU.

| Tipo | Name | Contenido | Prioridad |
|---|---|---|---|
| TXT | `@` | Código de verificación de Zoho (del tipo `zoho-verification=zbXXXXXXXX.zmverify.zoho.com`) | — |
| MX | `@` | `mx.zoho.com` | 10 |
| MX | `@` | `mx2.zoho.com` | 20 |
| MX | `@` | `mx3.zoho.com` | 50 |
| TXT (SPF) | `@` | `v=spf1 include:zohomail.com ~all` | — |
| TXT (DMARC) | `_dmarc` | `v=DMARC1; p=none; rua=mailto:contacto@mantenplus.cl` | — |

- **Verificación:** si en Zoho se elige el método CNAME en vez de TXT, crear el CNAME que indique (nombre `zbXXXXXXXX`, destino `zmverify.zoho.com`) con proxy en *DNS only*.
- **MX:** sin estos registros no llega ningún correo. Cloudflare no aplica proxy a los MX.
- **SPF:** debe existir **un solo** registro SPF en `@`. Si más adelante otro servicio envía correos en nombre del dominio (por ejemplo, un sistema de facturación), se agrega su `include:` dentro del mismo registro, sin crear otro.
- **DMARC:** con `p=none` solo se reciben informes, sin bloquear nada. Cuando el correo funcione bien unas semanas, se puede subir a `p=quarantine`.
- **DKIM** se agrega en el paso 4, porque Zoho lo genera después de verificar el dominio.

## Paso 3 · Cambiar los servidores de nombre en NIC Chile

1. **DNSSEC:** en el panel de NIC Chile (clientes.nic.cl), revisar si el dominio tiene DNSSEC activado (registros DS). Si lo tiene, **desactivarlo antes** del cambio; si no, el dominio puede dejar de responder. Lo habitual es que no esté activado.
2. En el dominio `mantenplus.cl`, modificar los **servidores de nombre** y reemplazarlos por los dos de Cloudflare. Guardar.
3. Cloudflare avisa por correo cuando el dominio queda **Active**. En el panel de Cloudflare se puede pulsar *Check nameservers* para acelerar la revisión.

## Paso 4 · Activar el correo en Zoho Mail

1. **Verificar el dominio:** en Zoho, pulsar *Verificar*. Si falla, esperar un rato y reintentar: casi siempre es que el cambio de servidores aún no se propaga.
2. **Crear el buzón** `contacto@mantenplus.cl` (y alias si se necesitan, por ejemplo `empresas@` o `ventas@`, que llegan al mismo buzón).
3. **Comprobar MX y SPF** en la configuración de correo del dominio en Zoho (consola de administración). Zoho marca cada uno como verificado cuando los ve publicados.
4. **DKIM:** en esa misma configuración, agregar un selector (por ejemplo `zmail`). Zoho genera un registro TXT:
   - En Cloudflare: tipo **TXT**, *Name* `zmail._domainkey` (el selector elegido + `._domainkey`), contenido el valor completo que muestra Zoho.
   - Volver a Zoho, pulsar *Verificar* y **activar** DKIM.
5. **Uso diario:** app **Zoho Mail** para iPhone y Android, o el correo web de Zoho. Para Outlook u otro programa, usar los datos IMAP/SMTP que indica Zoho para la región de la cuenta.

## Paso 5 · Verificar el dominio en GitHub (recomendado)

Evita que otra cuenta de GitHub pueda usar el dominio.

1. Foto de perfil → **Settings** (de la cuenta) → **Pages** → **Add a domain** → `mantenplus.cl`.
2. GitHub muestra un registro **TXT** con nombre `_github-pages-challenge-cvarela-creacion`. Crearlo en Cloudflare (tipo TXT, ese *Name*, el valor que indica GitHub) y pulsar **Verify**.

## Paso 6 · Conectar el dominio en el repositorio

1. Repositorio → **Settings** → **Pages** → *Custom domain*: escribir `mantenplus.cl` → **Save**.
2. GitHub agrega un archivo `CNAME` a la rama publicada (`claude/mantenplus-web-redesign-cgys0a`). Es necesario: **no borrarlo**. Quien siga editando el sitio debe traer ese cambio (`git pull`) antes de trabajar.
3. Esperar a que el chequeo de DNS salga en verde.
4. Marcar **Enforce HTTPS** cuando se habilite (el certificado puede tardar hasta una hora más).

Desde ese momento, `cvarela-creacion.github.io/mantenplus/` y `www.mantenplus.cl` redirigen a `https://mantenplus.cl`. El sitio ya está preparado para el dominio: la dirección canónica, el sitemap y los metadatos para Google y redes apuntan a `https://mantenplus.cl`.

## Paso 7 · Comprobar que todo funciona

- [ ] `https://mantenplus.cl` y `https://www.mantenplus.cl` abren la web con candado (HTTPS).
- [ ] Un correo enviado **desde Gmail a** contacto@mantenplus.cl llega.
- [ ] Un correo enviado **desde** contacto@mantenplus.cl a Gmail llega a la bandeja de entrada, no a spam. En Gmail → *Mostrar original*, SPF, DKIM y DMARC deben decir **PASS**.
- [ ] El botón «Enviar por correo» del diálogo de contacto de la web abre un correo dirigido a contacto@mantenplus.cl.
- [ ] Al pegar `https://mantenplus.cl` en WhatsApp aparece la vista previa con la imagen de la marca.

## Problemas frecuentes

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| Zoho no verifica el dominio | El cambio de servidores aún no se propaga, o el TXT quedó con otro nombre | Esperar y reintentar; confirmar que el TXT esté en `@` y que Cloudflare muestre el dominio como *Active* |
| No llegan correos | Faltan los MX o tienen otra prioridad o región | Revisar los tres MX contra lo que muestra Zoho |
| Los correos enviados caen en spam | Falta DKIM o SPF, o hay dos registros SPF | Completar DKIM, dejar un solo SPF y revisar *Mostrar original* en Gmail |
| GitHub dice «DNS check unsuccessful» | Servidores aún no propagados, o registros con nube naranja | Esperar; poner los registros de la web en *DNS only* |
| *Enforce HTTPS* no se puede marcar | El certificado aún no se emite | Esperar hasta una hora; si hay un registro **CAA**, agregar uno que permita `letsencrypt.org` |
| El dominio dejó de responder tras el cambio | DNSSEC activo en NIC Chile con los datos antiguos | Desactivar DNSSEC en NIC Chile |

## Después del lanzamiento

- **Google Search Console:** verificar el dominio (Google entrega un registro TXT que se crea en Cloudflare) y enviar `https://mantenplus.cl/sitemap.xml`.
- **Google Business Profile:** crear o completar la ficha (alimenta las reseñas y el mapa) y poner su enlace en `[LINK_GOOGLE_RESENAS]`.
- **Opcional:** GA4 y/o Meta Pixel. El sitio ya envía los eventos de conversión (`hero_agendar`, `servicio_<equipo>`, `cobertura_consulta`, `contacto_formulario`…) si se instalan.

## Lista de control antes de anunciar el sitio

- [ ] Correo contacto@mantenplus.cl recibiendo y enviando (paso 7).
- [ ] Número de WhatsApp y móvil real (`569XXXXXXXX` y «Número definitivo pendiente»).
- [ ] Enlaces de Instagram, Facebook y reseñas de Google.
- [ ] Comunas de cobertura confirmadas.
- [ ] Respuestas de Preguntas frecuentes y promesas del servicio validadas (ver `01-arquitectura.md`).
- [ ] Fotos propias con el uniforme oficial en lugar de las que llevan el rótulo «Imagen referencial» (ver `07-directrices-marca.md`).
- [ ] Sección Opiniones con reseñas reales, u oculta.

> El repositorio es público: además de la web, cualquiera puede ver el código y la carpeta `docs/` en GitHub (y también en `…/docs/` dentro del sitio publicado). No guardar ahí contraseñas, códigos de verificación ni otros datos privados.

## Notas

- **Cambiar la rama de publicación:** si más adelante se prefiere publicar desde `main`, primero se fusiona el pull request #1, después se cambia la rama en *Settings → Pages*, y se confirma que el archivo `CNAME` siga en la rama nueva.
- **Alternativa a GitHub Pages:** Cloudflare Pages, también gratis (*Workers & Pages → Create → Pages → Connect to Git* → repositorio `cvarela-creacion/mantenplus`, sin comando de compilación, carpeta `/`; luego *Custom domains* → `mantenplus.cl` y `www.mantenplus.cl`). No es necesario mientras GitHub Pages funcione bien.
