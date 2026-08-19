#!/usr/bin/env bash
#
# Builds a whole auction carousel: asks for the details, takes the photos from
# Materiales/ and leaves publishable PNGs in Posts/<slug>/.
#
# It edits no code. The details reach Remotion through --props, so this script
# and the project stay independent: run it twice in a row with different cars
# and nothing from the first run sticks to the second.
#
#   ./nueva-subasta.sh 62996                # URL to PNGs, no questions asked
#   ./nueva-subasta.sh https://www.vmcsubastas.com/oferta/62996
#   ./nueva-subasta.sh 62996 --editar       # same, but reviewing every field
#   ./nueva-subasta.sh Materiales/toyota    # own photos, no scraping
#   ./nueva-subasta.sh                      # loose photos in Materiales/
#
# Given a URL it asks nothing: whatever the site returns is taken as true and
# rendered. The only thing left to check are the PNGs at the end.
#
set -euo pipefail
cd "$(dirname "$0")"

RAIZ="$PWD"
AUTOS="$RAIZ/remotion/public/autos"
ORIGEN="Materiales"
EDITAR=""
FOTOS_PROPIAS=""
while [ $# -gt 0 ]; do
  case "$1" in
    --editar|-e) EDITAR=1 ;;
    # Site details with my own photos: for when the listing's gallery is poor
    # or better shots from the lot exist.
    --fotos|-f) FOTOS_PROPIAS="${2:?--fotos necesita una carpeta}"; shift ;;
    *) ORIGEN="$1" ;;
  esac
  shift
done
[ -z "$FOTOS_PROPIAS" ] || [ -d "$FOTOS_PROPIAS" ] || {
  echo "No existe la carpeta de fotos '$FOTOS_PROPIAS'." >&2; exit 1; }

