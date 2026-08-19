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
import http.server
import io
import json
import mimetypes
import os
import re
import subprocess
import sys
import threading
import unicodedata
import urllib.parse
import webbrowser
import zipfile

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

# Starting slug, set when reopening a finished carousel.
SLUG_INICIAL = sys.argv[1].strip("/").removeprefix("Posts/") if len(sys.argv) > 1 else ""


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
        if ruta == "/":
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
        if ruta.startswith("/descargar/"):
            return self.descargar(seguro(ruta.split("/", 2)[2]))
        self.responder(404, "text/plain", b"no existe")

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
        return {
            "slug": SLUG_INICIAL, "codigo": codigo,
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
                      "/generar": self.generar, "/copy": self.copy,
                      "/generar-copy": self.generar_copy}.get(self.path)
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
        return {
            "codigo": codigo, "carpeta": codigo,
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
        """Have Claude write the caption with the `copy-subastas-vmc` skill.

        It writes `copy.md` itself instead of printing it: asked for the text,
        it answers with the text plus a note about what it did, and that note
        ends up in the file. The file is the contract, so the parsing problem
        disappears.

        The §1 rule travels in the prompt on purpose. Without it the draft comes
        back with "ágil", "económico de mantener", "de ciudad" — attributes
        nobody gave it, which is the mistake the skill itself calls the most
        repeated one."""
        slug = seguro(c.get("slug", ""))
        ruta = os.path.join(POSTS, slug, "datos.json")
        if not os.path.isfile(ruta):
            raise ValueError("Ese carrusel no existe todavía.")
        with open(ruta, encoding="utf8") as f:
            d = json.load(f)
        anio = d.get("anio", "").strip("'")
        # Today's date travels too: the skill's urgency patterns say "HOY", and
        # with no way to tell it would say it about an auction five days out.
        from datetime import date
        prompt = f"""Usa la skill copy-subastas-vmc y escribe el copy de esta subasta de VMC.

Hoy es {date.today().strftime('%d/%m/%Y')}.

Datos (son TODO lo que hay):
- Marca y modelo: {d.get('marca', '')} {d.get('modelo', '')}
- Año: {'20' + anio if anio else ''}
- Transmisión: {d.get('transmision', '')}
- Vendedor: {d.get('tienda', '')}
- Precio base: {d.get('precioBase', '')}
- Subasta: {d.get('fecha', '')} a la(s) {d.get('hora', '')}

Reglas:
- §1 al pie: NO inventes atributos, estado, condición ni demanda de mercado.
- "HOY" solo si la subasta es hoy; si no, nombra el día que es.
- Sin dato de kilometraje ni de estado: no los menciones ni los insinúes.
- La ficha lleva solo las líneas cuyo dato exista, con los emojis estables de la skill.

Escribe el resultado en Posts/{slug}/copy.md con dos secciones, "## Instagram" y
"## WhatsApp", y nada más: ese archivo es el entregable, no lleva comentarios tuyos."""

        r = subprocess.run(
            ["claude", "-p", prompt, "--allowed-tools", "Skill", "Write",
             "--permission-mode", "acceptEdits"],
            cwd=RAIZ, capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            raise RuntimeError((r.stderr or r.stdout).strip()[-300:])
        return {}

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
