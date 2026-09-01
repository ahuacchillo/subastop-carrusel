#!/usr/bin/env python3
"""
Pick the three photos of a carousel by looking at them.

The order of a carousel is not the order of the gallery. What sells is always
the same sequence: the car from the front, then what it is like inside, then the
back with the plate. Choosing that by hand is the slowest part of making a
carousel, and it is the only step that needs eyes.

    import elegir
    tres, chocado, focos = elegir.mirar("Materiales/63179")

From the terminal, on one listing:
    python3 elegir.py Materiales/63179
    python3 elegir.py --demo          # sin red ni modelo: revisa las reglas

Who looks: a vision model. First choice is DeepSeek's vision API
(deepseek-v4-flash-vision-exp), which takes images as base64 inline and answers
JSON directly — no CLI, no file contract, no subprocess. If DEEPSEEK_API_KEY is
not set, the code falls back to the `claude` CLI, which is what it did before.

Nothing here trusts that answer: whatever comes back is checked against the
photos that really exist, and anything missing falls back to gallery order. A
carousel with the photos in the wrong order is a bad carousel; a carousel that
never got made because a model wrote a filename with a typo is no carousel.

"Anything missing" includes there being no API key AND no `claude` on the
machine, which is the case inside the Cloud Run container without either: no
model means gallery order and a centred crop, not a failed batch.
"""
import base64
import json
import mimetypes
import os
import subprocess
import sys
import urllib.error
import urllib.request

RAIZ = os.path.dirname(os.path.abspath(__file__))
EXTS = (".png", ".jpg", ".jpeg")
CLAVES = ("frente", "interior_o_lado", "atras_con_placa")
DEEPSEEK = os.environ.get("DEEPSEEK_API_KEY", "")
# La galeria del sitio nunca pasaba de 8 (scraper.py la capaba ahi); Drive no
# tiene tope y una carpeta de 20 fotos hace que DeepSeek responda 413 (payload
# muy grande) -- y eso caia en silencio a orden de galeria, no a un error
# visible. El tope va aca, no en la descarga: el estudio a mano si necesita
# ver la carpeta entera para elegir.
MAX_PARA_MIRAR = 8

# The prompt is the same for both paths — only the delivery mechanism changes.
# DeepSeek gets the images inline and returns JSON to stdout; Claude reads files
# from disk and writes `seleccion.json`. The instructions stay in one place so
# they cannot drift apart.
INSTRUCCIONES = """Mira las {n} fotos y elige TRES para un carrusel de
Instagram de una subasta de autos.

Primero clasifica cada foto en una de estas vistas:
- "frente": se ve la trompa del auto, de frente o en tres cuartos delantero.
- "lado": el perfil, el auto visto de costado y entero.
- "atras": la cola del auto, de atrás o en tres cuartos trasero.
- "interior": tablero, asientos, timón, consola — cualquier toma desde adentro.
- "detalle": una parte suelta y de cerca: una llanta, un golpe, el motor, un
  documento, el número de chasis.
- "otra": lo que no sea el auto, y las capturas de pantalla de otro anuncio.

Después elige tres, en este orden:
1. "frente" — la mejor de las "frente": el auto lo más completo y menos tapado.
2. "interior_o_lado" — la mejor "interior". Si NO hay ninguna foto de interior,
   entonces la mejor "lado". Un tres cuartos trasero NO es un lado.
3. "atras_con_placa" — de las "atras", la que deje leer mejor la placa.

Reglas:
- Las tres tienen que ser fotos distintas, y no dos de la misma vista.
- Si una categoría no existe entre las fotos, igual elige la más parecida que no
  hayas usado: el carrusel lleva tres sí o sí.
- Descarta las borrosas, las muy oscuras y las que sean captura de otro anuncio.

Y para cada una de las tres, dime dónde está el centro del auto de izquierda a
derecha, en porcentaje del ancho de la foto: 0 es pegado al borde izquierdo, 50
justo al medio, 100 pegado al borde derecho. El slide es cuadrado y la foto es
más ancha, así que se recortan los lados por igual: ese número decide qué lado
se recorta y es lo único que evita que al auto le corten la trompa o la cola.
Si el auto ya está al medio, 50.

Y responde una cosa mas: "siniestrado", true si el auto está chocado o
golpeado —abolladuras, un parachoques partido, un faro roto, la carrocería
hundida—, false si está entero. Ante la duda, false.

Responde SOLO un JSON válido, sin comentarios ni texto adicional. Exactamente
esta forma, con los nombres de archivo tal cual y la vista que le pusiste a cada
foto:

{{"vistas": {{"01.jpeg": "frente", "02.jpeg": "atras"}}, "siniestrado": false,
 "frente": "01.jpeg", "interior_o_lado": "04.jpeg", "atras_con_placa": "06.jpeg",
 "centro_x": {{"01.jpeg": 44, "04.jpeg": 50, "06.jpeg": 61}}}}"""

