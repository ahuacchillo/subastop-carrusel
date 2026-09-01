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
import shutil
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
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime

import api
import bucket
import drive_fotos
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
# El CSS y el javascript de las dos estan en `web/`, no aca: ver `web()`.
HOJA = """<!doctype html><meta charset=utf8>
<title>{titulo} — Estudio VMC</title>
<link rel=stylesheet href="/web/base.css">
<link rel=stylesheet href="/web/{css}">
<header class=topbar>
 <span class=brand><b>Studio</b><span>VMC Subastas</span></span>
 {atras}
</header>
<main>
{cuerpo}
</main>
"""


def hoja(titulo, css, cuerpo, atras=True):
    """La hoja comun con lo propio de cada pagina adentro.

    Con replace y no con format: el HTML esta lleno de llaves. `atras=False`
    en las ofertas: ahi "Volver al estudio" apuntaria a la pagina en la que
    ya se esta parado, un boton sin funcion."""
    enlace = '<a class=back href="/">Volver al estudio</a>' if atras else ''
    return (HOJA.replace("{titulo}", titulo).replace("{css}", css)
            .replace("{atras}", enlace).replace("{cuerpo}", cuerpo))



AGENDA_HTML = hoja("Agenda", "agenda.css", """ <h1>Agenda</h1>
 <p class=sub>Lo publicado y lo que espera su hora. Un programado solo sale si
 algo corre <code>publicar.py --pendientes</code>.</p>
 <table>{filas}</table>""")





# Las ofertas abiertas, en tarjetas. Cada una es un enlace al estudio con su
# codigo: elegir la subasta es el primer paso del carrusel, y hasta ahora habia
# que ir a buscar el codigo a la web y volver a pegarlo.


def interes(tipo, n):
    """Live cuenta participantes; negociable, negociaciones. Y una es una."""
    if tipo == "vivo":
        return "participante" if n == 1 else "participantes"
    return "negociación" if n == 1 else "negociaciones"


# Los dos iconos que dibuja el servidor. Son del mismo trazo que los de `ICO`
# en web/ofertas.js: un ✓ de la fuente del sistema no es un icono, es lo que el
# sistema tenga ese dia.
_SVG = ('<svg class=ico viewBox="0 0 24 24" fill=none stroke=currentColor '
        'stroke-width=1.7 stroke-linecap=round stroke-linejoin=round '
        'aria-hidden=true>{}</svg>')
ICONO_CHECK = _SVG.format('<path d="M4.5 12.5l5 5 10-11"/>')
ICONO_FUERA = _SVG.format(
    '<path d="M14.5 4H20v5.5"/><path d="M20 4l-8.5 8.5"/>'
    '<path d="M18 14.5V19a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h4.5"/>')
# El reloj de "Cierra ...": el path exacto del TimerIcon de Concorde
# (voyager-ds), en su propio viewBox de 22 -- solo el trazo se baja a 1.7
# para calzar con el resto del set, que es mas fino que el 1.83 original.
ICONO_RELOJ = ('<svg class=ico viewBox="0 0 22 22" fill=none stroke=currentColor '
               'stroke-width=1.7 stroke-linecap=round stroke-linejoin=round '
               'aria-hidden=true><path d="M4.63973 10C5.09082 6.38255 8.17668 '
               '3.58333 11.9163 3.58333C15.9664 3.58333 19.2496 6.86658 19.2496 '
               '10.9167C19.2496 14.9668 15.9664 18.25 11.9163 18.25H7.33333'
               'M11.9167 10.9167V7.25M10.0833 1.75H13.75M2.75 12.75H7.33333'
               'M4.58333 15.5H9.16667"/></svg>')


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
WEB = os.path.join(RAIZ, "web")


