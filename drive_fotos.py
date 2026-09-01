#!/usr/bin/env python3
"""Baja las fotos de una placa desde el Drive de Socios Comerciales.

Como modulo (lo que usa scraper.py):
    import drive_fotos
    rutas = drive_fotos.bajar_placa("ABC123", "Materiales/63014")

Desde la terminal:
    python3 drive_fotos.py ABC123 Materiales/63014

Busca una carpeta con ese nombre en toda la unidad compartida (no hace falta
saber en que socio esta) y descarga ahi dentro todo lo que sea imagen.

Credenciales en ~/drive-clave.txt, tres lineas: client_id, client_secret,
refresh_token -- las deja drive_autorizar.py.
"""
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

# La carpeta de una placa vive dentro de "Socios Comerciales", pero anidada a
# distinta profundidad segun el socio -- a veces hasta duplicada dentro de si
# misma (ARB849/ARB849/*.jpg). Por eso no se navega el arbol: se busca el
# nombre en toda la unidad y se juntan las fotos de TODAS las carpetas que
# calcen, sin asumir cual es "la buena".
#
# corpora=drive exige ser miembro de la unidad compartida; sin el parametro,
# la busqueda por nombre igual encuentra lo que la cuenta puede ver.
API = "https://www.googleapis.com/drive/v3"

# El access token dura ~1h; cachearlo en el proceso evita un viaje a Google
# extra por cada oferta de un lote que corre varias seguidas en la misma
# instancia de Cloud Run.
_cache = {"token": None, "vence": 0}


def token():
    if _cache["token"] and time.time() < _cache["vence"]:
        return _cache["token"]

    # En Cloud Run vienen del entorno (desplegar.sh); en la maquina, del
    # archivo que deja drive_autorizar.py.
    client_id = os.environ.get("DRIVE_CLIENT_ID")
    client_secret = os.environ.get("DRIVE_CLIENT_SECRET")
    refresh = os.environ.get("DRIVE_REFRESH_TOKEN")
    try:
        if not (client_id and client_secret and refresh):
            client_id, client_secret, refresh = open(os.path.expanduser("~/drive-clave.txt")).read().split()
        data = urllib.parse.urlencode({
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh,
            "grant_type": "refresh_token",
        }).encode()
        with urllib.request.urlopen(urllib.request.Request("https://oauth2.googleapis.com/token", data=data)) as r:
            r = json.load(r)
    except FileNotFoundError as e:
        raise RuntimeError(
            "Faltan las credenciales de Drive -- correr drive_autorizar.py."
        ) from e
    except urllib.error.HTTPError as e:
        # invalid_grant es el token revocado o vencido -- ese si es un mensaje
        # accionable. Cualquier otro HTTPError (503, 500) es a Google, no a
        # nosotros: reintentar sirve, "corre drive_autorizar.py" no.
        if e.code == 400 and b"invalid_grant" in e.read():
            raise RuntimeError(
                "El token de Drive vencio o fue revocado -- correr drive_autorizar.py de nuevo."
            ) from e
        raise

    _cache["token"] = r["access_token"]
    _cache["vence"] = time.time() + r.get("expires_in", 3600) - 60  # margen de un minuto
    return _cache["token"]


def get(access, path, **params):
    # ponytail: estos dos flags o una unidad compartida devuelve vacio sin avisar
    params.setdefault("supportsAllDrives", "true")
    params.setdefault("includeItemsFromAllDrives", "true")
    url = f"{API}/{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {access}"})
    return urllib.request.urlopen(req)


def buscar_carpetas(access, placa):
    q = f"mimeType = 'application/vnd.google-apps.folder' and name contains '{placa}'"
    with get(access, "files", q=q, fields="files(id,name)") as r:
        return [c["id"] for c in json.load(r)["files"]]


def fotos_de(access, carpeta_id):
    q = f"'{carpeta_id}' in parents and mimeType contains 'image/'"
    with get(access, "files", q=q, fields="files(id,name,mimeType)") as r:
        return json.load(r)["files"]


def descargar(access, archivo, destino):
    ext = mimetypes.guess_extension(archivo["mimeType"]) or ".jpg"
    ruta = os.path.join(destino, archivo["name"] if "." in archivo["name"] else archivo["name"] + ext)
    with get(access, f"files/{archivo['id']}", alt="media") as r, open(ruta, "wb") as f:
        f.write(r.read())
    return ruta


def _juntar(fotos_por_carpeta):
    """Une las fotos de varias carpetas candidatas en una lista sin repetidos.

    Hace falta porque el nombre de una placa puede matchear mas de una
    carpeta (ARB849 vive duplicada dentro de si misma) y no todas tienen
    fotos -- juntar por id evita contar dos veces la que si las tiene."""
    vistas = {}
    for fotos in fotos_por_carpeta:
        for archivo in fotos:
            vistas[archivo["id"]] = archivo
    return list(vistas.values())


def bajar_placa(placa, destino):
    """Todas las fotos de una placa, bajadas a `destino`. Levanta LookupError
    si la placa no tiene carpeta o la carpeta esta vacia -- eso no deberia
    pasar nunca (las fotos se suben a Drive antes de publicar la oferta), asi
    que si pasa es un problema real y no algo para tapar con un fallback."""
    os.makedirs(destino, exist_ok=True)
    access = token()
    carpetas = buscar_carpetas(access, placa)
    if not carpetas:
        raise LookupError(f"No encontre ninguna carpeta con '{placa}' en el Drive.")

    # Casi siempre es 1 sola carpeta candidata; cuando son mas (ARB849 vive
    # duplicada dentro de si misma), listarlas en paralelo evita sumar sus
    # tiempos uno detras del otro.
    with ThreadPoolExecutor(8) as pool:
        fotos = _juntar(pool.map(lambda c: fotos_de(access, c), carpetas))
    if not fotos:
        raise LookupError(f"Ninguna carpeta de '{placa}' tiene fotos.")

    # En serie, 13 fotos son 13 viajes de red uno detras del otro -- lo mismo
    # que scraper.py ya evita para las del sitio.
    with ThreadPoolExecutor(8) as pool:
        return list(pool.map(lambda a: descargar(access, a, destino), fotos))


def _demo():
    a, b, c = {"id": "a"}, {"id": "b"}, {"id": "c"}
    # La carpeta duplicada (una vacia, otra con las fotos) es el caso real de
    # ARB849: no debe salir "b" dos veces ni perderse ninguna.
    assert _juntar([[a, b], [b, c]]) == [a, b, c], "b esta repetida entre las dos carpetas"
    assert _juntar([[], [a]]) == [a], "una carpeta vacia no debe tapar a la que si tiene fotos"
    assert _juntar([]) == [], "sin carpetas, sin fotos"
    print("ok")


def main():
    if "--demo" in sys.argv:
        return _demo()
    if len(sys.argv) != 3:
        sys.exit(f"Uso: {sys.argv[0]} <placa> <carpeta-destino> | --demo")
    try:
        for ruta in bajar_placa(sys.argv[1], sys.argv[2]):
            print(ruta)
    except (LookupError, RuntimeError) as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