# The Claude-CLI version keeps the old wording that tells it to Read files and
# Write the result. Separated here because DeepSeek receives the images inline
# and returns JSON directly — it has nothing to Read or Write.
INSTRUCCIONES_CLI = """Mira las {n} fotos de {carpeta} y elige TRES para un carrusel de
Instagram de una subasta de autos.

Léelas TODAS con Read en un solo turno, las {n} llamadas juntas y en paralelo.
Una por mensaje son {n} viajes de ida y vuelta y es lo que hace lento este paso.

Primero clasifica cada foto en una de estas vistas:
- "frente": se ve la trompa del auto, de frente o en tres cuartos delantero.
- "lado": el perfil, el auto visto de costado y entero.
- "atras": la cola del auto, de atrás o en tres cuartos trasero.
- "interior": tablero, asientos, timón, consola — cualquier toma desde adentro.
- "detalle": una parte suelta y de cerca: una llanta, un golpe, el motor, un
  documento, el número de chasis.
- "otra": lo que no sea el auto, y las capturas de pantalla de otro anuncio.

Después elige tres, en este orden:
1. "frente" — la mejor de las "frente": el auto lo más completo y menos tapado.
2. "interior_o_lado" — la mejor "interior". Si NO hay ninguna foto de interior,
   entonces la mejor "lado". Un tres cuartos trasero NO es un lado.
3. "atras_con_placa" — de las "atras", la que deje leer mejor la placa.

Reglas:
- Las tres tienen que ser fotos distintas, y no dos de la misma vista.
- Si una categoría no existe entre las fotos, igual elige la más parecida que no
  hayas usado: el carrusel lleva tres sí o sí.
- Descarta las borrosas, las muy oscuras y las que sean captura de otro anuncio.

Y para cada una de las tres, dime dónde está el centro del auto de izquierda a
derecha, en porcentaje del ancho de la foto: 0 es pegado al borde izquierdo, 50
justo al medio, 100 pegado al borde derecho. El slide es cuadrado y la foto es
más ancha, así que se recortan los lados por igual: ese número decide qué lado
se recorta y es lo único que evita que al auto le corten la trompa o la cola.
Si el auto ya está al medio, 50.

Y responde una cosa mas: "siniestrado", true si el auto está chocado o
golpeado —abolladuras, un parachoques partido, un faro roto, la carrocería
hundida—, false si está entero. Ante la duda, false.

Escribe el resultado en {carpeta}/seleccion.json y nada más. Ese archivo es el
entregable, no lleva comentarios tuyos. Exactamente esta forma, con los nombres
de archivo tal cual y la vista que le pusiste a cada foto:

{{"vistas": {{"01.jpeg": "frente", "02.jpeg": "atras"}}, "siniestrado": false,
 "frente": "01.jpeg", "interior_o_lado": "04.jpeg", "atras_con_placa": "06.jpeg",
 "centro_x": {{"01.jpeg": 44, "04.jpeg": 50, "06.jpeg": 61}}}}"""


def fotos_de(carpeta):
    """Las fotos de la carpeta, en orden de galeria."""
    return sorted(f for f in os.listdir(carpeta) if f.lower().endswith(EXTS))


def _foco(valor):
    """Un `objectPosition` para el slide, del centro horizontal que dio el modelo.

    Solo el eje X: la foto del CDN es 4:3 y el slide es 1:1, asi que `cover`
    recorta los lados y nunca el alto. Preguntar por una Y seria pedir un dato
    que el render tira.

    Fuera de rango, no numerico o ausente cae en el centro, que es lo que hacia
    la pagina antes de que hubiera modelo. Y se recorta a 15-85: un 0 pega el
    auto contra el borde y ahi vive la tarjeta de datos.
    """
    try:
        x = round(float(valor))
    except (TypeError, ValueError):
        return "50% 50%"
    return f"{min(85, max(15, x))}% 50%"