def web(nombre):
    """Un archivo de `web/`, leido en cada pedido.

    El CSS y el javascript de las dos paginas que dibuja el servidor vivian
    dentro de strings de Python y eran la mitad de este archivo: ningun editor
    los coloreaba, ningun linter los miraba y editarlos era buscar y reemplazar
    dentro de una cadena. Ahora son .css y .js de verdad, y el servidor los lee
    del disco en cada pedido igual que `estudio.html` — recargar el navegador
    sigue siendo todo lo que hace falta para ver un cambio."""
    with open(os.path.join(WEB, seguro(nombre)), encoding="utf8") as f:
        return f.read()
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
        if ruta.startswith("/web/"):
            return self.archivo(os.path.join(WEB, seguro(ruta[5:])), WEB)
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
        def vacio(titulo, dice):
            return hoja("Ofertas", "ofertas.css",
                        " <h1>Ofertas</h1>\n"
                        f' <p class=vacio><b>{titulo}</b>{dice}</p>',
                        atras=False)

        try:
            grupos = api.ofertas()
        except Exception as e:  # noqa: BLE001 - la pagina lo dice, no el log
            return vacio("No se pudo leer la API",
                         f'{html.escape(str(e) or type(e).__name__)}. Recarga la '
                         f'página; si sigue igual, revisa la conexión.')
        if not grupos:
            return vacio("No hay subastas abiertas",
                         "Cuando vmcsubastas publique la próxima tanda, aparece "
                         "acá. Mientras tanto se puede reabrir un carrusel hecho "
                         "con <code>./estudio.sh &lt;slug&gt;</code>.")

        cuerpo, total = [], 0
        for g in grupos:
            tarjetas = []
            for o in g["ofertas"]:
                total += 1
                # En negociable la API manda null a proposito: no hay precio base.
                precio = (f'<span class=pre><s>US$</s>{o["precio"]:,.0f}</span>'
                          if o["precio"] else
                          '<span class="pre sin">Negociable</span>')
                anio = f'<i>{html.escape(o["anio"])}</i>' if o["anio"] else ""
                # "Hoy 06:02 pm" es lo unico de la tarjeta que cambia una
                # decision, asi que el "Hoy" se ve y el resto es dato.
                cierre = html.escape(o["cierre"])
                if cierre.startswith("Hoy"):
                    cierre = "<b>Hoy</b>" + cierre[3:]
                tarjetas.append(
                    f'<div class=card data-id="{o["id"]}" '
                    f'data-nombre="{html.escape(o["nombre"], quote=True)}" '
                    f'data-foto="{html.escape(o["foto"], quote=True)}">'
                    f'<label>'
                    f'<input type=checkbox value="{o["id"]}">'
                    f'<img src="{html.escape(o["foto"])}" alt="" decoding=async loading=lazy>'
                    f'<span class=tic>{ICONO_CHECK}</span>'
                    f'<span class=txt>'
                    f'<span class=nom>{html.escape(o["nombre"])}{anio}</span>'
                    f'{precio}'
                    f'<span class=cie>{ICONO_RELOJ}Cierra {cierre}</span>'
                    f'<span class=num><span class=vis>{o["vistas"]:,} '
                    f'{"vista" if o["vistas"] == 1 else "vistas"} · '
                    f'{o["interes"]} {interes(g["tipo"], o["interes"])}</span>'
                    f'<b class=cod>{o["id"]}</b></span>'
                    f'</span></label>'
                    f'<a class=abrir href="/estudio?oferta={o["id"]}">'
                    f'{ICONO_FUERA}Estudio</a>'
                    f'<span class=est></span>'
                    f'</div>')
            cuantas = len(g["ofertas"])
            cuerpo.append(
                f'<section class="grupo {g["tipo"]}">'
                f'<h2>{html.escape(g["fecha"])} '
                f'<span class=hora>{html.escape(g["hora"])}</span>'
                f'<span class=cuantas>{cuantas} '
                f'{"subasta" if cuantas == 1 else "subastas"}</span>'
                f'<b class=sello>{"en vivo" if g["tipo"] == "vivo" else "negociable"}'
                f'</b></h2>'
                f'<div class=rejilla>{"".join(tarjetas)}</div></section>')
        return hoja("Ofertas", "ofertas.css",
                    f" <h1>Ofertas</h1>\n"
                    f" <p class=sub>Las {total} subastas abiertas ahora mismo, "
                    f"directo de la API. Marca las que quieras y el lote hace "
                    f"los carruseles solo: elige las tres fotos mirándolas, "
                    f"renderiza y escribe el copy.</p>\n"
                    + "\n".join(cuerpo) + web("lote.html")
                    + '<script src="/web/ofertas.js" defer></script>',
                    atras=False)

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
                      "/publicar": self.publicar,
                      "/reencuadrar": self.reencuadrar,
                      "/galeria": self.galeria,
                      "/revisar-fotos": self.revisar_fotos}.get(self.path)
            if not accion:
                return self.responder(404, "text/plain", b"no existe")
            r = accion(cuerpo)
            r["ok"] = True
            self.json(r)
        except Exception as e:  # noqa: BLE001 - whatever fails is shown on the page
            self.json({"ok": False, "error": str(e) or type(e).__name__})

    def galeria(self, c):
        """Todas las fotos crudas ya bajadas de una oferta -- no solo las tres
        que el carrusel esta usando -- para elegir otra desde el editor."""
        codigo = seguro(str(c.get("codigo", "")))
        carpeta = os.path.join(MATERIALES, codigo)
        return {"fotos": [{"archivo": f, "url": f"/foto/{codigo}/{f}"}
                           for f in listar(carpeta)]}

    def revisar_fotos(self, c):
        """Chequeo liviano al marcar una oferta en la lista: si tiene placa,
        hay carpeta con fotos en Drive para ella. No descarga nada -- es un
        aviso antes de correr el lote, no el fetch real.

        Sin placa no hay nada que avisar: scraper.bajar() cae al sitio solo,
        sin tropezar. El aviso es solo para el caso que sí falla hoy: hay
        placa pero el socio todavia no subio las fotos a Drive."""
        codigo = seguro(str(c.get("codigo", "")))
        datos, _ = scraper.leer(codigo)
        placa = datos.get("PLACA", "")
        if not placa:
            return {"encontrada": True}
        access = drive_fotos.token()
        carpetas = drive_fotos.buscar_carpetas(access, placa)
        fotos = drive_fotos._juntar(drive_fotos.fotos_de(access, c) for c in carpetas)
        if not fotos:
            return {"encontrada": False, "motivo": f"placa {placa} sin fotos en Drive todavía"}
        return {"encontrada": True}

    def reencuadrar(self, c):
        """Ajusta foco/escala de un slide de un carrusel existente y
        re-renderiza. Con `origen` (un archivo de Materiales/<codigo>/) ademas
        cambia CUAL foto usa ese slide, no solo su encuadre."""
        slug = seguro(str(c.get("slug", "")))
        indice = int(c.get("indice", 0))
        foco = str(c.get("foco", "50% 50%"))
        escala = float(c.get("escala", 1.0))
        origen = seguro(str(c.get("origen", "")))

        datos_path = os.path.join(POSTS, slug, "datos.json")
        if not os.path.isfile(datos_path):
            raise ValueError(f"No existe datos.json para {slug}")

        with open(datos_path, "r", encoding="utf8") as f:
            d = json.load(f)

        fotos = d.get("fotos", [])
        if indice < 0 or indice >= len(fotos):
            raise ValueError(f"Índice de foto {indice} fuera de rango")

        f_actual = fotos[indice]
        src = f_actual if isinstance(f_actual, str) else f_actual.get("src", "")

        if origen:
            # El mismo prefijo/numero que ya usa nueva-subasta.sh, asi una
            # segunda vuelta de reencuadrar no deja huerfanos en public/autos.
            codigo = slug.split("-", 1)[0]
            ruta_origen = os.path.join(MATERIALES, codigo, origen)
            if not os.path.isfile(ruta_origen):
                raise ValueError(f"No existe la foto {origen} en Materiales/{codigo}")
            ext = os.path.splitext(origen)[1].lower() or ".jpeg"
            nombre = f"{slug}-{indice + 1}{ext}"
            os.makedirs(AUTOS, exist_ok=True)
            shutil.copyfile(ruta_origen, os.path.join(AUTOS, nombre))
            src = f"autos/{nombre}"

        if foco != "50% 50%" or escala != 1.0:
            fotos[indice] = {"src": src, "foco": foco, "escala": escala}
        else:
            fotos[indice] = src
        
        d["fotos"] = fotos
        with open(datos_path, "w", encoding="utf8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
            
        r = subprocess.run([os.path.join(RAIZ, "ajustar.sh"), slug, "--render"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError((r.stderr or r.stdout).strip()[-300:])
            
        pngs = sorted(f for f in os.listdir(os.path.join(POSTS, slug))
                      if f.endswith(".png"))
        import time as _t
        v = int(_t.time())
        return {
            "slug": slug,
            "slides": [f"/post/{slug}/{p}?v={v}" for p in pngs],
            "fotos": fotos,
            "indice": indice
        }

    def oferta(self, c):
        codigo = str(c.get("codigo", "")).strip().rstrip("/").rsplit("/", 1)[-1]
        if not codigo.isdigit():
            raise ValueError("Eso no parece un código de oferta ni un link.")
        datos, urls = scraper.leer(codigo)
        carpeta = os.path.join(MATERIALES, codigo)
        scraper.bajar(urls, carpeta, datos.get("PLACA", ""))
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
        # El slug es el mismo calculo que hace generar() por dentro: conocerlo
        # antes deja pedir el copy sin esperar a que generar() termine de
        # devolver algo.
        slug = slugificar(pedido["codigo"], pedido["datos"]["marca"],
                          pedido["datos"]["modelo"])
        peticion = {"codigo": pedido["codigo"], "datos": pedido["datos"],
                    "fotos": [{"archivo": f, "carpeta": pedido["carpeta"],
                               "foco": foco, "escala": 1}
                              for f, foco in zip(tres, focos)]}
        # El copy no necesita el render: generar() escribe datos.json antes de
        # llamar a Remotion, y generar_copy() no lee otra cosa. En fila eran
        # ~13s de render + ~3-4s de copy; a la vez, el mayor de los dos.
        with ThreadPoolExecutor(2) as pool:
            fut_render = pool.submit(self.generar, peticion)
            fut_copy = pool.submit(self.generar_copy,
                                    {"slug": slug, "siniestrado": chocado})
            hecho = fut_render.result()
            fut_copy.result()
        # El modal necesita los slides y el copy para mostrarlos en la misma
        # pantalla: sin ellos habria que abrir cada carrusel en el estudio.
        copy_path = os.path.join(POSTS, hecho["slug"], "copy.md")
        copy_text = ""
        if os.path.isfile(copy_path):
            with open(copy_path, encoding="utf8") as f:
                copy_text = f.read()
        return {"slug": hecho["slug"], "fotos": hecho.get("fotos", tres), "siniestrado": chocado,
                "slides": hecho["slides"], "copy": copy_text,
                "nombre": c.get("nombre", "")}

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
        return {"slug": slug, "slides": [f"/post/{slug}/{p}?v={v}" for p in pngs], "fotos": salida}

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
        # En el lote esto corre en paralelo con el render, no despues: generar()
        # escribe datos.json antes de arrancar Remotion, asi que la espera real
        # es de milisegundos salvo que el render haya fallado sin llegar a
        # escribirlo -- ahi el timeout entrega el mismo error de siempre.
        for _ in range(30):
            if os.path.isfile(ruta):
                break
            time.sleep(0.1)
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
