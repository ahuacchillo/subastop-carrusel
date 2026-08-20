#!/usr/bin/env python3
"""Los PNG de un carrusel, en una URL publica que Meta pueda leer.

La Graph API no acepta que le subamos los bytes de una imagen: descarga cada
una desde una URL que le pasamos. Los renders viven en el disco de la instancia
que los hizo, que desde internet no existe, asi que publicar sin esto no es
dificil, es imposible.

Y sube JPEG, no PNG. Instagram solo publica JPEG: un PNG devuelve error. El
render sigue siendo PNG —es el que se ve en pantalla y el que viaja en el ZIP,
sin perdida— y la conversion pasa aca, en el unico sitio que necesita el otro
formato.

    python3 bucket.py 63015-toyota-yaris    # sube y escribe las URLs
    python3 bucket.py --self-check

El bucket se crea una vez con ./bucket-crear.sh.
"""
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

RAIZ = os.path.dirname(os.path.abspath(__file__))
POSTS = os.path.join(RAIZ, "Posts")
BUCKET = os.environ.get("BUCKET_CARRUSEL", "project-030f48f6-0f61-4e51-850-carrusel")


def token():
    """Un token de acceso, por el camino que haya.

    En Cloud Run lo da el servidor de metadatos. En una laptop lo da gcloud, que
    ya esta autenticado para desplegar. Ninguno de los dos deja una llave de
    servicio en el disco ni en el repo, que es justo la que se filtra.
    """
    try:
        pedido = urllib.request.Request(
            "http://metadata.google.internal/computeMetadata/v1/"
            "instance/service-accounts/default/token",
            headers={"Metadata-Flavor": "Google"})
        with urllib.request.urlopen(pedido, timeout=2) as r:
            return json.load(r)["access_token"]
    except Exception:  # noqa: BLE001 - fuera de Cloud Run no hay metadatos, y esta bien
        pass
    gcloud = os.environ.get("GCLOUD", os.path.expanduser("~/google-cloud-sdk/bin/gcloud"))
    r = subprocess.run([gcloud, "auth", "print-access-token"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("Sin token: no hay metadatos de Cloud Run, y gcloud no "
                           "esta autenticado.\n" + (r.stderr or "").strip()[-200:])
    return r.stdout.strip()


def publica(nombre):
    """La URL con la que la Graph API va a descargar el objeto."""
    return f"https://storage.googleapis.com/{BUCKET}/{urllib.parse.quote(nombre)}"


def jpeg(ruta):
    """El PNG del render, como JPEG, sin escribir nada en disco.

    ffmpeg y no una libreria de imagenes: ya esta instalado (lo usa el pipeline
    de los reels) y esto es una sola llamada. -q:v 2 es calidad alta; Instagram
    recomprime de todos modos, asi que apretar mas solo pierde el original.
    """
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", ruta, "-q:v", "2",
                        "-f", "mjpeg", "pipe:1"], capture_output=True)
    if r.returncode != 0 or not r.stdout:
        raise RuntimeError(f"ffmpeg no convirtio {os.path.basename(ruta)}: "
                           f"{r.stderr.decode('utf8', 'replace')[-200:]}")
    return r.stdout


def subir_uno(acceso, nombre, ruta):
    cuerpo = jpeg(ruta)
    pedido = urllib.request.Request(
        f"https://storage.googleapis.com/upload/storage/v1/b/{BUCKET}/o"
        f"?uploadType=media&name={urllib.parse.quote(nombre, safe='')}",
        data=cuerpo, method="POST", headers={
            "Authorization": "Bearer " + acceso,
            "Content-Type": "image/jpeg",
        })
    try:
        with urllib.request.urlopen(pedido, timeout=120) as r:
            json.load(r)
    except urllib.error.HTTPError as e:
        # El cuerpo del error de GCS dice exactamente que falta (el bucket, el
        # permiso, el proyecto). Sin leerlo solo queda un numero.
        raise RuntimeError(f"GCS {e.code} al subir {nombre}: "
                           f"{e.read().decode('utf8', 'replace')[:300]}") from None
    return publica(nombre)


def subir(slug, carpeta=None):
    """Sube los PNG del carrusel y devuelve sus URLs publicas, en orden.

    Un solo token para los cuatro: vale una hora y esto tarda segundos.

    El nombre del objeto es <slug>/<numero>.jpg, asi que volver a renderizar la
    misma subasta sobreescribe en lugar de acumular. Es lo que se quiere: lo
    ultimo que se vio en pantalla es lo que se publica.
    """
    carpeta = carpeta or os.path.join(POSTS, slug)
    pngs = sorted(f for f in os.listdir(carpeta) if f.lower().endswith(".png"))
    if not pngs:
        raise ValueError(f"No hay PNG en {carpeta}")
    acceso = token()
    return [subir_uno(acceso, f"{slug}/{os.path.splitext(p)[0]}.jpg",
                      os.path.join(carpeta, p)) for p in pngs]


def self_check():
    import tempfile
    global BUCKET
    BUCKET = "un-bucket"
    assert publica("63015-toyota-yaris/1.jpg") == \
        "https://storage.googleapis.com/un-bucket/63015-toyota-yaris/1.jpg"
    # El espacio de una foto propia no puede romper la URL que lee Meta.
    assert publica("a b/1.jpg") == "https://storage.googleapis.com/un-bucket/a%20b/1.jpg"

    d = tempfile.mkdtemp()
    try:
        subir("vacio", d)
    except ValueError:
        pass
    else:
        raise AssertionError("una carpeta sin PNG tiene que fallar antes de pedir token")

    # El orden importa: es el orden del carrusel, y la 1 es la portada.
    for n in ("10.png", "2.png", "1.png", "copy.md", "datos.json"):
        open(os.path.join(d, n), "w").close()
    subidos = []
    globals()["subir_uno"] = lambda a, nombre, ruta: subidos.append(nombre) or publica(nombre)
    globals()["token"] = lambda: "falso"
    urls = subir("x", d)
    # Sube JPEG aunque lea PNG: Instagram no publica PNG.
    assert subidos == ["x/1.jpg", "x/10.jpg", "x/2.jpg"], subidos
    assert urls[0].endswith("/x/1.jpg"), urls
    print("ok")


if __name__ == "__main__":
    if "--self-check" in sys.argv:
        self_check()
    elif len(sys.argv) > 1:
        print("\n".join(subir(sys.argv[1].strip("/").removeprefix("Posts/"))))
    else:
        sys.exit(__doc__)
