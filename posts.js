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
     pin    (opcional)     1, 2 o 3: lo fija arriba en ese orden (máximo 3)
     network(opcional)     "x" | "instagram" | "youtube" — se detecta solo

   También puedes poner solo el link entre comillas:
     "https://www.instagram.com/p/ABC123/",

   Los más recientes (por fecha) se muestran primero. Si varios tienen
   la misma fecha, salen en el mismo orden de esta lista (el de arriba primero),
   así que lo más fácil es pegar los nuevos ARRIBA de la lista.
   ============================================================ */

window.SITE_CONFIG = {
  username: "naciceleste",
  title: "Biblioteca pública de Ⱥrmin",
  tagline: "mi biblioteca pública donde guardo todo lo que me gusta 🙂",
  profiles: {
    x:         { url: "https://x.com/naciceleste",                 enabled: true  },
    instagram: { url: "https://www.instagram.com/naciceleste/",    enabled: true  },
    youtube:   { url: "https://www.youtube.com/@naci.celeste",     enabled: true  },
    tiktok:    { url: "https://www.tiktok.com/@naciceleste",       enabled: true  }
  }
};

window.POSTS = [
  // Pega tus posts aquí abajo 👇 (los nuevos, mejor arriba)
  { url: "https://x.com/CarlosMaslaton/status/1523198958100643841", date: "2026-10-27", tags: ["tuits que envejecieron mal"] },
  { url: "https://x.com/HodlerTom/status/1927340595002970346", date: "2026-10-27", tags: ["bitcoin"] },
  { url: "https://x.com/PunchingCat/status/1848188558751969566", date: "2026-10-27", tags: ["te quiero mucho gatito","gatitos"] },
  { url: "https://x.com/noplacexhideo/status/1975511909320237353", date: "2026-10-27", note: "Moraleja: Nunca se niega a una medialuna", tags: ["se va todo a la mierda"] },
  { url: "https://www.instagram.com/p/DbypFAppK38/", date: "2026-10-27", note: "Mi hermanita 🥺", tags: ["no te olvides de vivir"] },
  { url: "https://www.youtube.com/watch?v=3FnH7fJ1ntI", date: "2026-10-27", note: "El mejor creador de contenido del Río de la Plata jamás me cansaré de decirlo", tags: ["misión inútil","agustín"] },
  { url: "https://www.tiktok.com/@valesulca_/video/7647184835190082836", date: "2026-10-27", tags: ["tipazo"] },
  { url: "https://www.instagram.com/p/De8yN7kiKI_/", date: "2026-10-27", tags: ["alberto"] },
  { url: "https://x.com/labestiapau/status/2114759487718645850", date: "2026-10-27", tags: ["independiente","mickey","la voz del hincha"] },
  { url: "https://www.instagram.com/p/De7Lg22osT3/", date: "2026-10-26", tags: ["animalitos"] },
  { url: "https://x.com/elmauro1/status/2114441301466743197", date: "2026-10-26", tags: ["inimputable"] },
  { url: "https://www.instagram.com/p/De4aDqvxhcy/", date: "2026-10-26", tags: ["no te rindas"] },
  { url: "https://www.youtube.com/watch?v=5w4W6M0mh1c", date: "2026-10-25", tags: ["fieles tv","deudas"] },
  { url: "https://www.tiktok.com/@fpisso/video/7700017822268656904", date: "2026-10-25", note: "Decíselo", tags: ["franco"] },
  { url: "https://x.com/naciceleste/status/1739760034027024649", date: "2026-10-24", tags: ["yo voy a chambear"] },
  { url: "https://x.com/naciceleste/status/1804743773093588998", date: "2026-10-24", tags: ["vivan por siempre los pueblos","armin"] },
  { url: "https://x.com/CopaAmerica/status/1807984351126188098", date: "2026-10-24", note: "Dios, patria y familia", tags: ["uruguay nt","uruguay"] },
  { url: "https://x.com/naciceleste/status/1819579934408425693", date: "2026-10-24", tags: ["juegos olímpicos","nuevo formato dale rey"], pin: 3 },
  { url: "https://x.com/TheCinesthetic/status/1933658892577484834", date: "2026-10-24", note: "Me volvía loco la histeria colectiva de las cocinas, luego me acostumbré 🙃", tags: ["the bear","series"] },
  { url: "https://x.com/naciceleste/status/1875752609308668239", date: "2026-10-24", note: "Qué milagro, mamá?", tags: ["la sociedad de la nieve","fito strauch"], pin: 2 },
  { url: "https://www.instagram.com/p/DJrQwATOgCG/", date: "2026-10-24", note: "Calladito más bonito, mijo !", tags: ["parcero"] },
  { url: "https://x.com/naciceleste/status/1877115383586361753", date: "2026-10-24", note: "Que pasó con estos muñecos?", tags: ["yihadistas porteños"] },
  { url: "https://www.instagram.com/p/DcOOduIo9s-/", date: "2026-10-24", note: "No te tomes la vida tan en serio, chaval", tags: ["alberto"] },
  { url: "https://x.com/HippiesConOsde/status/2110484265242706203", date: "2026-10-24", note: "Es difícil concentrarse cuando habla Lara 🤭", tags: ["lara","oro"] },
  { url: "https://www.instagram.com/p/Dcw77T0gmAz/", date: "2026-10-24", note: "Hacé tu testamento, AHORA !", tags: ["facundo arana","testamento","no me sigas"], pin: 1 },
  { url: "https://x.com/naciceleste/status/1976050892332790063", date: "2026-10-24", note: "Como te la aplicaron viejo, al final todos iguales", tags: ["milei","avisos funebres","armin"] },
  { url: "https://x.com/ShouldHaveRabit/status/2113445248416563374", date: "2026-10-24", tags: ["conejo","rabbit","ternura time"] },
  { url: "https://www.instagram.com/p/DeS6Kcpgzw4/", date: "2026-10-24", tags: ["pietro","mentalidad"] },
  { url: "https://x.com/flanchota/status/2108211133035262362", date: "2026-10-23", tags: ["guerra civil"] },
  { url: "https://x.com/Ujjawal_athrav/status/2113638571274076506", date: "2026-10-23", tags: ["cheeseball"] },
  { url: "https://www.instagram.com/p/De0LTZkyV9D/", date: "2026-10-23", tags: ["milei","galperin","argentina"] },
  { url: "https://x.com/argentinareacts/status/1714713566765371852", date: "2026-10-23", tags: ["guerra civil","memes"] },
  { url: "https://www.instagram.com/p/De18P67RW4a/", date: "2026-10-23", tags: ["carlos","bitcoin","la moneda del pueblo"] },
  { url: "https://x.com/srtamilanesaa/status/2112860573977186470", date: "2026-10-22", tags: ["tuitazos","uruguay"] },
  { url: "https://x.com/RyderNoContext/status/2113020079550157005", date: "2026-10-22", tags: ["factos"] },
  { url: "https://x.com/ClauLocura/status/2112694588557427151", date: "2026-10-22", tags: ["aves"] },
  { url: "https://x.com/Wheeljacklib2/status/2112125724978987282", date: "2026-10-22", tags: ["bocchi"] },
  { url: "https://x.com/Solithra/status/2111566354905989282", date: "2026-10-22", tags: ["dibujos","halloween"] },
  { url: "https://www.instagram.com/p/DemBmRljHxK/", date: "2026-10-22", tags: ["no guardes ropa loco"] },
  { url: "https://www.instagram.com/p/Dej5f9AAVPg/", date: "2026-10-22", tags: ["pietro","psicología"] },
  { url: "https://www.instagram.com/p/DechQzfNfug/", date: "2026-10-22", tags: ["crisis de los 40"] },
  { url: "https://www.instagram.com/p/Ddl6EFKBjCd/", date: "2026-10-22", note: "A 11 de estos ejemplares me tocará luchar cuando los canguros quieran invadir Uruguay", tags: ["parcero","australia","canguros"] },
  { url: "https://www.instagram.com/p/DdaNppNAL98/", date: "2026-10-22", tags: ["los quiero mucho"] },
  { url: "https://www.instagram.com/p/Ddh5-oLAGQ-/", date: "2026-10-22", tags: ["los quiero mucho"] },

];
