/* Otros proyectos: para sumar uno nuevo, agregá un objeto a esta lista.
   { icon: emoji, title: nombre, text: línea corta, url: dirección (relativa o completa) } */
window.PROYECTOS = [
  { icon: "📺", title: "Guía de TV", text: "Mi programación, privada con clave", url: "/guia/" }
];

(function () {
  var box = document.getElementById("proyectos-list");
  if (!box || !window.PROYECTOS || !PROYECTOS.length) { var s = document.getElementById("proyectos"); if (s) s.hidden = true; return; }
  PROYECTOS.forEach(function (p) {
    var a = document.createElement("a");
    a.className = "social project";
    a.href = p.url;
    if (/^https?:/.test(p.url) && p.url.indexOf(location.host) < 0) { a.target = "_blank"; a.rel = "noopener"; }
    var ico = document.createElement("span"); ico.className = "ico"; ico.setAttribute("aria-hidden", "true"); ico.textContent = p.icon || "✨";
    var txt = document.createElement("span"); txt.className = "p-txt";
    var t = document.createElement("strong"); t.textContent = p.title;
    var d = document.createElement("small"); d.textContent = p.text || "";
    txt.appendChild(t); txt.appendChild(d);
    a.appendChild(ico); a.appendChild(txt);
    box.appendChild(a);
  });
})();
