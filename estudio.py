#!/usr/bin/env python3
"""
Studio: from a listing code to publishable PNGs, without touching a terminal.

    ./estudio.sh                   # start a new carousel
    ./estudio.sh 62915-dfsk-glory  # reopen a finished one, to reframe it

Everything on one page: paste the listing, check the details, pick the photos
and their order, frame them. It then renders and shows the four slides.

Same pipeline as always: `scraper.py` for the details and `ajustar.sh --render`
for the PNGs. This page renders nothing of its own, so it cannot drift away
from what the terminal produces.

A stdlib server: nothing is installed and, by default, nothing leaves the
machine. It binds 127.0.0.1 unless told otherwise, so no phone or other
computer can reach it — see ESTUDIO_HOST below for the container.
"""
import base64
import hmac
import html
import http.server
import io
import json
import mimetypes
import os
import re
import subprocess
import sys
import threading
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
import zipfile
from datetime import date, datetime

import api
import bucket
import elegir
import publicar as publicar_mod
import scraper

RAIZ = os.path.dirname(os.path.abspath(__file__))
MATERIALES = os.path.join(RAIZ, "Materiales")
POSTS = os.path.join(RAIZ, "Posts")
AUTOS = os.path.join(RAIZ, "remotion", "public", "autos")
EXTS = (".png", ".jpg", ".jpeg")

# Desktop by default; the container overrides all three.
#
# CLAVE is what makes the difference between "on my machine" and "on the
# internet". Unset, the page is open — which is correct on 127.0.0.1, where
# only this machine can knock. Set, every request has to carry it: the server
# writes files and shells out to a renderer, so exposing it without a lock
# would hand both to whoever finds the URL.
HOST = os.environ.get("ESTUDIO_HOST", "127.0.0.1")
PUERTO = int(os.environ.get("PORT") or os.environ.get("ESTUDIO_PUERTO") or 4173)
CLAVE = os.environ.get("ESTUDIO_CLAVE", "")

# Who writes the caption: with a key in the environment, a direct call to the
# model's API; without it, the Claude CLI reading the skill. Both land in the
# same `copy.md`, so the page cannot tell them apart.
DEEPSEEK = os.environ.get("DEEPSEEK_API_KEY", "")
SKILL = os.path.join(RAIZ, ".claude", "skills",
                     "vmc-ig-copy-ficha-tecnica", "SKILL.md")

# Starting slug, set when reopening a finished carousel.
SLUG_INICIAL = sys.argv[1].strip("/").removeprefix("Posts/") if len(sys.argv) > 1 else ""


# La agenda, en su propia pagina y sin javascript, pero con la misma hoja que
# el estudio: barra, superficies, insignias y tipografia. Es la otra vista del
# mismo producto, y cruzar el enlace no puede sentirse como salir de el.
# Las dos paginas que el servidor dibuja —la agenda y las ofertas— comparten
# hoja con estudio.html: barra, superficies, insignias y tipografia. Cruzar un
# enlace no puede sentirse como salir del producto. Los tokens siguen siendo una
# copia de los de estudio.html y tienen que moverse con ella; lo que no puede
# haber es una tercera copia, que fue como esta pagina habia derivado sola.
HOJA = """<!doctype html><meta charset=utf8>
<title>{titulo} — Estudio VMC</title>
<style>
 /* Los tokens son una copia de estudio.html y tienen que moverse con ella: son
    dos documentos, no dos productos. Antes esta pagina habia derivado sola —su
    --violet era el --violet-2 del estudio— y se notaba al cruzar el enlace. */
 @font-face{font-family:Jakarta;src:url(/fuente) format("woff2");font-display:swap}
 :root{color-scheme:dark;
       --bg:#0E0B14;--ink:#EDE9F5;--ink-2:#9A90B4;
       --violet:#8460E5;--violet-2:#AE8EFF;
       --green:#4ADE9B;--red:#F87171;--orange:#ED8936;
       --sheet:rgba(13,9,21,.78);--raise:rgba(38,29,56,.58);
       --raise-2:rgba(52,40,76,.74);
       --edge:rgba(255,255,255,.11);--edge-2:rgba(255,255,255,.20);
       --frost:saturate(155%) blur(20px);
       --lift:0 18px 44px -18px rgba(0,0,0,.9);
       --scroll:rgba(174,142,255,.20);--scroll-2:rgba(174,142,255,.40)}
 *{box-sizing:border-box;margin:0;scrollbar-width:thin;
   scrollbar-color:var(--scroll) transparent}
 body{min-height:100vh;color:var(--ink);
      font:400 15px/1.55 Jakarta,system-ui,sans-serif;-webkit-font-smoothing:antialiased;
      background:
        radial-gradient(560px 760px at 3% 22%,rgba(132,96,229,.30),transparent 70%),
        radial-gradient(520px 720px at 99% 30%,rgba(174,142,255,.22),transparent 70%),
        radial-gradient(620px 420px at 8% 102%,rgba(174,142,255,.12),transparent 70%),
        var(--bg)}
 ::selection{background:var(--violet);color:#fff}
 :focus-visible{outline:2px solid var(--violet-2);outline-offset:2px;border-radius:8px}

 /* La misma barra que el estudio: cruzar el enlace no puede sentirse como
    salir del producto. Antes se aterrizaba en una pagina desnuda y el camino
    de vuelta era un enlace suelto al final de un parrafo, partido en dos
    lineas. */
 .topbar{display:flex;align-items:center;gap:16px;padding:12px 20px;
         border-bottom:1px solid var(--edge);background:var(--sheet);
         backdrop-filter:var(--frost);-webkit-backdrop-filter:var(--frost);
         box-shadow:inset 0 1px 0 var(--edge-2),0 12px 32px -24px #000}
 .brand{display:flex;align-items:baseline;gap:8px}
 .brand b{font-weight:800;font-size:20px;letter-spacing:-.03em;
          background:linear-gradient(100deg,var(--ink) 18%,var(--violet-2));
          -webkit-background-clip:text;background-clip:text;color:transparent}
 .brand span{color:var(--ink-2);font-size:13px}
 .back{margin-inline-start:auto;display:inline-flex;align-items:center;gap:6px;
       padding:9px 16px;border:1px solid var(--edge);border-radius:8px;
       background:var(--raise);box-shadow:inset 0 1px 0 var(--edge-2);
       backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);
       font:600 15px Jakarta,system-ui,sans-serif;color:var(--ink);
       text-decoration:none;transition:background .15s,border-color .15s}
 .back:hover{background:var(--raise-2);border-color:var(--edge-2)}

 main{max-width:860px;margin:0 auto;padding:40px 24px 64px}
 h1{font-size:26px;font-weight:800;letter-spacing:-.02em;margin:0 0 6px}
 p.sub{color:var(--ink-2);margin:0 0 24px;font-size:13.5px;max-width:62ch}
 code{font:500 12.5px ui-monospace,SFMono-Regular,Menlo,monospace;
      padding:2px 6px;border-radius:6px;background:var(--raise);
      border:1px solid var(--edge);color:var(--ink);white-space:nowrap}

{estilo}
</style>
<header class=topbar>
 <span class=brand><b>Studio</b><span>VMC Subastas</span></span>
 <a class=back href="/">Volver al estudio</a>
</header>
<main>
{cuerpo}
</main>
"""


