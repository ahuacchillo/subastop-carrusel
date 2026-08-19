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

# --memory 2Gi : el pico medido del render es 704 MiB; 1 GiB queda muy justo
# --cpu 2      : el render es CPU pura, más CPU son menos segundos facturados
# --concurrency 8 : dos renders a la vez caben en 2 GiB; el default de 80 no
# --min-instances 0 : escala a cero, no se paga por estar quieto
# --max-instances 3 : techo de gasto si algo se desboca
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
  --max-instances 3 \
  --allow-unauthenticated \
  --set-env-vars "ESTUDIO_CLAVE=$CLAVE" \
  --quiet