def _validar(seleccion, archivos):
    """La eleccion del modelo contra las fotos que de verdad hay.

    Devuelve tres nombres distintos y su foco, siempre. Lo que no venga, o venga
    repetido, o nombre un archivo que no existe, se rellena en orden de galeria:
    es la misma eleccion que se hacia antes de que hubiera modelo.
    """
    tres = []
    for clave in CLAVES:
        nombre = os.path.basename(str(seleccion.get(clave, "")))
        if nombre in archivos and nombre not in tres:
            tres.append(nombre)
    for archivo in archivos:                 # el relleno, en orden de galeria
        if len(tres) == 3:
            break
        if archivo not in tres:
            tres.append(archivo)
    centros = seleccion.get("centro_x")
    if not isinstance(centros, dict):
        centros = {}
    # Por nombre de archivo y no por posicion: si el relleno cambio los tres, el
    # foco que el modelo dio para otra foto no puede viajar pegado al indice.
    return tres, [_foco(centros.get(f)) for f in tres]


def _media_type(nombre):
    """MIME type from the file name, defaulting to jpeg for unknowns."""
    mt, _ = mimetypes.guess_type(nombre)
    return mt or "image/jpeg"


def _mirar_deepseek(carpeta, archivos):
    """Call DeepSeek Vision with all photos inline as base64.

    Returns the parsed JSON dict or {} on any failure. The caller validates
    whatever comes back exactly the same way it validates Claude's answer, so a
    bad response here is harmless — it just falls through to gallery order.

    Images go as base64 data-URIs inside the `image_url` content part, which is
    the OpenAI-compatible shape that DeepSeek's vision endpoint accepts. One
    user message contains all photos interleaved with their file names so the
    model can reference them in its answer.
    """
    # Build the multimodal message: for each photo, a text part with the file
    # name followed by an image part with the base64 data.
    partes = []
    for nombre in archivos:
        ruta = os.path.join(carpeta, nombre)
        with open(ruta, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        partes.append({"type": "text", "text": f"Foto: {nombre}"})
        partes.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:{_media_type(nombre)};base64,{b64}",
            },
        })
    prompt = INSTRUCCIONES.format(n=len(archivos))
    cuerpo = json.dumps({
        "model": "deepseek-v4-flash-vision-exp",
        "messages": [
            {"role": "system", "content": "Eres un asistente que clasifica fotos "
             "de autos para carruseles de Instagram. Respondes SOLO JSON válido."},
            {"role": "user", "content": [
                {"type": "text", "text": prompt},
                *partes,
            ]},
        ],
    }).encode()
    pedido = urllib.request.Request(
        "https://api.deepseek.com/chat/completions", data=cuerpo,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {DEEPSEEK}"})
    try:
        with urllib.request.urlopen(pedido, timeout=180) as r:
            texto = json.load(r)["choices"][0]["message"]["content"].strip()
    except (urllib.error.HTTPError, urllib.error.URLError,
            OSError, KeyError, IndexError) as e:
        print(f"elegir: DeepSeek falló ({e}), cayendo a fallback.", file=sys.stderr)
        return {}
    # The model sometimes wraps JSON in a code fence.
    if texto.startswith("```"):
        texto = texto.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    try:
        resultado = json.loads(texto)
    except (ValueError, TypeError):
        print(f"elegir: DeepSeek devolvió texto no-JSON, cayendo a fallback.",
              file=sys.stderr)
        return {}
    return resultado if isinstance(resultado, dict) else {}


def _mirar_claude(carpeta, archivos, tiempo):
    """Fall back to the Claude CLI if DeepSeek is not available.

    This is the original implementation: it shells out to `claude` with the Read
    and Write tools, and the model writes seleccion.json to disk.
    """
    ruta = os.path.join(carpeta, "seleccion.json")
    relativa = os.path.relpath(os.path.abspath(carpeta), RAIZ)
    try:
        r = subprocess.run(
            ["claude", "-p",
             INSTRUCCIONES_CLI.format(n=len(archivos), carpeta=relativa),
             "--allowed-tools", "Read", "Write", "--permission-mode", "acceptEdits",
             "--model", "sonnet"],
            cwd=RAIZ, capture_output=True, text=True, timeout=tiempo)
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        r = None
    seleccion = {}
    if r is not None and r.returncode == 0 and os.path.isfile(ruta):
        try:
            with open(ruta, encoding="utf8") as f:
                seleccion = json.load(f)
        except (ValueError, OSError):
            seleccion = {}
    if not isinstance(seleccion, dict):
        seleccion = {}
    return seleccion


def mirar(carpeta, tiempo=300):
    """(tres fotos, siniestrado, focos). En orden: portada, interior/lado, placa.

    Lo de siniestrado viaja aca y no en otra llamada porque es la misma mirada:
    quien ya vio las ocho fotos sabe si el auto esta chocado, y el copy de una
    unidad chocada es otro copy. Sin esto el lote publicaria "en buen estado"
    sobre una foto de un parachoques partido.

    Con menos de tres fotos no hay nada que elegir y no se gasta un modelo en
    mirarlas — pero tampoco hay quien mire el estado, y no inventarlo es lo
    correcto: sale false, que es lo que la pagina ya asumia.

    Order of attempts:
    1. DEEPSEEK_API_KEY set → DeepSeek Vision (no CLI, no subprocess)
    2. No key → Claude CLI with Sonnet (the original path)
    3. Neither works → gallery order, centred crop
    """
    archivos = fotos_de(carpeta)
    if len(archivos) <= 3:
        return archivos, False, ["50% 50%"] * len(archivos)

    ruta = os.path.join(carpeta, "seleccion.json")
    # La respuesta de la corrida anterior se borra antes de pedir otra: si esta
    # falla, leerla seria dar por bueno un orden que nadie eligio para estas
    # fotos. Mirar de nuevo cuesta medio minuto; equivocarse cuesta un carrusel.
    if os.path.isfile(ruta):
        os.remove(ruta)

    # Al modelo se le manda un tope; _validar sigue viendo la galeria entera
    # para rellenar lo que falte, asi que una respuesta valida del subconjunto
    # nunca queda invalidada por el tope.
    vistas = archivos[:MAX_PARA_MIRAR]
    if DEEPSEEK:
        seleccion = _mirar_deepseek(carpeta, vistas)
    else:
        seleccion = _mirar_claude(carpeta, vistas, tiempo)

    tres, focos = _validar(seleccion, archivos)
    return tres, seleccion.get("siniestrado") is True, focos


def _demo():
    fotos = ["01.jpeg", "02.jpeg", "03.jpeg", "04.jpeg", "05.jpeg"]
    tres, focos = _validar({"frente": "03.jpeg", "interior_o_lado": "05.jpeg",
                            "atras_con_placa": "02.jpeg",
                            "centro_x": {"03.jpeg": 38, "02.jpeg": 71}}, fotos)
    assert tres == ["03.jpeg", "05.jpeg", "02.jpeg"], "el orden lo manda la categoria"
    # El foco viaja con su archivo, y la que el modelo no midio queda centrada.
    assert focos == ["38% 50%", "50% 50%", "71% 50%"], focos
    # Un nombre inventado, uno repetido y uno que falta: se rellena en orden de
    # galeria y nunca salen menos de tres ni dos veces la misma.
    tres, focos = _validar({"frente": "09.jpeg", "interior_o_lado": "04.jpeg",
                            "atras_con_placa": "04.jpeg",
                            # 09 no existe: su foco no puede caerle al relleno.
                            "centro_x": {"09.jpeg": 20}}, fotos)
    assert tres == ["04.jpeg", "01.jpeg", "02.jpeg"], tres
    assert focos == ["50% 50%"] * 3, focos
    assert _validar({}, fotos)[0] == fotos[:3], "sin respuesta, el orden de siempre"
    # Una ruta en vez de un nombre es lo que mas escribe el modelo.
    assert _validar({"frente": "Materiales/63179/05.jpeg"}, fotos)[0][0] == "05.jpeg"
    # Lo que el modelo escribe cuando no sabe: texto, nada, o fuera de rango.
    assert _foco(None) == _foco("centro") == _foco("") == "50% 50%"
    assert _foco(0) == "15% 50%" and _foco(140) == "85% 50%"
    assert _foco("62") == _foco(61.7) == "62% 50%"
    print("ok")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        _demo()
    elif len(sys.argv) > 1:
        tres, chocado, focos = mirar(sys.argv[1])
        for n, (f, foco) in enumerate(zip(tres, focos), 1):
            print(f"{n}. {f}\t{foco}")
        print("siniestrado" if chocado else "en buen estado")
    else:
        sys.exit("Uso: elegir.py <carpeta-de-fotos> | --demo")