def hoja(titulo, estilo, cuerpo):
    """La hoja comun con lo propio de cada pagina adentro.

    Con replace y no con format: el CSS esta lleno de llaves."""
    return (HOJA.replace("{titulo}", titulo).replace("{estilo}", estilo)
            .replace("{cuerpo}", cuerpo))


ESTILO_AGENDA = """
 /* Panel sobre mesa iluminada, la misma profundidad que las slides del
    estudio. Antes era un bloque plano que no se distinguia del fondo. */
 table{width:100%;border-collapse:collapse;background:var(--sheet);
       border:1px solid var(--edge);border-radius:16px;overflow:hidden;
       box-shadow:var(--lift);
       backdrop-filter:var(--frost);-webkit-backdrop-filter:var(--frost)}
 td{padding:13px 16px;border-top:1px solid var(--edge);vertical-align:middle}
 tr:first-child td{border-top:0}
 tr:hover td{background:rgba(255,255,255,.022)}
 td.h{font-variant-numeric:tabular-nums;color:var(--ink-2);white-space:nowrap;
      font-size:13.5px;width:1%}
 td.s{font-weight:600}
 td.n{color:var(--ink-2);font-size:13.5px}
 td.n a{color:var(--green);text-decoration:underline;text-underline-offset:3px}
 td.n a:hover{color:var(--ink)}

 /* La insignia de estado habla el mismo idioma que el contador de la barra del
    estudio: pildora con canto propio y brillo arriba, no una palabra suelta. */
 td b{display:inline-grid;place-items:center;min-width:19px;height:21px;
   padding:0 9px;border-radius:11px;
   font-weight:800;font-size:11px;letter-spacing:.06em;text-transform:uppercase;
   background:var(--raise-2);border:1px solid var(--edge-2);
   box-shadow:inset 0 1px 0 var(--edge-2);color:var(--ink-2)}
 tr.publicado b{color:var(--green);border-color:rgba(74,222,155,.34)}
 tr.programado b{color:var(--violet-2);border-color:rgba(174,142,255,.40)}
 tr.atrasado b{color:var(--orange);border-color:rgba(237,137,54,.42)}
 tr.error b{color:var(--red);border-color:rgba(248,113,113,.42)}"""

AGENDA_HTML = hoja("Agenda", ESTILO_AGENDA, """ <h1>Agenda</h1>
 <p class=sub>Lo publicado y lo que espera su hora. Un programado solo sale si
 algo corre <code>publicar.py --pendientes</code>.</p>
 <table>{filas}</table>""")


# El lote: una oferta por peticion, dos peticiones en vuelo.
#
# Cada subasta tarda cerca de un minuto, y medido en esta maquina ese minuto es
# casi todo espera de red: el modelo que mira las ocho fotos son 35 s, el que
# escribe el copy unos 20 s, y el render son 7 s de CPU. En fila, esos 55 s de
# espera no hacen nada.
#
# Dos en vuelo los solapan y los renders se serializan solos: el servidor es un
# ThreadingHTTPServer y en Cloud Run `--concurrency 8` con 2 GiB aguanta dos
# Chromium (el pico medido de uno es 704 MiB). Cuatro no —ni de memoria ni de
# CPU—, y ademas cuatro tarjetas cambiando de estado a la vez no se leen. Dos es
# el numero que sale de la memoria del contenedor, no una preferencia: esta en
# `EN_VUELO` para poder bajarlo a 1 sin tocar nada mas.
LOTE_JS = """
<div class=barra id=barra hidden>
 <b id=cuenta></b>
 <span class=paso id=paso></span>
 <button class=limpiar type=button id=limpiar>Quitar la selección</button>
 <button type=button id=hacer>Hacer los carruseles</button>
 <a id=zip hidden download>Descargar el ZIP</a>
</div>
<script>
const $ = (id) => document.getElementById(id);
const marcadas = () => [...document.querySelectorAll('.card input:checked')]
                       .map(i => i.closest('.card'));

function contar() {
  const n = marcadas().length;
  $('cuenta').textContent = n === 1 ? '1 subasta elegida'
                                    : n + ' subastas elegidas';
  $('barra').hidden = n === 0;
  $('hacer').disabled = n === 0;
}
document.addEventListener('change', e => {
  if (e.target.matches('.card input')) contar();
});

$('limpiar').onclick = () => {
  document.querySelectorAll('.card input:checked').forEach(i => {
    i.checked = false;
    // El estado se va con la seleccion: una tarjeta en verde de una tanda
    // anterior mentiria sobre lo que se acaba de hacer.
    i.closest('.card').removeAttribute('data-est');
  });
  $('paso').textContent = ''; $('zip').hidden = true; contar();
};

function estado(card, est, texto) {
  card.dataset.est = est;
  card.querySelector('.est').textContent = texto;
}

const EN_VUELO = 2;

$('hacer').onclick = async () => {
  const cards = marcadas();
  if (!cards.length) return;
  $('hacer').disabled = true; $('limpiar').disabled = true; $('zip').hidden = true;
  $('hacer').textContent = 'Haciendo los carruseles…';

  // Por indice y no con push: con dos en vuelo terminan desordenadas, y el ZIP
  // tiene que salir en el orden en que estan en pantalla.
  const slugs = new Array(cards.length).fill(null);
  let siguiente = 0, cerradas = 0;

  const trabajador = async () => {
    while (siguiente < cards.length) {
      const i = siguiente++;
      const card = cards[i];
      estado(card, 'haciendo', 'haciendo el carrusel…');
      card.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      try {
        const r = await fetch('/lote', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ codigo: card.dataset.id }) });
        const j = await r.json();
        if (!j.ok) throw new Error(j.error || 'falló');
        slugs[i] = j.slug;
        estado(card, 'listo', j.slug);
      } catch (err) {
        // Una que falla no detiene el lote: lo normal es que sea una negociable
        // sin precio base, y las otras nueve no tienen la culpa.
        estado(card, 'error', err.message);
      }
      // Cuantas cerraron, no cual va: con dos en vuelo "3 de 10" no señala nada.
      cerradas++;
      $('paso').textContent = `${cerradas} de ${cards.length}`;
    }
  };
  await Promise.all(Array.from({ length: Math.min(EN_VUELO, cards.length) },
                               trabajador));

  const hechos = slugs.filter(Boolean);
  $('paso').textContent = hechos.length
    ? `${hechos.length} de ${cards.length} listos`
    : 'ninguno salió';
  if (hechos.length) {
    $('zip').href = '/descargar-lote?slugs=' + encodeURIComponent(hechos.join(','));
    $('zip').hidden = false;
  }
  $('hacer').disabled = false; $('limpiar').disabled = false;
  $('hacer').textContent = 'Hacer los carruseles';
};

contar();
</script>"""


