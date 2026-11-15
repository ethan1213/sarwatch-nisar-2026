# Textos preparados para el formulario Space Apps

## Project Name
SARWatch — Satellite Evidence for Wildfire Analysis

## Summary
SARWatch brings satellite evidence about wildfires into an interactive map focused on Chile. Users can explore thermal detections from NASA FIRMS and NOAA GOES, inspect weather forecasts, compare Sentinel-2 observations before and after a fire, and follow later land-surface changes with NASA–ISRO NISAR radar.

Our Biobío case combines the January 2026 fire record with official Copernicus mapped extents and NISAR observations acquired in subsequent months. A separate Viña del Mar case compares Sentinel-2 imagery around the February 2024 fire. Sources and acquisition dates remain visible throughout the application.

The project makes complex Earth-observation data easier to inspect and export. An exploratory model ranks cells for surveillance; it does not predict fire trajectories or safe routes. By distinguishing observations, weather estimates and model limitations, SARWatch provides a reproducible foundation for further research and review with emergency specialists.

## Project
https://sarwatch-525550511866.southamerica-west1.run.app/

## Project Demonstration
Pendiente: la demo existente dura 117 segundos y no cumple el máximo de 30 segundos. No usar ese enlace como entrega definitiva.

## Project Details
SARWatch connects a React and MapLibre interface to a Python FastAPI service hosted on Google Cloud Run. Reproducible processing scripts prepare satellite layers and provenance records, while Google Cloud Storage holds derived NISAR products.

Users select an area and an evidence layer: thermal detections, weather, optical burn signals, NISAR evolution, official mapped extents, terrain or exploratory surveillance priority. Maps retain acquisition dates and sources. Evidence can be exported as JSON. The Biobío NISAR series contains observations after the January fire; the application does not describe these as pre-fire measurements. Viña 2024 optical imagery is kept separate from NISAR observations in 2026.

The surveillance model is evaluated on held-out dates (ROC AUC 0.632; 44 positive cases). These results do not establish operational performance or calibrated fire probabilities. Propagation remains disabled pending fuel, fuel-moisture, terrain and wind inputs and independent validation. Weather-relative sectors are geographic context and do not identify safe access routes.

The intended benefit is accessible, traceable analysis for researchers and future collaboration with emergency specialists. The contribution combines multiple observation timescales in one interface while exposing uncertainty. The public repository contains Apache-2.0 project code; third-party data and libraries retain their own terms.

## Use of Super Intelligence — texto de apoyo
Claude Code and OpenAI Codex assisted with programming, debugging, documentation and interface development. The adapted Figma Make design is identified as an AI-assisted design reference. The SVG logo is code authored with AI assistance. Satellite observations are provider data, not AI-generated observations. Derived layers and model outputs are produced by reproducible processing scripts. The published application does not call an external language model. The earlier narrated demonstration uses explicitly disclosed Windows synthetic speech. Select the actual matching options shown by the form; do not claim that no SI was used.

## Cifras del incendio
El resumen preparado omite fallecidos y viviendas porque no se ha identificado el informe oficial exacto que respalda las cifras del texto anterior. Si el equipo desea incluirlas, añadir informe SENAPRED/CONAF, fecha de corte y ámbito territorial.

## Declaraciones finales
Las casillas de términos y originalidad son declaraciones del equipo. Revisar las atribuciones antes de confirmar la entrega. Este archivo prepara los campos; no certifica que el formulario haya sido enviado.
