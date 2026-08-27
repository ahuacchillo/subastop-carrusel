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

# ── Agrandar las fotos antes de renderizar ───────────────────────────────────
# El CDN de vmcsubastas solo publica 800x600 y el slide es 1080x1080: con
# `cover` la foto tiene que llegar a 1440x1080, y Chrome la ampliaba 1.8x
# interpolando barato. Ampliada acá a 1440 de lado corto con Lanczos y un
# unsharp leve, el navegador *reduce* en vez de ampliar —que es la operación que
# hace bien— y el borde llega definido en vez de blando. No inventa detalle que
# la foto no tiene; deja de perder el que hay.
#
# Va acá y no en los dos scripts que copian fotos (`estudio.py` y
# `nueva-subasta.sh`) porque acá pasan las dos.
#
# ponytail: 1440 de lado corto, un tercio de más sobre lo que el slide pide.
# Con `escala` > 1 el slide muestra menos foto y querría más; subir el mínimo
# cuando alguien use zoom fuerte, que hoy es la excepción.
python3 -c 'import json,sys; print("\n".join(
    f if isinstance(f, str) else f["src"]
    for f in json.load(open(sys.argv[1]))["fotos"]))' "$DATOS" \
  | while IFS= read -r rel; do
      foto="$RAIZ/remotion/public/$rel"
      [ -f "$foto" ] || continue
      corto="$(identify -format '%[fx:min(w,h)]' "$foto[0]" 2>/dev/null || echo 1440)"
      [ "$corto" -lt 1440 ] 2>/dev/null || continue
      convert "$foto" -filter Lanczos -resize '1440x1440^' \
              -unsharp 0x0.75+0.75+0.008 -quality 96 "$foto"
      echo "  ↑ $rel  ${corto}px → 1440px de lado corto"
    done

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