# Las ofertas abiertas, en tarjetas. Cada una es un enlace al estudio con su
# codigo: elegir la subasta es el primer paso del carrusel, y hasta ahora habia
# que ir a buscar el codigo a la web y volver a pegarlo.
ESTILO_OFERTAS = """
 /* La hoja comun mide 860px, que es el ancho de la tabla de la agenda. Una
    rejilla de 61 tarjetas necesita mas, y solo esta pagina lo necesita. */
 main{max-width:1160px}
 .grupo{margin:0 0 34px}
 .grupo h2{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;
           font-size:15px;font-weight:700;letter-spacing:-.01em;margin:0 0 14px;
           padding-bottom:10px;border-bottom:1px solid var(--edge)}
 .grupo h2 span{color:var(--ink-2);font-weight:500;font-size:13px}
 .grupo h2 b{margin-inline-start:auto;padding:2px 9px;border-radius:11px;
             font-size:11px;font-weight:800;letter-spacing:.06em;
             text-transform:uppercase;background:var(--raise-2);
             border:1px solid var(--edge-2);box-shadow:inset 0 1px 0 var(--edge-2)}
 .grupo.vivo h2 b{color:var(--orange);border-color:rgba(237,137,54,.42)}
 .grupo.negociable h2 b{color:var(--violet-2);border-color:rgba(174,142,255,.40)}

 .rejilla{display:grid;gap:14px;
          grid-template-columns:repeat(auto-fill,minmax(214px,1fr))}
 .card{position:relative;display:flex;flex-direction:column;color:inherit;
       background:var(--sheet);border:1px solid var(--edge);border-radius:14px;
       overflow:hidden;box-shadow:var(--lift);
       backdrop-filter:var(--frost);-webkit-backdrop-filter:var(--frost);
       transition:border-color .15s,transform .15s}
 .card:hover{border-color:var(--violet);transform:translateY(-2px)}
 /* Elegida: el canto violeta y la marca arriba a la izquierda. El checkbox no
    se ve; la tarjeta entera es el control. */
 .card:has(input:checked){border-color:var(--violet-2);
   box-shadow:var(--lift),0 0 0 1px var(--violet-2) inset}
 .card label{display:block;cursor:pointer}
 .card input{position:absolute;opacity:0;pointer-events:none}
 .card .tic{position:absolute;top:9px;left:9px;width:22px;height:22px;
   border-radius:7px;border:1px solid var(--edge-2);background:rgba(8,5,14,.66);
   backdrop-filter:blur(6px);display:grid;place-items:center;
   font:800 12px Jakarta,sans-serif;color:transparent}
 .card:has(input:checked) .tic{background:var(--violet);border-color:var(--violet-2);
   color:#fff}
 .card:has(input:checked) .tic::after{content:"✓"}
 /* El camino de siempre sigue estando: una oferta a mano, en el estudio. */
 .card .abrir{position:absolute;top:9px;right:9px;padding:4px 9px;border-radius:8px;
   border:1px solid var(--edge-2);background:rgba(8,5,14,.66);
   backdrop-filter:blur(6px);font:600 11px Jakarta,sans-serif;
   color:var(--ink-2);text-decoration:none;opacity:0;transition:opacity .15s}
 .card:hover .abrir,.card .abrir:focus{opacity:1}
 .card .abrir:hover{color:var(--ink);border-color:var(--violet)}
 /* El estado del lote tapa la foto: es lo unico que importa mientras corre. */
 .card .est{position:absolute;inset:0 0 auto;padding:7px 11px;font-size:11.5px;
   font-weight:600;background:rgba(8,5,14,.82);backdrop-filter:blur(8px);
   border-bottom:1px solid var(--edge);display:none}
 .card[data-est] .est{display:block}
 .card[data-est="haciendo"] .est{color:var(--violet-2)}
 .card[data-est="listo"] .est{color:var(--green)}
 .card[data-est="error"] .est{color:var(--red);white-space:normal}
 .card[data-est="haciendo"]{border-color:var(--violet-2)}
 .card[data-est="listo"]{border-color:rgba(74,222,155,.45)}
 .card[data-est="error"]{border-color:rgba(248,113,113,.45)}

 /* La barra del lote: aparece con la primera elegida y no se va al hacer
    scroll — con 60 tarjetas, un boton al final de la pagina no existe. */
 .barra{position:sticky;bottom:0;z-index:5;margin:26px 0 0;
   display:flex;align-items:center;gap:14px;flex-wrap:wrap;
   padding:13px 18px;border:1px solid var(--edge);border-radius:14px;
   background:var(--sheet);box-shadow:var(--lift);
   backdrop-filter:var(--frost);-webkit-backdrop-filter:var(--frost)}
 .barra[hidden]{display:none}
 .barra b{font-size:14px}
 .barra .paso{color:var(--ink-2);font-size:13px;flex:1 1 auto;min-width:10ch}
 .barra button,.barra a{padding:9px 17px;border-radius:9px;
   font:700 13px Jakarta,system-ui,sans-serif;cursor:pointer;text-decoration:none}
 .barra button{border:1px solid var(--violet-2);background:var(--violet);color:#fff}
 .barra button:disabled{opacity:.5;cursor:default}
 .barra a{border:1px solid rgba(74,222,155,.45);color:var(--green);
   background:rgba(74,222,155,.10)}
 .barra a[hidden]{display:none}
 .barra .limpiar{border:1px solid var(--edge);background:transparent;
   color:var(--ink-2);font-weight:600}
 /* La foto es la del CDN y llega en 800x600 con marca de agua a veces: aca
    solo se elige la subasta, el encuadre se hace despues en el estudio. */
 .card img{width:100%;aspect-ratio:4/3;object-fit:cover;display:block;
           background:var(--raise)}
 .card .txt{display:flex;flex-direction:column;gap:3px;padding:11px 13px 13px}
 .card .nom{font-weight:700;font-size:14px;line-height:1.3;
            display:flex;gap:6px;align-items:baseline}
 .card .nom i{font-style:normal;color:var(--ink-2);font-weight:500;font-size:12.5px;
              font-variant-numeric:tabular-nums}
 .card .pre{font-weight:800;font-size:15px;color:var(--green);
            font-variant-numeric:tabular-nums}
 .card .pre.sin{color:var(--ink-2);font-weight:600;font-size:13px}
 .card .cie{font-size:12px;color:var(--ink-2);font-variant-numeric:tabular-nums}
 .card .num{display:flex;align-items:baseline;gap:8px;
            font-size:11.5px;color:var(--ink-2);opacity:.8;
            font-variant-numeric:tabular-nums}
 .card .cod{margin-inline-start:auto;font:500 11px ui-monospace,Menlo,monospace;
            color:var(--ink-2)}
 .vacio{padding:22px;border:1px dashed var(--edge-2);border-radius:14px;
        color:var(--ink-2)}"""



