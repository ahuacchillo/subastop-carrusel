#!/usr/bin/env bash
#
# Details come from the listing, the photos come from me.
#
# Same as `nueva-subasta.sh <code>` but without downloading the site gallery:
# make, model, year, transmission, price, date, time and store are read from
# vmcsubastas.com, and the carousel is built from the folder you point at.
# For when the listing's own photos are poor, or better ones exist.
#
#   ./subasta-fotos-propias.sh 62996 Materiales/toyota
#   ./subasta-fotos-propias.sh https://www.vmcsubastas.com/oferta/62996 fotos/
#
# It asks for the carousel order: when the photos were picked by hand, which
# one leads is a human decision, not the site's. Add --editar to also review
# every scraped field.
#
set -euo pipefail

[ $# -ge 2 ] || {
  echo "Uso: $(basename "$0") <código-o-URL> <carpeta-de-fotos> [--editar]" >&2
  exit 1
}

OFERTA="$1"; CARPETA="$2"; shift 2
exec "$(dirname "$0")/nueva-subasta.sh" "$OFERTA" --fotos "$CARPETA" "$@"
