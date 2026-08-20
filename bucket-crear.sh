#!/usr/bin/env bash
#
# Crea el bucket donde van los PNG que Meta descarga al publicar. UNA vez.
#
#   ./bucket-crear.sh
#
# Por que hace falta un bucket y no basta el propio estudio: la Graph API no
# acepta que le subamos los bytes de una imagen, descarga cada una desde una URL
# publica. El estudio esta entero detras de una clave —escribe archivos y lanza
# un renderizador, exponerlo abierto seria regalar las dos cosas— asi que Meta no
# puede leer sus PNG. Y el disco de la instancia muere con ella.
#
set -euo pipefail

GCLOUD="$HOME/google-cloud-sdk/bin/gcloud"
PROYECTO="project-030f48f6-0f61-4e51-850"
REGION="us-central1"
BUCKET="${PROYECTO}-carrusel"

# Lectura publica para cualquiera. No es un descuido: estas imagenes se van a
# publicar en Instagram en el minuto siguiente, asi que su secreto dura eso. La
# alternativa —URLs firmadas— pide una llave RSA de servicio guardada en algun
# disco, que es un secreto de verdad y con consecuencias de verdad si se filtra.
#
# ponytail: objetos publicos. Si algun dia hay que publicar algo que no sea
#           contenido de marketing, aca van URLs firmadas.
$GCLOUD storage buckets create "gs://$BUCKET" \
  --project="$PROYECTO" \
  --location="$REGION" \
  --uniform-bucket-level-access \
  --no-public-access-prevention

$GCLOUD storage buckets add-iam-policy-binding "gs://$BUCKET" \
  --member=allUsers --role=roles/storage.objectViewer

# Se borran solos a los 7 dias. Ningun codigo de limpieza que escribir, ninguna
# tarea que se olvide: un carrusel ya publicado no le sirve a nadie en el bucket,
# el original queda en Posts/ y el publicado queda en Instagram.
TMP="$(mktemp)"
cat > "$TMP" <<'JSON'
{"lifecycle":{"rule":[{"action":{"type":"Delete"},"condition":{"age":7}}]}}
JSON
$GCLOUD storage buckets update "gs://$BUCKET" --lifecycle-file="$TMP"
rm -f "$TMP"

# La cuenta de servicio de Cloud Run escribe con el rol que ya tiene en el
# proyecto; en la laptop se escribe con la sesion de gcloud. Ninguna de las dos
# necesita una llave en el repo.
echo
echo "  ✓ gs://$BUCKET"
echo "    Ponlo en el entorno del estudio si cambias de bucket:"
echo "      BUCKET_CARRUSEL=$BUCKET"