def cierre_de_subasta(fecha, hora, hoy):
    """The ⏰ line, written here instead of left to the model: asked to compare
    with today it announced "La subasta es HOY 14 de agosto" for an auction six
    days gone. `datos.json` carries a bare "14/08", so the year is this one.

    >>> from datetime import date
    >>> cierre_de_subasta("14/08", "1:05 pm", date(2026, 8, 14))
    '⏰ La subasta es HOY 14 de agosto a la 1:05 p.m.'
    >>> cierre_de_subasta("26/08", "10:20 am", date(2026, 8, 20))
    '⏰ Cierre de subasta: Miércoles 26 de agosto | 10:20 a.m.'
    >>> cierre_de_subasta("el jueves", "temprano", date(2026, 8, 20))
    '⏰ Cierre de subasta: el jueves | temprano'
    """
    hora = hora.replace(" pm", " p.m.").replace(" am", " a.m.")
    try:
        f = datetime.strptime(f"{fecha}/{hoy.year}", "%d/%m/%Y").date()
    except ValueError:
        return f"⏰ Cierre de subasta: {fecha} | {hora}"  # a hand-typed date
    mes = ("enero febrero marzo abril mayo junio julio agosto septiembre "
           "octubre noviembre diciembre".split()[f.month - 1])
    if f == hoy:
        # "a la 1:15", "a las 10:20": the hour is always 1-something in
        # practice, but the plural costs one conditional and reads right.
        return (f"⏰ La subasta es HOY {f.day} de {mes} "
                f"a la{'' if hora.startswith('1:') else 's'} {hora}")
    dia = ("Lunes Martes Miércoles Jueves Viernes Sábado Domingo"
           .split()[f.weekday()])
    return f"⏰ Cierre de subasta: {dia} {f.day} de {mes} | {hora}"


