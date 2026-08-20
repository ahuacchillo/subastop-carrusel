#!/usr/bin/env bash
#
# Despliega el estudio en Cloud Run.
#
#   ./desplegar.sh
#
# Construye la imagen del Dockerfile en Cloud Build (unos 5-10 min la primera
# vez) y publica el servicio. Queda accesible desde internet, protegido por la
# contraseña de ~/estudio-clave.txt y no por IAM: así entra alguien que no
# tiene cuenta de Google.
#
# Volver a correrlo actualiza el servicio en su misma URL.
#
set -euo pipefail
cd "$(dirname "$0")"

GCLOUD="$HOME/google-cloud-sdk/bin/gcloud"
PROYECTO="project-030f48f6-0f61-4e51-850"
REGION="us-central1"          # nivel 1 de precios, que es el que tiene capa gratuita
SERVICIO="estudio"

[ -f "$HOME/estudio-clave.txt" ] || {
  echo "Falta ~/estudio-clave.txt con la contraseña." >&2; exit 1; }
CLAVE="$(cat "$HOME/estudio-clave.txt")"

# La clave de DeepSeek viaja igual: fuera del repo, dentro del entorno. Sin
# ella el servicio arranca y renderiza; lo único que no funciona es "Draft it",
# porque en el contenedor no hay CLI de Claude al que caerse.
DS="$(cat "$HOME/deepseek-clave.txt" 2>/dev/null || true)"
[ -n "$DS" ] || echo "Aviso: sin ~/deepseek-clave.txt, el botón Draft it queda muerto." >&2

# --memory 2Gi : el pico medido del render es 704 MiB; 1 GiB queda muy justo
# --cpu 2      : el render es CPU pura, más CPU son menos segundos facturados
# --concurrency 8 : dos renders a la vez caben en 2 GiB; el default de 80 no
# --min-instances 0 : escala a cero, no se paga por estar quieto
# --max-instances 1 : NO es un techo de gasto, es correctitud. El estudio
#   guarda las fotos y los PNG en el disco de su propia instancia, así que una
#   segunda instancia atiende con el disco vacío: el navegador pide los cuatro
#   slides en paralelo, cuatro caen en la instancia nueva y vuelven 404 — que
#   en la página se ve como imágenes rotas, unas sí y otras no. Con una sola
#   instancia el disco es siempre el mismo. Concurrency 8 alcanza de sobra para
#   una persona; el día que haya que compartirlo, el estado va a un bucket.
exec "$GCLOUD" run deploy "$SERVICIO" \
  --project "$PROYECTO" \
  --source . \
  --region "$REGION" \
  --port 8080 \
  --memory 2Gi \
  --cpu 2 \
  --concurrency 8 \
  --timeout 600 \
  --min-instances 0 \
  --max-instances 1 \
  --allow-unauthenticated \
  --set-env-vars "ESTUDIO_CLAVE=$CLAVE,DEEPSEEK_API_KEY=$DS" \
  --quiet
