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

# Un secreto guardado en un archivo del home. Se ignoran las lineas en blanco
# y las que empiezan con #, asi que el archivo puede llevar sus instrucciones
# dentro; el token es la primera linea que no sea comentario. Un # en medio de
# una contrasena sobrevive: solo se descarta la linea que *empieza* con el.
llave() { grep -vE '^[[:space:]]*(#|$)' "$1" 2>/dev/null | head -n1 | tr -d '\r\n'; }

CLAVE="$(llave "$HOME/estudio-clave.txt")"
[ -n "$CLAVE" ] || { echo "Falta ~/estudio-clave.txt con la contraseña." >&2; exit 1; }

# La clave de DeepSeek viaja igual: fuera del repo, dentro del entorno. Sin
# ella el servicio arranca y renderiza; lo único que no funciona es "Draft it",
# porque en el contenedor no hay CLI de Claude al que caerse.
DS="$(llave "$HOME/deepseek-clave.txt")"
[ -n "$DS" ] || echo "Aviso: sin ~/deepseek-clave.txt, el botón Draft it queda muerto." >&2

# Y el token de Instagram, por el mismo camino: en un archivo del home, nunca en
# el repo. Sin él el estudio arranca y hace carruseles; lo único que no funciona
# es el botón de publicar, que responde "Falta IG_TOKEN en el entorno".
IG="$(llave "$HOME/ig-token.txt")"
[ -n "$IG" ] || echo "Aviso: sin ~/ig-token.txt, el botón Publicar queda muerto." >&2

# Las credenciales de Drive no son un botón aparte: son la fuente de fotos por
# defecto de cada oferta con placa (ver drive_fotos.py). ~/drive-clave.txt
# tiene tres lineas -- client_id, client_secret, refresh_token -- las deja
# drive_autorizar.py. Sin ellas el estudio sigue levantando, pero cualquier
# oferta con placa se cae al pedir las fotos, no solo un boton.
drive_linea() { sed -n "${2}p" "$1" 2>/dev/null | tr -d '\r\n'; }
DRIVE_ID="$(drive_linea "$HOME/drive-clave.txt" 1)"
DRIVE_SECRET="$(drive_linea "$HOME/drive-clave.txt" 2)"
DRIVE_REFRESH="$(drive_linea "$HOME/drive-clave.txt" 3)"
[ -n "$DRIVE_ID" ] && [ -n "$DRIVE_SECRET" ] && [ -n "$DRIVE_REFRESH" ] || \
  echo "Aviso: ~/drive-clave.txt incompleto, las fotos por placa van a fallar." >&2

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
  --set-env-vars "ESTUDIO_CLAVE=$CLAVE,DEEPSEEK_API_KEY=$DS,IG_TOKEN=$IG,DRIVE_CLIENT_ID=$DRIVE_ID,DRIVE_CLIENT_SECRET=$DRIVE_SECRET,DRIVE_REFRESH_TOKEN=$DRIVE_REFRESH" \
  --quiet