# ── Scraping the listing ─────────────────────────────────────────────────────
# The vmcsubastas page is server-rendered: the details and the photos are in
# the HTML, so no browser is needed. What comes out of here is only the default
# answer to each question; every one of them can still be corrected by hand.
MARCA=""; MODELO=""; ANIO="25'"; TRANSMISION="Mecánica"; PRECIO=""
FECHA=""; HORA=""; TIENDA=""; OFERTA=""
if [[ "$ORIGEN" =~ ^https?://|^[0-9]+$ ]]; then
  ID="${ORIGEN##*/}"
  OFERTA="$ID"
  # Photos are stored under the listing code: it is the one name that survives
  # a later correction to the make or the model, so nothing is downloaded twice.
  # With --fotos nothing is downloaded at all; the gallery only confirms that
  # the page that answered is the listing and not the site's front page.
  if [ -n "$FOTOS_PROPIAS" ]; then
    ORIGEN="$FOTOS_PROPIAS"
    DESTINO=""
  else
    ORIGEN="Materiales/$ID"
    mkdir -p "$ORIGEN"
    DESTINO="$ORIGEN"
  fi
  # ${DESTINO:+…} vanishes entirely when empty, so with --fotos the scraper
  # receives no folder and therefore downloads nothing.
  SCRAPE="$(python3 "$RAIZ/scraper.py" "$ID" ${DESTINO:+"$DESTINO"})"
  while IFS=$'\t' read -r clave valor; do
    printf -v "$clave" '%s' "$valor"
  done <<< "$SCRAPE"
fi

[ -d "$ORIGEN" ] || { echo "No existe la carpeta '$ORIGEN'." >&2; exit 1; }

# ── Details ──────────────────────────────────────────────────────────────────
# Enter accepts the value in brackets. If the scrape already found a field it
# is not asked about: the site is the source. --editar reviews all of them, and
# anything the scrape missed is always asked for.
preguntar() { # preguntar VARIABLE "Texto" ["default"]
  local resp
  if [ -z "$EDITAR" ] && [ -n "$OFERTA" ] && [ -n "${3:-}" ]; then
    printf -v "$1" '%s' "$3"
    printf "  %-32s %s\n" "$2:" "$3"
    return
  fi
  read -r -p "  $2${3:+ [$3]}: " resp
  resp="${resp:-${3:-}}"
  [ -n "$resp" ] || { echo "  ↳ hace falta un valor." >&2; preguntar "$1" "$2" "${3:-}"; return; }
  printf -v "$1" '%s' "$resp"
}

echo
echo "── Datos del auto ─────────────────────────────────────────"
preguntar MARCA       "Marca (título con degradado)"   "$MARCA"
preguntar MODELO      "Modelo (va encima, en blanco)"  "$MODELO"
preguntar ANIO        "Año corto"                      "$ANIO"
preguntar TRANSMISION "Transmisión"                    "$TRANSMISION"
preguntar PRECIO      "Precio base (sin US\$)"         "$PRECIO"
echo
echo "── Subasta ────────────────────────────────────────────────"
preguntar FECHA       "Fecha (dd/mm)"                  "$FECHA"
preguntar HORA        "Hora"                           "$HORA"
preguntar TIENDA      "Tienda oficial"                 "$TIENDA"

# ── Photos ───────────────────────────────────────────────────────────────────
mapfile -t DISPONIBLES < <(
  find "$ORIGEN" -maxdepth 1 -type f \
    \( -iname '*.png' -o -iname '*.jpg' -o -iname '*.jpeg' \) | sort
)
[ "${#DISPONIBLES[@]}" -gt 0 ] || { echo "No hay fotos en $ORIGEN/." >&2; exit 1; }

echo
echo "── Fotos en $ORIGEN/ ──────────────────────────────────────"
for i in "${!DISPONIBLES[@]}"; do
  printf "  %d) %s\n" "$((i + 1))" "$(basename "${DISPONIBLES[$i]}")"
done
echo
echo "  El primero es la portada: es el único slide que lleva marca y modelo."
# The carousel holds 3: any extra photos in the folder are ignored.
TODAS="$(seq -s' ' 1 "$(( ${#DISPONIBLES[@]} < 3 ? ${#DISPONIBLES[@]} : 3 ))")"
ORDEN=""
if [ -z "$EDITAR" ] && [ -n "$OFERTA" ] && [ -z "$FOTOS_PROPIAS" ]; then
  # The site's photos already arrive in gallery order, so they are used as-is.
  # Hand-picked ones are different: there the cover is a decision, so we ask.
  ORDEN="$TODAS"
else
  while [ -z "$ORDEN" ]; do
    read -r -p "  Orden del carrusel (3 slides) [$TODAS]: " ORDEN
    ORDEN="$(echo "${ORDEN:-$TODAS}" | cut -d' ' -f1-3)"
    malo=""
    for idx in $ORDEN; do
      case "$idx" in
        ''|*[!0-9]*) malo="$idx" ;;
        *) [ "$idx" -ge 1 ] && [ "$idx" -le "${#DISPONIBLES[@]}" ] || malo="$idx" ;;
      esac
    done
    [ -z "$malo" ] || {
      echo "  ↳ '$malo' no está en la lista. Números del 1 al ${#DISPONIBLES[@]}, separados por espacio."
      ORDEN=""
    }
  done
fi

# Typing "3" means choosing the cover, not asking for a one-slide carousel, so
# the rest is filled in from the listing order.
# ponytail: which also means a deliberate subset can no longer be rendered.
# If that is ever needed it is a --slides flag, not another prompt.
for idx in $(seq 1 "${#DISPONIBLES[@]}"); do
  case " $ORDEN " in *" $idx "*) ;; *) ORDEN="$ORDEN $idx" ;; esac
done
ORDEN="$(echo $ORDEN | cut -d' ' -f1-3)"
echo "  Carrusel: $ORDEN"

# ── Copy the photos under stable names ───────────────────────────────────────
# The slug prefixes the files so two auctions cannot collide inside public/.
# The listing code goes first: it tells two different Fortuners apart, and it
# is the number people search for when they need the original publication.
SLUG="$(printf '%s-%s-%s' "$OFERTA" "$MARCA" "$MODELO" \
  | iconv -f utf8 -t ascii//TRANSLIT \
  | tr '[:upper:]' '[:lower:]' \
  | tr -cs 'a-z0-9' '-' \
  | sed 's/^-//; s/-$//')"

mkdir -p "$AUTOS" "$RAIZ/Posts/$SLUG"
FOTOS=()
n=0
for idx in $ORDEN; do
  origen="${DISPONIBLES[$((idx - 1))]}"
  ext="${origen##*.}"
  n=$((n + 1))
  destino="$AUTOS/$SLUG-$n.${ext,,}"
  cp "$origen" "$destino"
  FOTOS+=("autos/$SLUG-$n.${ext,,}")
done

# ── datos.json ───────────────────────────────────────────────────────────────
# Built with python rather than a heredoc because the values carry apostrophes
# (25') and accents, which break a heredoc silently. It sits next to the
# renders, so the piece can be rebuilt identically a year from now.
MARCA="$MARCA" MODELO="$MODELO" ANIO="$ANIO" TRANSMISION="$TRANSMISION" \
PRECIO="$PRECIO" FECHA="$FECHA" HORA="$HORA" TIENDA="$TIENDA" \
FOTOS="${FOTOS[*]}" SALIDA="$RAIZ/Posts/$SLUG" \
python3 - <<'PY'
import json, os
e = os.environ
s = {
    "marca": e["MARCA"], "modelo": e["MODELO"], "anio": e["ANIO"],
    "transmision": e["TRANSMISION"], "precioBase": "US$ " + e["PRECIO"],
    "fecha": e["FECHA"], "hora": e["HORA"], "tienda": e["TIENDA"],
    "fotos": e["FOTOS"].split(),
}
with open(f"{e['SALIDA']}/datos.json", "w") as f:
    json.dump(s, f, ensure_ascii=False, indent=2)
PY

# ── Render ───────────────────────────────────────────────────────────────────
# `ajustar.sh` does the rendering: one path only, so the closing card and the
# framing support never live in two places that drift apart.
exec "$RAIZ/ajustar.sh" "$SLUG" --render
