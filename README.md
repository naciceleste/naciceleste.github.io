# Biblioteca pública de Ⱥrmin · @naciceleste

Documentando mi obsesiva necesidad de verlo todo 🙂

Los momentos que me gustan en Twitter/X e Instagram (y pronto YouTube), todas en un solo lugar.
Las imágenes **no** se guardan aquí: se cargan directamente desde cada red y al tocarlas te llevan al post original.

- **Página principal** (`/`): muro celeste estilo Tumblr con los posts completos (embeds oficiales), modo claro y oscuro
  (botón ☀️/🌙 arriba a la derecha; por defecto sigue el tema del sistema y recuerda la elección).
- **Versión cuadrícula** (`/cuadricula/`): cuadrícula de imágenes minimal. Al pasar el mouse se ve la red y la fecha del post (DD/MM/AA).

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
(se ven en la página principal). **Cada línea termina con una coma.**

Links que funcionan: `x.com/…/status/…` o `twitter.com/…/status/…` · Instagram `…/p/CODIGO/` o `…/reel/CODIGO/` ·
YouTube `watch?v=…`, `youtu.be/…`, `shorts/…`.

## media.js (automático)
`media.js` guarda **solo enlaces** a las imágenes de X, las fechas de publicación y medidas para recortar bien. No contiene imágenes.
Lo genera `scripts/actualizar-medios.mjs`, y en GitHub lo corre solo la Action **Actualizar medios**
(`.github/workflows/medios.yml`) cada vez que cambias `posts.js` y una vez por semana.
Si algo falla (por ejemplo, Instagram bloquea la consulta), se conservan los datos que ya había.
Mientras un tuit nuevo no esté en `media.js`, se muestra un cuadro con texto en su lugar.

Para correrlo a mano: `node scripts/actualizar-medios.mjs` (Node 18 o más nuevo).

## Mi lista de YouTube (automática)
La sección **Mi lista de YouTube** muestra los videos de mi lista pública "Biblioteca"
(https://www.youtube.com/playlist?list=PLJ-DohLIgv3w) en cuadrícula: miniatura completa en 16:9 y los Shorts como póster 9:16.
En "Todos" se ve un adelanto; con el filtro **YouTube** se ven todos. También aparecen en la versión cuadrícula.

Para sumar un video: en YouTube, *Guardar* → *Biblioteca*. Los datos viven en `youtube.js` (no editar a mano), que genera
`scripts/youtube_sync.py` leyendo el feed público de la lista (sin login ni API key). Solo agrega videos nuevos, nunca borra.

```
python3 scripts/youtube_sync.py            # agrega los nuevos y, si hubo, hace commit + push
python3 scripts/youtube_sync.py --no-push  # solo actualiza youtube.js
python3 scripts/youtube_sync.py --dry-run  # muestra qué agregaría
```
Ojo: el feed muestra como máximo ~15 videos de la lista. Conviene que en la lista los nuevos se agreguen **arriba**.

## Título, frase y foto
El título y la frase de arriba se cambian en `posts.js` (`title` y `tagline`). La foto de perfil es `assets/avatar.jpg`
(copia de la foto de Twitter); para cambiarla, sube otra imagen cuadrada con ese mismo nombre.
El título usa la letra Merriweather porque tiene la **Ⱥ**.

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
- `index.html`, `styles.css`, `app.js` – página principal (muro celeste)
- `cuadricula/` – versión cuadrícula
- `posts.js` – **tus posts y configuración** ← el único que vas a editar
- `media.js` – datos automáticos (no editar)
- `youtube.js`, `scripts/youtube_sync.py` – mi lista de YouTube (automático)
- `yt-canales.js` – accesos directos a mis canales de YouTube (una línea por canal)
- `scripts/actualizar-medios.mjs`, `.github/workflows/medios.yml` – actualización automática
- `assets/avatar.jpg` – foto de perfil
- `assets/favicon.svg` – iconito de la pestaña
