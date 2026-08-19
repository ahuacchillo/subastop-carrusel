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
# One props JSON per slide. Built with python rather than a heredoc because the
# values carry apostrophes (25') and accents, which break a heredoc silently.
PROPS="$(mktemp -d)"
trap 'rm -rf "$PROPS"' EXIT
SLIDES="$(DATOS="$DATOS" DESTINO="$PROPS" python3 - <<'PY'
import json, os
datos = json.load(open(os.environ["DATOS"]))
for i in range(len(datos["fotos"])):
    with open(f"{os.environ['DESTINO']}/{i}.json", "w") as f:
        json.dump({"s": datos, "indice": i}, f, ensure_ascii=False)
print(len(datos["fotos"]))
PY
)"

echo
echo "── Renderizando $SLIDES slides ───────────────────────────────"
# ponytail: one bundle per slide (~13s each). If that ever hurts, switch to the
# Node API (@remotion/renderer), which bundles once for all of them.
cd remotion
for i in $(seq 0 $((SLIDES - 1))); do
  npx remotion still Auto \
    --props="$PROPS/$i.json" \
    --output="$RAIZ/Posts/$SLUG/$((i + 1)).png" \
    --overwrite --log=error
  echo "  ✓ Posts/$SLUG/$((i + 1)).png"
done

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