def deepseek(sistema, mensaje):
    """One call to DeepSeek, which speaks the OpenAI shape. `urllib` is enough:
    no SDK, so the project stays with no dependencies."""
    cuerpo = json.dumps({
        "model": "deepseek-chat",
        "messages": [{"role": "system", "content": sistema},
                     {"role": "user", "content": mensaje}],
    }).encode()
    pedido = urllib.request.Request(
        "https://api.deepseek.com/chat/completions", data=cuerpo,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {DEEPSEEK}"})
    try:
        with urllib.request.urlopen(pedido, timeout=180) as r:
            texto = json.load(r)["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e:  # the body says what the status hides
        raise RuntimeError(f"DeepSeek {e.code}: {e.read().decode()[:300]}") from None
    # It hands the answer back inside a fence often enough to strip it here.
    if texto.startswith("```"):
        texto = texto.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    return texto


def seguro(nombre):
    """A file name with no path in it. Nothing arriving from the browser gets
    to choose which folder is written to."""
    return os.path.basename(nombre).replace("\x00", "")


def slugificar(*partes):
    """Same slug as `nueva-subasta.sh`: code-make-model."""
    crudo = "-".join(str(p) for p in partes)
    plano = unicodedata.normalize("NFKD", crudo).encode("ascii", "ignore").decode()
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]", "-", plano.lower())).strip("-")


def listar(carpeta):
    if not os.path.isdir(carpeta):
        return []
    return sorted(f for f in os.listdir(carpeta) if f.lower().endswith(EXTS))


def normalizar(f):
    if isinstance(f, str):
        return {"src": f, "foco": "50% 50%", "escala": 1}
    return {"src": f["src"], "foco": f.get("foco", "50% 50%"),
            "escala": f.get("escala", 1)}


PAGINA = os.path.join(RAIZ, "estudio.html")
FUENTE = os.path.join(RAIZ, "remotion", "public", "brand",
                      "plus-jakarta-sans.woff2")


class Handler(http.server.BaseHTTPRequestHandler):
    # HTTP/1.1 so the browser reuses the connection. With 1.0 it opens one per
    # photo, runs out of pool around the tenth thumbnail, and the rest hang
    # forever. Every response sends Content-Length, which is what 1.1 needs in
    # order to reuse a connection.
    protocol_version = "HTTP/1.1"

    def log_message(self, *_):
        pass

    def responder(self, codigo, tipo, cuerpo, extra=None):
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        for clave, valor in (extra or {}).items():
            self.send_header(clave, valor)
        self.end_headers()
        self.wfile.write(cuerpo)

    def json(self, obj):
        self.responder(200, "application/json",
                       json.dumps(obj, ensure_ascii=False).encode())

    def autorizado(self):
        """Basic auth, and only when CLAVE is set — on 127.0.0.1 there is
        nobody to authenticate against. The user name is ignored: this locks
        one tool for one person, it does not keep accounts."""
        if not CLAVE:
            return True
        cabecera = self.headers.get("Authorization", "")
        if cabecera.startswith("Basic "):
            try:
                pareja = base64.b64decode(cabecera[6:]).decode("utf8", "replace")
            except Exception:  # noqa: BLE001 - malformed header is just a failure
                pareja = ""
            # compare_digest and not ==: a plain comparison gives the password
            # away one character at a time to anyone who can time the answers.
            if hmac.compare_digest(pareja.split(":", 1)[-1], CLAVE):
                return True
        # Drain the body before answering. With keep-alive, an unread POST body
        # is read as the next request line and the connection derails.
        largo = int(self.headers.get("Content-Length", 0) or 0)
        if largo:
            self.rfile.read(largo)
        self.responder(401, "text/plain", "Hace falta la clave.".encode(),
                       {"WWW-Authenticate": 'Basic realm="Estudio VMC"'})
        return False

    def archivo(self, ruta, base):
        """Serve a file, always from inside `base`."""
        ruta = os.path.abspath(ruta)
        if not ruta.startswith(os.path.abspath(base) + os.sep) or not os.path.isfile(ruta):
            return self.responder(404, "text/plain", b"no existe")
        tipo = mimetypes.guess_type(ruta)[0] or "application/octet-stream"
        with open(ruta, "rb") as f:
            self.responder(200, tipo, f.read())

    # ── GET ──────────────────────────────────────────────────────────────────
    def do_GET(self):
        if not self.autorizado():
            return
        # unquote: WhatsApp file names carry spaces and the browser sends them
        # as %20. Without this the thumbnail comes out broken.
        ruta = urllib.parse.unquote(self.path.split("?")[0])
        # La entrada es la lista de subastas: lo primero es elegir cual, y
        # hasta ahora habia que ir a buscar el codigo a la web y pegarlo.
        # Reabrir un carrusel hecho (`./estudio.sh <slug>`) sigue entrando
        # derecho al estudio: ahi la subasta ya esta elegida.
        if ruta == "/":
            if not SLUG_INICIAL:
                return self.responder(200, "text/html; charset=utf8",
                                      self.ofertas().encode("utf8"))
            return self.responder(302, "text/plain", b"", {"Location": "/estudio"})
        if ruta in ("/estudio", "/ofertas"):
            if ruta == "/ofertas":               # el enlace viejo, a su sitio
                return self.responder(302, "text/plain", b"", {"Location": "/"})
            # From disk rather than a constant: reloading the browser is all
            # it takes to see a page change, with no restart.
            with open(PAGINA, "rb") as f:
                return self.responder(200, "text/html; charset=utf8", f.read())
        if ruta == "/fuente":
            return self.archivo(FUENTE, os.path.dirname(FUENTE))
        if ruta == "/inicio":
            return self.json(self.inicio())
        if ruta.startswith("/foto/"):
            _, _, carpeta, archivo = ruta.split("/", 3)
            return self.archivo(
                os.path.join(MATERIALES, seguro(carpeta), seguro(archivo)), MATERIALES)
        if ruta.startswith("/auto/"):
            # Photos already copied into a finished carousel.
            return self.archivo(
                os.path.join(AUTOS, seguro(ruta.split("/", 2)[2])), AUTOS)
        if ruta.startswith("/post/"):
            _, _, slug, archivo = ruta.split("/", 3)
            return self.archivo(
                os.path.join(POSTS, seguro(slug), seguro(archivo)), POSTS)
        if ruta == "/cuenta":
            ahora = time.time()
            filas = publicar_mod.leer()
            return self.json({
                "esperando": sum(1 for f in filas if f["estado"] == "programado"),
                "atrasados": sum(1 for f in filas if f["estado"] == "programado"
                                 and f["cuando"] < ahora - 300),
                "fallidos": sum(1 for f in filas if f["estado"] == "error")})
        if ruta == "/agenda":
            return self.responder(200, "text/html; charset=utf8",
                                  self.agenda().encode("utf8"))
        if ruta == "/descargar-lote":
            pedido = urllib.parse.parse_qs(
                urllib.parse.urlparse(self.path).query).get("slugs", [""])[0]
            return self.descargar_lote([seguro(x) for x in pedido.split(",") if x])
        if ruta.startswith("/descargar/"):
            return self.descargar(seguro(ruta.split("/", 2)[2]))
        self.responder(404, "text/plain", b"no existe")

    def agenda(self):
        """Lo publicado y lo que espera, en una pagina sin javascript.

        Se dibuja en el servidor porque la agenda es un archivo del servidor: sin
        fetch, sin estado en el navegador, y recargar es la unica forma de que
        este al dia — que para una lista que cambia cuatro veces al dia alcanza.
        """
        ahora = time.time()
        filas = list(reversed(publicar_mod.leer()))
        cuerpo = []
        for f in filas:
            estado = f["estado"]
            # Programado y con la hora pasada no es programado: es que nadie
            # corrio --pendientes. Decirlo aca es lo unico que evita descubrirlo
            # tres dias despues, cuando el post no salio.
            if estado == "programado" and f["cuando"] < ahora - 300:
                estado, nota = "atrasado", ("nadie corrio --pendientes; "
                                            "revisa el cron")
            else:
                nota = f["error"] or ""
            enlace = (f'<a href="{html.escape(f["permalink"])}" target="_blank" '
                      f'rel="noopener">ver el post</a>' if f["permalink"] else "")
            cuerpo.append(
                f'<tr class="{estado}"><td class="h">{publicar_mod.cuando_dice(f["cuando"])}</td>'
                f'<td><b>{estado}</b></td><td class="s">{html.escape(f["slug"])}</td>'
                f'<td class="n">{enlace}{html.escape(nota)}</td></tr>')
        if not cuerpo:
            cuerpo = ['<tr><td colspan="4" class="n">Nada publicado ni programado '
                      'todavia.</td></tr>']
        return AGENDA_HTML.replace("{filas}", "\n".join(cuerpo))

    def ofertas(self):
        """Las subastas abiertas, traidas de la API, para elegir varias.

        Es la pagina de entrada. Se marcan las que van a salir esta semana y un
        boton las hace todas: baja las fotos, un modelo elige las tres, se
        renderiza y se escribe el copy. El estudio queda para la correccion a
        mano, a un clic de cada tarjeta.

        El HTML lo dibuja el servidor —la lista cambia cuando cierra una subasta
        y recargar es la unica forma de estar al dia— y el javascript es solo el
        lote: elegir es un checkbox, que no necesita ninguno.
        """
        try:
            grupos = api.ofertas()
        except Exception as e:  # noqa: BLE001 - la pagina lo dice, no el log
            return hoja("Ofertas", ESTILO_OFERTAS,
                        " <h1>Ofertas</h1>\n"
                        f' <p class=vacio>No se pudo leer la API: '
                        f'{html.escape(str(e) or type(e).__name__)}</p>')

        cuerpo, total = [], 0
        for g in grupos:
            tarjetas = []
            for o in g["ofertas"]:
                total += 1
                # En negociable la API manda null a proposito: no hay precio base.
                precio = (f'<span class=pre>US$ {o["precio"]:,.0f}</span>'
                          if o["precio"] else
                          '<span class="pre sin">Negociable</span>')
                anio = f'<i>{html.escape(o["anio"])}</i>' if o["anio"] else ""
                tarjetas.append(
                    f'<div class=card data-id="{o["id"]}" '
                    f'data-nombre="{html.escape(o["nombre"], quote=True)}">'
                    f'<label>'
                    f'<input type=checkbox value="{o["id"]}">'
                    f'<img src="{html.escape(o["foto"])}" alt="" decoding=async>'
                    f'<span class=tic></span>'
                    f'<span class=txt>'
                    f'<span class=nom>{html.escape(o["nombre"])}{anio}</span>'
                    f'{precio}'
                    f'<span class=cie>Cierra {html.escape(o["cierre"])}</span>'
                    f'<span class=num>{o["vistas"]} vistas · {o["interes"]} '
                    f'{"participantes" if g["tipo"] == "vivo" else "negociaciones"}'
                    f'<b class=cod>{o["id"]}</b></span>'
                    f'</span></label>'
                    f'<a class=abrir href="/estudio?oferta={o["id"]}">Estudio</a>'
                    f'<span class=est></span>'
                    f'</div>')
            cuerpo.append(
                f'<section class="grupo {g["tipo"]}">'
                f'<h2>{html.escape(g["fecha"])} <span>{html.escape(g["hora"])}</span>'
                f'<b>{"en vivo" if g["tipo"] == "vivo" else "negociable"}</b></h2>'
                f'<div class=rejilla>{"".join(tarjetas)}</div></section>')
        return hoja("Ofertas", ESTILO_OFERTAS,
                    f" <h1>Ofertas</h1>\n"
                    f" <p class=sub>Las {total} subastas abiertas ahora mismo, "
                    f"directo de la API. Marca las que quieras y el lote hace "
                    f"los carruseles solo: elige las tres fotos mirándolas, "
                    f"renderiza y escribe el copy.</p>\n"
                    + "\n".join(cuerpo) + LOTE_JS)

    def descargar(self, slug):
        """The whole carousel as one ZIP, built in memory: four downloads in a
        row is four trips to the file manager, and a temp file would be one
        more thing to clean up."""
        carpeta = os.path.join(POSTS, slug)
        pngs = [f for f in listar(carpeta) if f.lower().endswith(".png")]
        if not pngs:
            return self.responder(404, "text/plain", b"no existe")
        buf = io.BytesIO()
        # Stored, not deflated: PNG is already compressed, so deflate spends
        # CPU to save nothing.
        with zipfile.ZipFile(buf, "w") as z:
            for p in pngs:                       # listar() sorts: 1, 2, 3, 4
                z.write(os.path.join(carpeta, p), p)
            texto = os.path.join(carpeta, "copy.md")
            if os.path.isfile(texto):            # the post, not just the images
                z.write(texto, "copy.md")
        self.responder(200, "application/zip", buf.getvalue(),
                       {"Content-Disposition": f'attachment; filename="{slug}.zip"'})

    def inicio(self):
        """State for reopening a finished carousel. Empty without an argument."""
        if not SLUG_INICIAL:
            return {"slug": ""}
        datos_json = os.path.join(POSTS, SLUG_INICIAL, "datos.json")
        if not os.path.isfile(datos_json):
            return {"slug": ""}
        d = json.load(open(datos_json, encoding="utf8"))
        codigo = SLUG_INICIAL.split("-")[0]
        codigo = codigo if codigo.isdigit() else ""

        # The photos actually used are the ones copied into public/autos, so
        # they are offered from there and not from Materiales: they are the
        # only ones that map exactly onto the saved framing. Guessing by
        # position pins the framing to the wrong photo the moment the order
        # was not 1-2-3.
        fotos, elegidas, ajustes = [], [], {}
        for f in (normalizar(x) for x in d["fotos"]):
            archivo = os.path.basename(f["src"])
            url = f"/auto/{archivo}"
            fotos.append({"archivo": archivo, "carpeta": "", "url": url})
            elegidas.append(url)
            ajustes[url] = {"foco": f["foco"], "escala": f["escala"]}

        # Plus the original folder, so a photo can still be swapped out.
        carpeta = codigo if os.path.isdir(os.path.join(MATERIALES, codigo)) else ""
        fotos += [{"archivo": f, "carpeta": carpeta, "url": f"/foto/{carpeta}/{f}"}
                  for f in listar(os.path.join(MATERIALES, carpeta))] if carpeta else []
        # Los renders que ya existen, para que la pestana del carrusel muestre el
        # carrusel y no una pantalla vacia. Sin esto, reabrir ofrece publicar algo
        # que no esta a la vista.
        slides = [f"/post/{SLUG_INICIAL}/{f}"
                  for f in listar(os.path.join(POSTS, SLUG_INICIAL))
                  if f.lower().endswith(".png")]
        return {
            "slug": SLUG_INICIAL, "codigo": codigo, "slides": slides,
            "fotos": fotos, "elegidas": elegidas, "ajustes": ajustes,
            "datos": {
                "marca": d.get("marca", ""), "modelo": d.get("modelo", ""),
                "anio": d.get("anio", ""), "transmision": d.get("transmision", ""),
                "precio": d.get("precioBase", "").replace("US$", "").strip(),
                "fecha": d.get("fecha", ""), "hora": d.get("hora", ""),
                "tienda": d.get("tienda", ""),
            },
        }

    # ── POST ─────────────────────────────────────────────────────────────────
    def do_POST(self):
        if not self.autorizado():
            return
        try:
            largo = int(self.headers.get("Content-Length", 0))
            cuerpo = json.loads(self.rfile.read(largo) or b"{}")
            accion = {"/oferta": self.oferta, "/subir": self.subir,
                      "/lote": self.lote,
                      "/generar": self.generar, "/copy": self.copy,
                      "/generar-copy": self.generar_copy,
                      "/publicar": self.publicar}.get(self.path)
            if not accion:
                return self.responder(404, "text/plain", b"no existe")
            r = accion(cuerpo)
            r["ok"] = True
            self.json(r)
        except Exception as e:  # noqa: BLE001 - whatever fails is shown on the page
            self.json({"ok": False, "error": str(e) or type(e).__name__})

    def oferta(self, c):
        codigo = str(c.get("codigo", "")).strip().rstrip("/").rsplit("/", 1)[-1]
        if not codigo.isdigit():
            raise ValueError("Eso no parece un código de oferta ni un link.")
        datos, urls = scraper.leer(codigo)
        carpeta = os.path.join(MATERIALES, codigo)
        scraper.bajar(urls, carpeta)
        # Lo que el scraper no encontro y la pagina rellena con un valor por
        # defecto. En el estudio eso es comodidad —el campo se ve y se corrige—;
        # en el lote seria publicar "Mecánica" sobre una caja automatica.
        return {
            "codigo": codigo, "carpeta": codigo,
            "faltan": [k for k in ("ANIO", "TRANSMISION") if not datos.get(k)],
            "fotos": [{"archivo": f, "carpeta": codigo,
                       "url": f"/foto/{codigo}/{f}"}
                      for f in listar(carpeta)],
            "datos": {
                "marca": datos.get("MARCA", ""), "modelo": datos.get("MODELO", ""),
                "anio": datos.get("ANIO", "") or "25'",
                "transmision": datos.get("TRANSMISION", "") or "Mecánica",
                "precio": datos.get("PRECIO", ""), "fecha": datos.get("FECHA", ""),
                "hora": datos.get("HORA", ""), "tienda": datos.get("TIENDA", ""),
            },
        }

    def lote(self, c):
        """Una subasta entera, de codigo a carrusel con copy, sin tocar nada.

        No hay ni un paso nuevo: es `oferta` + `generar` + `generar_copy`, los
        tres que ya usa la pagina del estudio, con el unico agregado de que las
        tres fotos las elige un modelo mirandolas en vez de una persona. Si
        alguno se cae, se cae este pedido y no la fila entera: la tarjeta lo
        dice y el lote sigue con la siguiente.
        """
        pedido = self.oferta(c)                     # datos + fotos, en 800x600
        if pedido["faltan"]:
            raise ValueError("la web no dio " + " ni ".join(
                x.lower() for x in pedido["faltan"]) + "; ábrela en el estudio")
        carpeta = os.path.join(MATERIALES, pedido["carpeta"])
        # Portada de frente, interior o lateral, y la trasera con la placa. Y el
        # foco de cada una: la foto es 4:3 y el slide 1:1, asi que `cover`
        # recorta los lados, y centrado a ciegas le cortaba la cabina a una
        # camioneta que en la foto estaba corrida a la izquierda. Lo mide quien
        # ya esta mirando las ocho fotos.
        tres, chocado, focos = elegir.mirar(carpeta)
        hecho = self.generar({
            "codigo": pedido["codigo"], "datos": pedido["datos"],
            "fotos": [{"archivo": f, "carpeta": pedido["carpeta"],
                       "foco": foco, "escala": 1}
                      for f, foco in zip(tres, focos)]})
        # El caption despues del render: se escribe desde el datos.json que
        # acaba de dejar `generar`, que es la unica fuente de esos ocho datos.
        self.generar_copy({"slug": hecho["slug"], "siniestrado": chocado})
        return {"slug": hecho["slug"], "fotos": tres, "siniestrado": chocado}

    def descargar_lote(self, slugs):
        """Los carruseles de una tanda en un solo ZIP, cada uno en su carpeta.

        Uno por uno son cuatro PNG y un copy.md por subasta, todos con el mismo
        nombre: sin carpeta dentro del ZIP, diez subastas son cuarenta archivos
        llamados `1.png`.
        """
        buf = io.BytesIO()
        adentro = 0
        # Almacenado y no comprimido: el PNG ya viene comprimido y deflate
        # gastaria CPU para no ahorrar nada.
        with zipfile.ZipFile(buf, "w") as z:
            for slug in slugs:
                carpeta = os.path.join(POSTS, slug)
                for archivo in listar(carpeta):   # listar() ordena: 1, 2, 3, 4
                    if archivo.lower().endswith(".png"):
                        z.write(os.path.join(carpeta, archivo), f"{slug}/{archivo}")
                        adentro += 1
                # El copy va con sus slides: publicar es pegar las dos cosas, y
                # `listar` solo devuelve imagenes.
                texto = os.path.join(carpeta, "copy.md")
                if os.path.isfile(texto):
                    z.write(texto, f"{slug}/copy.md")
        if not adentro:
            return self.responder(404, "text/plain", b"no existe")
        self.responder(200, "application/zip", buf.getvalue(),
                       {"Content-Disposition": 'attachment; filename="carruseles.zip"'})

    def subir(self, c):
        # With no code the photos get their own folder, so they never mix with
        # a listing they do not belong to.
        carpeta = seguro(str(c.get("codigo") or "").strip()) or "subidas"
        destino = os.path.join(MATERIALES, carpeta)
        os.makedirs(destino, exist_ok=True)
        nombre = seguro(c["nombre"])
        if not nombre.lower().endswith(EXTS):
            raise ValueError(f"{nombre}: solo PNG o JPG.")
        with open(os.path.join(destino, nombre), "wb") as f:
            f.write(base64.b64decode(c["datos"]))
        return {"foto": {"archivo": nombre, "carpeta": carpeta,
                         "url": f"/foto/{carpeta}/{nombre}"}}

    def generar(self, c):
        d, fotos = c["datos"], c["fotos"]
        if not fotos:
            raise ValueError("No hay fotos elegidas.")
        faltan = [k for k in ("marca", "modelo", "anio", "transmision", "precio",
                              "fecha", "hora", "tienda") if not d.get(k, "").strip()]
        if faltan:
            raise ValueError("Faltan datos: " + ", ".join(faltan))

        slug = slugificar(c.get("codigo", ""), d["marca"], d["modelo"])
        os.makedirs(AUTOS, exist_ok=True)
        os.makedirs(os.path.join(POSTS, slug), exist_ok=True)

        # Read EVERYTHING before writing anything: when a carousel is reopened
        # the source and the destination are the same folder, and reordering
        # would overwrite a photo that has not been read yet.
        crudo = []
        for f in fotos:
            archivo, carpeta = seguro(f["archivo"]), seguro(f.get("carpeta") or "")
            base = os.path.join(MATERIALES, carpeta) if carpeta else AUTOS
            with open(os.path.join(base, archivo), "rb") as a:
                crudo.append((os.path.splitext(archivo)[1].lower(), a.read()))

        # Stable names prefixed by the slug, same as the script, so two
        # auctions cannot collide inside public/.
        salida = []
        for n, (f, (ext, contenido)) in enumerate(zip(fotos, crudo), 1):
            with open(os.path.join(AUTOS, f"{slug}-{n}{ext}"), "wb") as b:
                b.write(contenido)
            entrada = {"src": f"autos/{slug}-{n}{ext}"}
            if f.get("foco", "50% 50%") != "50% 50%" or float(f.get("escala", 1)) != 1:
                entrada.update(foco=f["foco"], escala=float(f["escala"]))
                salida.append(entrada)
            else:
                salida.append(entrada["src"])

        with open(os.path.join(POSTS, slug, "datos.json"), "w", encoding="utf8") as f:
            json.dump({
                "marca": d["marca"], "modelo": d["modelo"], "anio": d["anio"],
                "transmision": d["transmision"], "precioBase": "US$ " + d["precio"],
                "fecha": d["fecha"], "hora": d["hora"], "tienda": d["tienda"],
                "fotos": salida,
            }, f, ensure_ascii=False, indent=2)

        r = subprocess.run([os.path.join(RAIZ, "ajustar.sh"), slug, "--render"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError((r.stderr or r.stdout).strip()[-300:])
        print(f"  ✓ Posts/{slug}/", flush=True)
        pngs = sorted(f for f in os.listdir(os.path.join(POSTS, slug))
                      if f.endswith(".png"))
        # The ?v= keeps the browser from serving the previous render from cache.
        import time as _t
        v = int(_t.time())
        return {"slug": slug, "slides": [f"/post/{slug}/{p}?v={v}" for p in pngs]}

    def generar_copy(self, c):
        """Write the caption with the `vmc-ig-copy-ficha-tecnica` skill.

        Two ways in, same file out. With DEEPSEEK_API_KEY the skill travels as
        the system prompt and the answer is written here. Without it, the Claude
        CLI writes `copy.md` itself instead of printing it: asked for the text,
        it answers with the text plus a note about what it did, and that note
        ends up in the file. The file is the contract, so the parsing problem
        disappears.

        The no-invented-data rule travels in the prompt on purpose: DeepSeek
        reading the skill alone fills the gap with mileage and a body style
        nobody gave it, the mistake the skill calls its own worst. Adjectives in
        the hook are a different thing and they are welcome — that part is what
        the skill actually asks to be written."""
        slug = seguro(c.get("slug", ""))
        ruta = os.path.join(POSTS, slug, "datos.json")
        if not os.path.isfile(ruta):
            raise ValueError("Ese carrusel no existe todavía.")
        with open(ruta, encoding="utf8") as f:
            d = json.load(f)
        anio = d.get("anio", "").strip("'")
        cierre = cierre_de_subasta(d.get("fecha", ""), d.get("hora", ""),
                                   date.today())
        # The WhatsApp opener is derived from that same line and never written
        # again: the skill's template for the channel has "¡HOY [FECHA]!" baked
        # in, and the model copied the HOY into a Wednesday six days out.
        apertura = "⏰ ¡" + cierre.split(" ", 1)[1] + "! 🚨"
        estado = ("SINIESTRADA (unidad chocada o recuperada)"
                  if c.get("siniestrado") else "en buen estado")
        datos = f"""Datos (son TODO lo que hay):
- Marca y modelo: {d.get('marca', '')} {d.get('modelo', '')}
- Año: {'20' + anio if anio else ''}
- Transmisión: {d.get('transmision', '')}
- Vendedor: {d.get('tienda', '')}
- Precio base: {d.get('precioBase', '')}
- Condición: {estado}

La línea de cierre de subasta va LITERAL, esta y sin recalcular nada:

{cierre}

Y la apertura de la versión de WhatsApp va LITERAL, esta, aunque la plantilla de
la skill diga HOY: si la línea no lo dice, no es hoy.

{apertura}

Reglas:
- No inventes DATOS: nada de kilometraje, combustible, tracción, color ni
  dueños anteriores. Si no está en la lista de arriba, no existe. Ese hueco es
  a propósito: es lo que obliga a entrar a vmcsubastas.com.
- El gancho sí vende un beneficio, con el ángulo que la unidad sostenga: es el
  trabajo creativo y sale de la librería de ángulos de la skill.
- La condición de arriba manda el ángulo. Siniestrada va por rentabilidad de
  reacondicionar, y no se esconde. En buen estado nunca se insinúa chocada.
- Instagram en texto plano: sin negritas, cursivas ni markdown, que los muestra
  como asteriscos. WhatsApp sí lleva negritas, con un solo asterisco (*texto*).
- Sin pie de firma: nada de "link en BIO" ni "SUBASTOP S.A.C. / RUC"."""
        entrega = """
Dos secciones y nada más: un encabezado "## Instagram" y un encabezado
"## WhatsApp", cada uno con su copy debajo. No pongas los rótulos "Versión
para..." de la skill, que los encabezados ya dicen cuál es cuál."""

        if DEEPSEEK:
            with open(SKILL, encoding="utf8") as f:
                receta = f.read()
            texto = deepseek(receta, f"""{datos}
{entrega}
Esa respuesta es el entregable, no lleva comentarios tuyos.""")
            with open(os.path.join(POSTS, slug, "copy.md"), "w", encoding="utf8") as f:
                f.write(texto + "\n")
            return {}

        r = subprocess.run(
            ["claude", "-p", f"""Usa la skill vmc-ig-copy-ficha-tecnica y escribe el copy de esta subasta de VMC.

{datos}
{entrega}

Escribe el resultado en Posts/{slug}/copy.md: ese archivo es el entregable, no
lleva comentarios tuyos.""",
             "--allowed-tools", "Skill", "Write",
             "--permission-mode", "acceptEdits"],
            cwd=RAIZ, capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            raise RuntimeError((r.stderr or r.stdout).strip()[-300:])
        return {}

    def publicar(self, c):
        """Sube al bucket y publica, o lo deja programado a una hora.

        Publicar ya y programar son la misma cosa con distinta hora, asi que
        comparten camino, archivo y pantalla: una sola cola, un solo registro.

        La subida al bucket pasa aca y no a la hora de publicar. El disco de la
        instancia no sobrevive a un reinicio, y un post programado para el jueves
        no puede depender de que sigan existiendo los PNG del martes.
        """
        slug = seguro(str(c.get("slug", "")))
        carpeta = os.path.join(POSTS, slug)
        if not os.path.isdir(carpeta):
            raise ValueError("Ese carrusel no existe todavía.")
        texto = publicar_mod.caption(c.get("texto", ""))
        if not texto:
            raise ValueError("Falta el caption: sin él el post sale mudo.")
        # El caption se guarda igual que con el botón de guardar. El archivo es
        # la fuente de verdad, y lo que se publica tiene que quedar en el ZIP.
        with open(os.path.join(carpeta, "copy.md"), "w", encoding="utf8") as f:
            f.write(c.get("texto", ""))
        urls = bucket.subir(slug, carpeta)
        cuando = c.get("cuando")
        fila = (publicar_mod.programar(slug, texto, urls, float(cuando)) if cuando
                else publicar_mod.ahora(slug, texto, urls))
        if fila["estado"] == "error":
            raise RuntimeError(fila["error"])
        return {"estado": fila["estado"], "permalink": fila["permalink"],
                "cuando": publicar_mod.cuando_dice(fila["cuando"])}

    def copy(self, c):
        """Save the caption next to the slides. Whoever wrote it —a person, or
        Claude reading the skill, or one day an API— it lands in the same file,
        and it travels in the ZIP with the images."""
        carpeta = os.path.join(POSTS, seguro(c.get("slug", "")))
        if not os.path.isdir(carpeta):
            raise ValueError("Ese carrusel no existe todavía.")
        with open(os.path.join(carpeta, "copy.md"), "w", encoding="utf8") as f:
            f.write(c.get("texto", ""))
        return {}


if __name__ == "__main__":
    servidor = http.server.ThreadingHTTPServer((HOST, PUERTO), Handler)
    local = HOST in ("127.0.0.1", "localhost")
    url = f"http://{'127.0.0.1' if local else HOST}:{PUERTO}/"
    print(f"Estudio → {url}")
    if not local and not CLAVE:
        print("  ⚠ Sin ESTUDIO_CLAVE y escuchando fuera de 127.0.0.1: "
              "cualquiera que llegue a esta URL puede usarlo.", flush=True)
    # Only on the desktop. In a container there is no browser to open, and the
    # attempt hangs looking for one.
    if local:
        print("Ctrl-C para cerrar.", flush=True)
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print()
