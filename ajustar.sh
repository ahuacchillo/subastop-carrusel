#!/usr/bin/env bash
#
# Reframe a carousel, or rebuild it from its `datos.json`.
#
#   ./ajustar.sh 62915-dfsk-glory            # opens the studio on that post
#   ./ajustar.sh 62915-dfsk-glory --render   # rebuilds the PNGs from datos.json
#
# With no flag it opens the studio in the browser: drag the photo, scroll to
# zoom, and the button saves and renders. That is what writes into datos.json:
#
#   "fotos": [
#     { "src": "autos/x-1.jpeg", "foco": "50% 35%", "escala": 1.2 },
#     "autos/x-2.jpeg"          <- a bare string means centred, no zoom
#   ]
#
# `nueva-subasta.sh` ends by calling this, so there is a single render path and
# the closing card and the framing support live in exactly one place.
#
set -euo pipefail
cd "$(dirname "$0")"

RAIZ="$PWD"
SLUG="${1:-}"
MODO="${2:-}"
[ -n "$SLUG" ] || { echo "Uso: $(basename "$0") <slug-de-Posts> [--render]" >&2; exit 1; }

# Either the slug or the whole path works: `Posts/x` and `Posts/x/` too.
SLUG="${SLUG#Posts/}"; SLUG="${SLUG%/}"
DATOS="$RAIZ/Posts/$SLUG/datos.json"
[ -f "$DATOS" ] || { echo "No existe $DATOS." >&2; exit 1; }

if [ "$MODO" != "--render" ]; then
  exec python3 "$RAIZ/estudio.py" "$SLUG"
fi

# ── Render ───────────────────────────────────────────────────────────────────
# `remotion/render.mjs` hace el trabajo: un bundle y un navegador para todo el
# carrusel. Por el CLI era uno de cada cosa por slide — medido en esta máquina,
# 9.9 s contra 5.4 s, y los PNG salen byte-idénticos.
SLIDES="$(python3 -c 'import json,sys; print(len(json.load(open(sys.argv[1]))["fotos"]))' "$DATOS")"

echo
echo "── Renderizando $SLIDES slides ───────────────────────────────"
cd remotion
node render.mjs "$DATOS" "$RAIZ/Posts/$SLUG"

# ── Closing card ─────────────────────────────────────────────────────────────
# Always last and always verbatim: it never goes through Remotion, carries no
# car data, and never changes. If it is missing, the rendered carousel survives.
CIERRE="$RAIZ/Materiales/cierre.png"
if [ -f "$CIERRE" ]; then
  cp "$CIERRE" "$RAIZ/Posts/$SLUG/$((SLIDES + 1)).png"
  echo "  ✓ Posts/$SLUG/$((SLIDES + 1)).png  (placa de cierre)"
else
  echo "  ⚠ Falta Materiales/cierre.png: el carrusel quedó sin placa final." >&2
fi

echo
echo "Listo → $RAIZ/Posts/$SLUG/"
echo "Míralos antes de publicar: que el título no se pierda contra el cielo y"
echo "que el precio no reviente la tarjeta."
