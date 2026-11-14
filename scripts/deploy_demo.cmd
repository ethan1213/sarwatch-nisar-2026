@echo off
rem Reconstruye la imagen de demo y la publica en Cloud Run. Ejecutar desde la raiz del repo con Docker Desktop encendido.
rem Uso: scripts\deploy_demo.cmd [ID_PROYECTO]
setlocal
set PROJECT=%1
if "%PROJECT%"=="" set PROJECT=sarwatch-nisar-demo
set REGION=southamerica-west1
set IMAGE=%REGION%-docker.pkg.dev/%PROJECT%/sarwatch/app:demo
if not exist data\manifest.json (echo Falta data\manifest.json & exit /b 1)
git pull || exit /b 1
docker compose build || exit /b 1
docker build -f Dockerfile.deploy -t sarwatch-nisar:demo . || exit /b 1
docker tag sarwatch-nisar:demo %IMAGE% || exit /b 1
docker push %IMAGE% || exit /b 1
gcloud run deploy sarwatch --project %PROJECT% --image %IMAGE% --region %REGION% --port 8080 --memory 2Gi --cpu 2 --min-instances 1 --max-instances 2 --session-affinity --timeout 3600 --allow-unauthenticated
