#!/usr/bin/env python3
"""Publica un carrusel en Instagram, ahora o a una hora.

    python3 publicar.py --ahora 63015-toyota-yaris
    python3 publicar.py --programar 63015-toyota-yaris "2026-08-22 18:30"
    python3 publicar.py --pendientes     # lo que ya toca. Esto es lo que va en cron.
    python3 publicar.py --agenda         # que hay publicado y que espera
    python3 publicar.py --self-check

Instagram no programa. Su API publica en el momento, y sus contenedores caducan
en 24 horas, asi que la cola tiene que ser nuestra y los contenedores se crean
recien a la hora de publicar. "Programar" solo escribe una linea en agenda.json:
publicar de verdad lo hace quien corra --pendientes.

Hace falta IG_TOKEN en el entorno, con el permiso instagram_business_content_publish.
El token lo emite authorize.py de ../../ig-comentarios, que es la misma app de Meta.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

import bucket

RAIZ = os.path.dirname(os.path.abspath(__file__))
POSTS = os.path.join(RAIZ, "Posts")
AGENDA = os.path.join(RAIZ, "agenda.json")

BASE = os.environ.get("IG_API_BASE", "https://graph.instagram.com/v23.0")

# Topes de Instagram, no nuestros: un carrusel lleva de 2 a 10 piezas y el
# caption corta a los 2200 caracteres.
MIN_SLIDES, MAX_SLIDES, MAX_CAPTION = 2, 10, 2200

# El bucket borra sus objetos a los 30 dias. Programar mas lejos que eso
# publicaria un post cuyas imagenes ya no existen, asi que se corta antes.
TOPE_DIAS = 21


def token():
    t = os.environ.get("IG_TOKEN", "").strip()
    if not t:
        raise RuntimeError("Falta IG_TOKEN en el entorno. Lo emite authorize.py "
                           "de ig-comentarios, y necesita el permiso "
                           "instagram_business_content_publish.")
    return t


def graph(ruta, **params):
    params["access_token"] = token()
    url = f"{BASE}/{ruta}?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)


def graph_post(ruta, **datos):
    datos["access_token"] = token()
    pedido = urllib.request.Request(f"{BASE}/{ruta}",
                                    data=urllib.parse.urlencode(datos).encode())
    try:
        with urllib.request.urlopen(pedido, timeout=120) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        # El cuerpo del error de Meta dice que falta —el permiso, el formato de
        # la imagen, la URL que no pudo descargar—. El codigo suelto no dice nada.
        cuerpo = e.read().decode("utf8", "replace")
        try:
            mensaje = json.loads(cuerpo)["error"]["message"]
        except Exception:  # noqa: BLE001 - si no es el JSON de siempre, va crudo
            mensaje = cuerpo[:300]
        raise RuntimeError(f"Instagram: {mensaje}") from None


def mi_id():
    """El id de la cuenta. Publicar cuelga de el, no de /me."""
    d = graph("me", fields="user_id,username")
    return str(d.get("user_id") or d["id"])


def caption(texto):
    """Solo la seccion de Instagram del copy.

    copy.md lleva el post del feed y el de WhatsApp, uno debajo del otro bajo su
    encabezado. Publicar el archivo entero mandaria el texto de WhatsApp y los
    titulos "## Instagram" dentro del caption.
    """
    lineas, dentro, salida = texto.splitlines(), False, []
    for linea in lineas:
        if linea.startswith("## "):
            dentro = linea.strip().lower() == "## instagram"
            continue
        if dentro:
            salida.append(linea)
    if not dentro and not salida:      # sin encabezados, es todo el caption
        return texto.strip()
    return "\n".join(salida).strip()


def publicar(urls, texto):
    """Las tres llamadas de Meta: un contenedor por imagen, uno de carrusel con
    los hijos, y publicar ese. Devuelve el id del post y su enlace."""
    if not MIN_SLIDES <= len(urls) <= MAX_SLIDES:
        raise ValueError(f"Un carrusel lleva entre {MIN_SLIDES} y {MAX_SLIDES} "
                         f"imagenes, y hay {len(urls)}.")
    if len(texto) > MAX_CAPTION:
        raise ValueError(f"El caption tiene {len(texto)} caracteres y el tope "
                         f"de Instagram son {MAX_CAPTION}.")
    ig = mi_id()
    hijos = [graph_post(f"{ig}/media", image_url=u, is_carousel_item="true")["id"]
             for u in urls]
    padre = graph_post(f"{ig}/media", media_type="CAROUSEL",
                       children=",".join(hijos), caption=texto)["id"]
    post = graph_post(f"{ig}/media_publish", creation_id=padre)["id"]
    try:
        enlace = graph(post, fields="permalink").get("permalink", "")
    except Exception:  # noqa: BLE001 - ya esta publicado; el enlace es un adorno
        enlace = ""
    return post, enlace


# ── la agenda ───────────────────────────────────────────────────────────────

def leer():
    if not os.path.exists(AGENDA):
        return []
    with open(AGENDA, encoding="utf8") as f:
        return json.load(f)


def escribir(filas):
    # Escritura atomica: un corte a mitad dejaria la agenda truncada, y ahi
    # viven los posts que todavia no salieron.
    tmp = AGENDA + ".tmp"
    with open(tmp, "w", encoding="utf8") as f:
        json.dump(filas, f, ensure_ascii=False, indent=1)
    os.replace(tmp, AGENDA)


def nueva(slug, texto, urls, cuando=None):
    ahora = time.time()
    cuando = float(cuando or ahora)
    if cuando > ahora + TOPE_DIAS * 86400:
        raise ValueError(f"No se programa a mas de {TOPE_DIAS} dias: las imagenes "
                         "del bucket se borran antes de que llegue la hora.")
    return {"slug": slug, "caption": texto, "urls": urls, "cuando": cuando,
            "creado": ahora, "estado": "programado",
            "post": "", "permalink": "", "error": ""}


def guardar(fila):
    """Escribe la fila en la agenda.

    Solo puede quedar un programado por subasta: lo ultimo que se dijo es lo que
    vale, y dos filas pendientes del mismo carrusel publicarian el mismo post
    dos veces.
    """
    otras = [f for f in leer()
             if (f["slug"], f["creado"]) != (fila["slug"], fila["creado"])
             and not (f["slug"] == fila["slug"] and f["estado"] == "programado")]
    escribir(sorted(otras + [fila], key=lambda f: f["cuando"]))
    return fila


def soltar(fila):
    """Publica una fila. El error se guarda en la fila, no se propaga: una
    subasta que falla no puede tumbar las que vienen detras en la misma corrida."""
    try:
        fila["post"], fila["permalink"] = publicar(fila["urls"], fila["caption"])
        fila["estado"], fila["error"] = "publicado", ""
    except Exception as e:  # noqa: BLE001 - lo que sea, queda escrito y a la vista
        fila["estado"], fila["error"] = "error", str(e)[:300]
    fila["cerrado"] = time.time()
    return fila


def ahora(slug, texto, urls):
    return guardar(soltar(nueva(slug, texto, urls)))


def programar(slug, texto, urls, cuando):
    return guardar(nueva(slug, texto, urls, cuando))


def pendientes(reloj=None):
    """Publica todo lo que ya toca. Esto es lo que corre en cron."""
    reloj = reloj or time.time()
    filas = leer()
    tocan = [f for f in filas if f["estado"] == "programado" and f["cuando"] <= reloj]
    for f in tocan:
        soltar(f)
        escribir(filas)     # tras cada uno: si el siguiente falla, este ya quedo anotado
    return tocan


def cuando_dice(marca):
    """La hora en horario de Lima, que es donde esta quien la programo."""
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("America/Lima")
    except Exception:  # noqa: BLE001 - imagen sin tzdata: Peru no tiene horario de verano
        from datetime import timedelta, timezone
        tz = timezone(timedelta(hours=-5))
    return datetime.fromtimestamp(marca, tz).strftime("%d/%m %H:%M")


def self_check():
    global AGENDA, publicar
    import tempfile
    AGENDA = os.path.join(tempfile.mkdtemp(), "agenda.json")

    # El caption sale de una sola seccion del copy.
    copy = ("## Instagram\n\nEste Honda entra el miercoles.\n\n#honda #subasta\n"
            "\n## WhatsApp\n\n*OJO* esto no va al feed.\n")
    assert caption(copy) == "Este Honda entra el miercoles.\n\n#honda #subasta"
    assert "WhatsApp" not in caption(copy)
    assert caption("solo un texto suelto") == "solo un texto suelto"

    # Topes de Meta, antes de gastar una llamada.
    for urls, malo in (([], "1"), (["u"], "2"), (["u"] * 11, "11")):
        try:
            publicar(urls, "x")
        except ValueError as e:
            assert "imagenes" in str(e), e
        else:
            raise AssertionError(f"{malo} imagenes tenia que fallar")
    try:
        publicar(["a", "b"], "x" * 2201)
    except ValueError as e:
        assert "2200" in str(e)
    else:
        raise AssertionError("un caption de 2201 tenia que fallar")

    try:
        nueva("x", "t", ["a", "b"], time.time() + (TOPE_DIAS + 1) * 86400)
    except ValueError as e:
        assert "dias" in str(e)
    else:
        raise AssertionError("programar mas alla del tope tenia que fallar")

    # Publicar de verdad, con Meta de mentira.
    publicado = []
    publicar = lambda urls, texto: (publicado.append(texto) or ("id1", "https://ig/p/1"))
    fila = ahora("63001-toyota-hilux", "hola", ["a", "b"])
    assert fila["estado"] == "publicado" and fila["permalink"] == "https://ig/p/1"
    assert publicado == ["hola"]

    # Reprogramar la misma subasta reemplaza, no acumula: publicaria dos veces.
    programar("63002-etios", "v1", ["a", "b"], time.time() + 3600)
    programar("63002-etios", "v2", ["a", "b"], time.time() + 7200)
    esperando = [f for f in leer() if f["estado"] == "programado"]
    assert len(esperando) == 1 and esperando[0]["caption"] == "v2", esperando
    assert len(leer()) == 2, "el publicado no se borra: la agenda es el registro"

    # Solo sale lo que ya toca.
    assert pendientes(time.time()) == []
    salieron = pendientes(time.time() + 8000)
    assert [f["slug"] for f in salieron] == ["63002-etios"], salieron
    assert all(f["estado"] == "publicado" for f in leer())

    # Un fallo queda escrito y no se lleva la corrida.
    def revienta(urls, texto):
        raise RuntimeError("Instagram: token sin permiso")
    publicar = revienta
    fila = ahora("63006-groove", "hola", ["a", "b"])
    assert fila["estado"] == "error" and "permiso" in fila["error"]
    print("ok")


def imprimir_agenda():
    for f in leer():
        marca = cuando_dice(f["cuando"])
        cola = f["permalink"] or f["error"] or ""
        print(f"{marca}  {f['estado']:<10} {f['slug']:<26} {cola}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--self-check" in a:
        self_check()
    elif "--pendientes" in a:
        salieron = pendientes()
        for f in salieron:
            print(f"{f['estado']}: {f['slug']}  {f['permalink'] or f['error']}")
        print(f"--- {len(salieron)} publicacion(es)")
    elif "--agenda" in a:
        imprimir_agenda()
    elif "--ahora" in a and len(a) > 1:
        slug = a[a.index("--ahora") + 1].strip("/").removeprefix("Posts/")
        carpeta = os.path.join(POSTS, slug)
        with open(os.path.join(carpeta, "copy.md"), encoding="utf8") as f:
            texto = caption(f.read())
        fila = ahora(slug, texto, bucket.subir(slug, carpeta))
        print(fila["permalink"] or fila["error"])
    elif "--programar" in a and len(a) > 2:
        i = a.index("--programar")
        slug = a[i + 1].strip("/").removeprefix("Posts/")
        cuando = datetime.strptime(a[i + 2], "%Y-%m-%d %H:%M").timestamp()
        carpeta = os.path.join(POSTS, slug)
        with open(os.path.join(carpeta, "copy.md"), encoding="utf8") as f:
            texto = caption(f.read())
        fila = programar(slug, texto, bucket.subir(slug, carpeta), cuando)
        print(f"programado para {cuando_dice(fila['cuando'])}")
    else:
        sys.exit(__doc__)
