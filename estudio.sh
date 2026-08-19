#!/usr/bin/env bash
#
# Abre el estudio en el navegador. Es el camino sin terminal:
#
#   ./estudio.sh                    # carrusel nuevo
#   ./estudio.sh 62915-dfsk-glory   # reabrir uno hecho, para reencuadrar
#
set -euo pipefail
cd "$(dirname "$0")"
exec python3 estudio.py "$@"
