#!/usr/bin/env bash
# Deploy SARWatch from Google Cloud Shell (browser, already signed in). No keys are typed or stored.
#
#   bash scripts/deploy_cloudshell.sh
#
# It reuses the image the service runs today (verified derivatives baked in) and replaces code, catalog,
# docs and the React build. Without a previous image it publishes the API-only image: Mundo, Chile and
# the fire story work; Pantanal, Santiago and Valparaíso need the data snapshot (scripts/deploy_gcp.ps1).
# An existing service keeps its limits (1 CPU, 2 GiB, 0-2 instances). It never touches billing.
set -euo pipefail
PROJECT="${PROJECT:-project-6fff6574-07af-4183-b83}"
REGION="${REGION:-southamerica-west1}"
SERVICE="${SERVICE:-sarwatch}"
# MIN_INSTANCES=1 bash scripts/deploy_cloudshell.sh keeps one instance warm for the jury; rerun with 0 afterwards.
cd "$(dirname "$0")/.."
test -f catalog/fire_story/story.json || { echo "Falta catalog/fire_story/story.json"; exit 1; }
mkdir -p deploy_data && touch deploy_data/.keep
gcloud config set project "$PROJECT" >/dev/null
REGISTRY="$REGION-docker.pkg.dev"
IMAGE="$REGISTRY/$PROJECT/sarwatch/app:$(date -u +%Y%m%d-%H%M%S)"
SNAPSHOT="${SNAPSHOT:-$(gcloud run services describe "$SERVICE" --region "$REGION" --format='value(spec.template.spec.containers[0].image)' 2>/dev/null || true)}"
gcloud auth configure-docker "$REGISTRY" --quiet
if [ -n "$SNAPSHOT" ]; then
  echo "Imagen base con datos: $SNAPSHOT"
  docker build -f Dockerfile.update --build-arg "SNAPSHOT=$SNAPSHOT" -t "$IMAGE" .
  docker push "$IMAGE"
  # An existing service keeps its variables, volume, identity and limits: only the image changes.
  gcloud run deploy "$SERVICE" --region "$REGION" --image "$IMAGE" --quiet
else
  echo "No hay servicio publicado: se construye la imagen sin instantánea de datos (Dockerfile.api)."
  docker build -f Dockerfile.api -t "$IMAGE" .
  docker push "$IMAGE"
  gcloud run deploy "$SERVICE" --region "$REGION" --image "$IMAGE" --port 8080 --cpu 1 --memory 2Gi --concurrency 4 \
    --min-instances 0 --max-instances 2 --timeout 180 --cpu-throttling --allow-unauthenticated --quiet \
    --set-env-vars=DATA_DIR=/app/data,ASSISTANT_LLM=none
fi
if [ -n "${MIN_INSTANCES:-}" ]; then gcloud run services update "$SERVICE" --region "$REGION" --min-instances "$MIN_INSTANCES" --quiet; fi
URL="$(gcloud run services describe "$SERVICE" --region "$REGION" --format='value(status.url)')"
echo "Publicado: $URL"
curl -fsS "$URL/api/health" && echo && curl -fsS "$URL/api/fire/story" | head -c 200 && echo
echo "Comprobación completa (requiere la instantánea de datos): python3 scripts/check_api.py $URL"
