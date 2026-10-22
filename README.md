# @naciceleste

Las cositas que me gustan en Twitter/X e Instagram (y pronto YouTube), todas en un solo lugar.
Las imágenes **no** se guardan aquí: se cargan directamente desde cada red y al tocarlas te llevan al post original.

- **Página principal** (`/`): cuadrícula de imágenes minimal. Al pasar el mouse se ve la red y la fecha del post (DD/MM/AA).
- **Versión celeste** (`/celeste/`): muro pastel estilo Tumblr con los embeds completos.

Las dos usan el mismo `posts.js`, así que siempre muestran los mismos posts.

## Cómo agregar un post

1. Abre **`posts.js`** (en GitHub: abre el archivo y toca el lápiz ✏️).
2. Dentro de `window.POSTS = [ ... ]`, pega una línea así, **arriba** de las demás:

```js
{ url: "https://x.com/usuario/status/1234567890", date: "2026-10-22" },
```

3. Guarda (*Commit changes*). En un par de minutos aparece en la página.

La red se detecta sola por el link. `date` es el día en que lo agregaste (sirve para ordenar: los más nuevos primero;
con la misma fecha, sale primero el que está más arriba en la lista). Opcionales: `note: "una notita"` y `tags: ["arte"]`
(se ven en la versión celeste). **Cada línea termina con una coma.**

Links que funcionan: `x.com/…/status/…` o `twitter.com/…/status/…` · Instagram `…/p/CODIGO/` o `…/reel/CODIGO/` ·
YouTube `watch?v=…`, `youtu.be/…`, `shorts/…`.

## media.js (automático)
`media.js` guarda **solo enlaces** a las imágenes de X, las fechas de publicación y medidas para recortar bien. No contiene imágenes.
Lo genera `scripts/actualizar-medios.mjs`, y en GitHub lo corre solo la Action **Actualizar medios**
(`.github/workflows/medios.yml`) cada vez que cambias `posts.js` y una vez por semana.
Si algo falla (por ejemplo, Instagram bloquea la consulta), se conservan los datos que ya había.
Mientras un tuit nuevo no esté en `media.js`, se muestra un cuadro con texto en su lugar.

Para correrlo a mano: `node scripts/actualizar-medios.mjs` (Node 18 o más nuevo).

## Activar YouTube
En `posts.js`, en la línea de `youtube`, cambia `enabled: false` a `enabled: true`.

## Verla en tu compu
En una terminal dentro de esta carpeta: `python3 -m http.server 8000` y entra a http://localhost:8000

## Bueno saber
- Twitter: las imágenes vienen de `pbs.twimg.com`; si borran el tuit o la foto, deja de verse.
- Instagram: se usa el visor oficial de Instagram, agrandado y recortado para que solo se vea la foto. Solo funciona con
  cuentas públicas. Los reels muestran el botón ▶ de Instagram encima.
- Algunos bloqueadores de anuncios pueden bloquear los visores de X e Instagram.

## Archivos
- `index.html`, `style.css`, `app.js` – página principal
- `celeste/` – versión celeste (pastel)
- `posts.js` – **tus posts y configuración** ← el único que vas a editar
- `media.js` – datos automáticos (no editar)
- `scripts/actualizar-medios.mjs`, `.github/workflows/medios.yml` – actualización automática
- `assets/favicon.svg` – iconito de la pestaña
