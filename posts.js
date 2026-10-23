/* ============================================================
   ☁️  MURO CELESTE — archivo de contenido
   ------------------------------------------------------------
   Este es el ÚNICO archivo que necesitas tocar para agregar posts.

   Para agregar un post, copia una línea dentro de POSTS = [ ... ]:

     { url: "https://x.com/usuario/status/1234567890", date: "2026-10-22" },

   Campos:
     url    (obligatorio)  link del post original (X, Instagram o YouTube)
     date   (opcional)     fecha en que lo agregaste, formato AAAA-MM-DD
     note   (opcional)     una notita tuya que aparece bajo el post
     tags   (opcional)     etiquetas, ej: ["arte", "gatitos"]
     network(opcional)     "x" | "instagram" | "youtube" — se detecta solo

   También puedes poner solo el link entre comillas:
     "https://www.instagram.com/p/ABC123/",

   Los más recientes (por fecha) se muestran primero. Si varios tienen
   la misma fecha, salen en el mismo orden de esta lista (el de arriba primero),
   así que lo más fácil es pegar los nuevos ARRIBA de la lista.
   ============================================================ */

window.SITE_CONFIG = {
  username: "naciceleste",
  title: "El búnker de Ⱥrmin",
  tagline: "Documentando mi obsesiva necesidad de verlo todo 🙂",
  profiles: {
    x:         { url: "https://x.com/naciceleste",                 enabled: true  },
    instagram: { url: "https://www.instagram.com/naciceleste/",    enabled: true  },
    // Cuando abras tu canal, cambia enabled a true ↓
    youtube:   { url: "https://www.youtube.com/@naciceleste",      enabled: false }
  }
};

window.POSTS = [
  // Pega tus posts aquí abajo 👇 (los nuevos, mejor arriba)
  { url: "https://x.com/srtamilanesaa/status/2112860573977186470", date: "2026-10-22" },
  { url: "https://x.com/RyderNoContext/status/2113020079550157005", date: "2026-10-22" },
  { url: "https://x.com/ClauLocura/status/2112694588557427151", date: "2026-10-22" },
  { url: "https://x.com/Wheeljacklib2/status/2112125724978987282", date: "2026-10-22" },
  { url: "https://x.com/Solithra/status/2111566354905989282", date: "2026-10-22" },
  { url: "https://www.instagram.com/p/DemBmRljHxK/", date: "2026-10-22" },
  { url: "https://www.instagram.com/p/Dej5f9AAVPg/", date: "2026-10-22" },
  { url: "https://www.instagram.com/p/DechQzfNfug/", date: "2026-10-22" },
  { url: "https://www.instagram.com/p/Ddl6EFKBjCd/", date: "2026-10-22" },
  { url: "https://www.instagram.com/p/DdaNppNAL98/", date: "2026-10-22" },
  { url: "https://www.instagram.com/p/Ddh5-oLAGQ-/", date: "2026-10-22" },

];
