#!/usr/bin/env python3
"""
Read the board from vmcsubastas' own API: every open listing, live and
negotiable, grouped by closing date.

`support/offer-groups` takes no token, so this works on the desktop and inside
the container without asking anyone for anything. The endpoints that carry the
full listing —`offers/state`, with transmission, seller and the whole gallery—
sit behind a Bearer token and an IP allowlist; until those arrive, `scraper.py`
stays the one that reads a single listing. See API-INTEGRACION.md.

    import api
    for grupo in api.ofertas():          # [{tipo, fecha, hora, ofertas: [...]}]
        ...

From the terminal, to check the API is answering:
    python3 api.py
"""
import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = "https://services.subastop.com/api/v3"


def _pedir(scope, value=None):
    """Un scope de offer-groups. Devuelve `result`, que es null si no hay nada."""
    pedido = urllib.request.Request(
        f"{BASE}/support/offer-groups",
        data=json.dumps({"scope": scope, "value": value}).encode(),
        # El WAF rechaza con 403 el User-Agent que urllib manda por defecto,
        # igual que en scraper.py.
        headers={"Accept": "application/json",
                 "Content-Type": "application/json",
                 "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(pedido, timeout=30) as r:
        return json.loads(r.read()).get("result") or {}


def _tarjeta(o):
    """Card de la API -> lo que la pagina necesita, y nada mas."""
    cierre = o.get("readable_close_date") or {}
    stats = o.get("stats") or {}
    return {
        "id": o["id"],
        "nombre": o.get("name") or "",
        "anio": str(o.get("model_year") or ""),
        # En negociables la API manda null a proposito: no hay precio base.
        "precio": o.get("base_price"),
        "cierre": " ".join(x for x in (cierre.get("date"), cierre.get("time"),
                                       cierre.get("meridian")) if x),
        # "image" es la de mayor calidad que publica la API para una
        # tarjeta -- recien activada; antes solo llegaba "image_md" (460x345).
        # image_md/image_xs quedan de respaldo por si una oferta vieja
        # todavia no la trae. De aca solo se elige; las del carrusel las baja
        # scraper.py en 800x600, que es el techo del CDN (API-INTEGRACION.md).
        "foto": o.get("image") or o.get("image_md") or o.get("image_xs") or "",
        "vistas": stats.get("views") or 0,
        # Live cuenta participantes; negociable, negociaciones. Nunca las dos.
        "interes": stats.get("participants") if stats.get("participants") is not None
                   else (stats.get("negotiations") or 0),
        "financia": bool(o.get("is_financing")),
    }


def _grupos(result, tipo):
    """Los grupos de un scope, sin las terminadas: un carrusel se hace de una
    subasta que todavia no cerro."""
    salida = []
    for g in (result.get("groups") or []):
        ofertas = [_tarjeta(o) for o in (g.get("offers") or [])]
        if ofertas:
            salida.append({"tipo": tipo, "fecha": g.get("date") or "",
                           "hora": g.get("time") or "", "ofertas": ofertas})
    return salida


def _grupo_o_nada(par):
    scope, tipo = par
    try:
        return _grupos(_pedir("offer-type", scope), tipo)
    except Exception:  # noqa: BLE001 - el otro scope sigue sirviendo
        return []


def ofertas():
    """Todo lo abierto: lo que se subasta en vivo y lo negociable.

    Un fallo de red en un scope no puede dejar la pagina vacia, asi que cada
    uno se pide por separado y el que responda se muestra. Los dos scopes no
    dependen uno del otro, asi que se piden a la vez.
    """
    with ThreadPoolExecutor(2) as pool:
        salida = [g for grupos in pool.map(
            _grupo_o_nada, (("live", "vivo"), ("negotiable", "negociable")))
            for g in grupos]
    if not salida:
        raise LookupError("La API no devolvió ofertas. ¿Hay conexión?")
    return salida


def _demo():
    """La forma de la respuesta cambia sin avisar: esto falla el dia que pase."""
    crudo = {"groups": [
        {"date": "mié. 26 ago.", "time": "Inicia 02:40 PM", "offers": [{
            "id": 63154, "name": "Toyota Rush", "model_year": "2026",
            "base_price": 10999, "is_financing": False,
            "image_md": "https://cdn/m_x.png",
            "readable_close_date": {"date": "Hoy", "time": "02:40",
                                    "meridian": "pm"},
            "stats": {"views": 1052, "participants": 22, "negotiations": None}}]},
        {"date": "jue. 27 ago.", "time": "", "offers": []},   # se descarta
    ]}
    g = _grupos(crudo, "vivo")
    assert len(g) == 1, "un grupo sin ofertas no se muestra"
    o = g[0]["ofertas"][0]
    assert o["id"] == 63154 and o["cierre"] == "Hoy 02:40 pm", o
    assert o["interes"] == 22, "en vivo manda participantes"
    assert o["foto"] == "https://cdn/m_x.png", "cae a image_md sin image"
    m = _tarjeta({"id": 2, "name": "y", "base_price": 1,
                  "image": "https://cdn/full.jpg", "image_md": "https://cdn/m_y.png",
                  "stats": {}})
    assert m["foto"] == "https://cdn/full.jpg", "image manda sobre image_md"
    # Negociable: sin precio base y contando negociaciones, no participantes.
    n = _tarjeta({"id": 1, "name": "x", "base_price": None,
                  "stats": {"views": 3, "participants": None, "negotiations": 0}})
    assert n["precio"] is None and n["interes"] == 0, n
    print("ok")


if __name__ == "__main__":
    import sys
    if "--demo" in sys.argv:
        _demo()
    else:
        grupos = ofertas()
        for g in grupos:
            print(f"{g['tipo']:11} {g['fecha']:14} {g['hora']:20} "
                  f"{len(g['ofertas'])} ofertas")
        print(f"{sum(len(g['ofertas']) for g in grupos)} ofertas abiertas")
