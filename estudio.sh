#!/usr/bin/env bash
#
# Abre el estudio en el navegador. Es el camino sin terminal:
#
#   ./estudio.sh                    # carrusel nuevo
#   ./estudio.sh 62915-dfsk-glory   # reabrir uno hecho, para reencuadrar
#
set -euo pipefail
cd "$(dirname "$0")"

# Las dos llaves viven en el home y nunca en el repo, igual que en desplegar.sh.
# Sin la de DeepSeek el lote cae al CLI de Claude para mirar las fotos; sin la
# de Instagram el botón de publicar responde "Falta IG_TOKEN en el entorno".
# Exportarlas a mano en cada terminal era el paso que se olvidaba.
# Un secreto guardado en un archivo del home. Se ignoran las lineas en blanco
# y las que empiezan con #, asi que el archivo puede llevar sus instrucciones
# dentro; el token es la primera linea que no sea comentario. Un # en medio de
# una contrasena sobrevive: solo se descarta la linea que *empieza* con el.
llave() { grep -vE '^[[:space:]]*(#|$)' "$1" 2>/dev/null | head -n1 | tr -d '\r\n'; }

DS="$(llave "$HOME/deepseek-clave.txt")"; [ -n "$DS" ] && export DEEPSEEK_API_KEY="$DS"
IG="$(llave "$HOME/ig-token.txt")";       [ -n "$IG" ] && export IG_TOKEN="$IG"

exec python3 estudio.py "$@"
