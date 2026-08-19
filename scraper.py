#!/usr/bin/env python3
"""
Read a vmcsubastas.com listing: the car's details and the gallery photos.

The page is server-rendered, so everything is in the HTML and no browser is
needed. What comes out are defaults: all of it can be corrected afterwards.
Neither the script nor the app treats the scrape as infallible.

As a module:
    import scraper
    datos, fotos = scraper.leer("62996")     # fotos = URLs, in gallery order
    scraper.bajar(fotos, "Materiales/62996") # saves them numbered

From the terminal (what `nueva-subasta.sh` uses):
    python3 scraper.py 62996 [target-folder]
Prints KEY<tab>VALUE per line, only for what it found, so the caller's own
default survives.
"""
import os
import re
import sys
import time
import urllib.request as U
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

CLAVES = ("MARCA", "MODELO", "ANIO", "TRANSMISION", "PRECIO", "TIENDA",
          "FECHA", "HORA")


def _bajar(url):
    return U.urlopen(
        U.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read()


def leer(oferta, intentos=3):
    """Returns (datos, fotos). `oferta` may be the code or the whole URL."""
    ident = str(oferta).rstrip("/").rsplit("/", 1)[-1]

    # Sometimes the site answers with its front page instead of the listing.
    # The tell is an empty gallery; retry before proceeding on invented data.
    for intento in range(intentos):
        html = _bajar(f"https://www.vmcsubastas.com/oferta/{ident}").decode(
            "utf8", "replace")
        # The carousel is 3 slides, so only the first few matter here.
        fotos = list(dict.fromkeys(
            re.findall(r'\\"image\\":\\"(https://[^\\]+?\.jpe?g)', html)))[:8]
        if fotos:
            break
        time.sleep(2)
    else:
        raise LookupError(f"La oferta {ident} no trajo fotos. "
                          "¿El código es correcto?")

    def uno(patron):
        m = re.search(patron, html, re.S)
        return m.group(1).strip() if m else ""

    # "Toyota Fortuner 2023" -> make / model / 23'
    titulo = uno(r"<h1[^>]*>([^<]+)</h1>").split()
    anio = titulo.pop() if titulo and titulo[-1].isdigit() else ""
    datos = {
        "MARCA": titulo[0] if titulo else "",
        "MODELO": " ".join(titulo[1:]),
        "ANIO": anio[2:] + "'" if anio else "",
        "TRANSMISION": uno(r"Transmisión.{0,80}?<span[^>]*>([^<]+)</span>"),
        # From the payload, not the painted HTML: on closed or negotiable
        # listings the price card is never rendered.
        "PRECIO": uno(r'basePriceLabel\\":\\"US\$\s*([\d.,]+)'),
        "TIENDA": uno(r"Vendedor:\s*([^<]+)<"),
    }
    cuando = uno(r'processDatetime\\":\\"([^\\]+)')
    if cuando:
        d = datetime.strptime(cuando, "%Y-%m-%d %H:%M:%S")
        datos["FECHA"] = d.strftime("%d/%m")
        datos["HORA"] = d.strftime("%I:%M %p").lstrip("0").lower()
    return datos, fotos


def bajar(fotos, destino):
    """Save the photos numbered. Gallery order matters, so the numbering keeps
    a later `sort` from scrambling it. Photos already on disk are not
    downloaded again. Returns the paths."""
    os.makedirs(destino, exist_ok=True)
    rutas = [os.path.join(destino, f"{i:02d}.jpeg")
             for i in range(1, len(fotos) + 1)]

    def guardar(par):
        ruta, url = par
        if not os.path.exists(ruta):
            with open(ruta, "wb") as f:
                f.write(_bajar(url))

    with ThreadPoolExecutor(8) as pool:
        list(pool.map(guardar, zip(rutas, fotos)))
    return rutas


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Uso: scraper.py <código-o-URL> [carpeta-destino]")
    ident = sys.argv[1]
    print(f"Leyendo oferta {ident}…", file=sys.stderr)
    try:
        datos, fotos = leer(ident)
    except LookupError as e:
        sys.exit(str(e))

    if len(sys.argv) > 2:
        destino = sys.argv[2]
        # The terminal carousel takes 3; the app pulls more and picks later.
        bajar(fotos[:3], destino)
        print(f"{len(fotos[:3])} fotos en {destino}/", file=sys.stderr)

    # Anything not found is not printed, so the caller's default survives.
    for clave in CLAVES:
        if datos.get(clave):
            print(f"{clave}\t{datos[clave]}")
