#!/usr/bin/env bash
#
# Permiso que le falta a Cloud Build. Se corre UNA vez, antes del primer
# ./desplegar.sh.
#
# El problema: Cloud Build construye usando la cuenta de servicio por defecto
# de Compute, y en los proyectos creados en los últimos años Google ya no le
# asigna roles automáticamente. Nace con cero permisos, así que no puede leer
# el ZIP con el código que el propio deploy acaba de subir, y falla con:
#
#   403 ... does not have storage.objects.get access ...
#
# El rol que se concede es el que Google documenta para esto. Cubre justo tres
# cosas y ninguna más: leer las fuentes del bucket, escribir los logs del
# build, y publicar la imagen en Artifact Registry.
#
set -euo pipefail

GCLOUD="$HOME/google-cloud-sdk/bin/gcloud"
PROYECTO="project-030f48f6-0f61-4e51-850"
CUENTA="274443599629-compute@developer.gserviceaccount.com"

echo "Concediendo roles/cloudbuild.builds.builder a:"
echo "  $CUENTA"
echo "en el proyecto $PROYECTO"
echo

"$GCLOUD" projects add-iam-policy-binding "$PROYECTO" \
  --member="serviceAccount:$CUENTA" \
  --role="roles/cloudbuild.builds.builder" \
  --condition=None \
  --format="value(etag)" > /dev/null

echo "Listo. Ahora: ./desplegar.sh"
