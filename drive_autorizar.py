#!/usr/bin/env python3
"""Corre UNA vez, a mano, para conseguir el refresh token que despues usa
Cloud Run para leer el Drive de fotos por placa. Abre el navegador, pide
consentimiento y deja el token en ~/drive-clave.txt (mismo patron que
~/ig-token.txt / ~/deepseek-clave.txt de desplegar.sh).

    DRIVE_CLIENT_ID=... DRIVE_CLIENT_SECRET=... python3 drive-autorizar.py

Login en el navegador: la cuenta que YA tiene acceso a la carpeta de Drive,
no la cuenta del proyecto de GCP -- no tienen por que ser la misma.
"""
import http.server
import json
import os
import sys
import urllib.parse
import urllib.request
import webbrowser

PUERTO = 8765
REDIRECT = f"http://localhost:{PUERTO}"
SCOPE = "https://www.googleapis.com/auth/drive.readonly"


def main():
    client_id = os.environ.get("DRIVE_CLIENT_ID")
    client_secret = os.environ.get("DRIVE_CLIENT_SECRET")
    if not client_id or not client_secret:
        sys.exit("Faltan DRIVE_CLIENT_ID / DRIVE_CLIENT_SECRET en el entorno.")

    codigo = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            codigo["valor"] = qs.get("code", [None])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("<p>Listo, ya podes cerrar esta pestaña.</p>".encode())

        def log_message(self, *a):
            pass  # ponytail: silencia el access log de un servidor de un solo pedido

    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": REDIRECT,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
    })
    print(f"Abriendo el navegador para autorizar (logueate con la cuenta que tiene el Drive)...\n{url}")
    webbrowser.open(url)

    server = http.server.HTTPServer(("localhost", PUERTO), Handler)
    server.handle_request()

    if not codigo.get("valor"):
        sys.exit("No llego el codigo de autorizacion.")

    data = urllib.parse.urlencode({
        "code": codigo["valor"],
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": REDIRECT,
        "grant_type": "authorization_code",
    }).encode()
    with urllib.request.urlopen(urllib.request.Request("https://oauth2.googleapis.com/token", data=data)) as resp:
        tokens = json.load(resp)

    refresh = tokens.get("refresh_token")
    if not refresh:
        sys.exit(f"Google no devolvio refresh_token. Respuesta: {tokens}")

    destino = os.path.expanduser("~/drive-clave.txt")
    with open(destino, "w") as f:
        f.write(f"{client_id}\n{client_secret}\n{refresh}\n")
    print(f"Guardado en {destino}")


if __name__ == "__main__":
    main()
