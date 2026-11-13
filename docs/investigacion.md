# Investigación — 13 noviembre 2026

## Continuidad

Se revisó el chat «Crear carpeta de investigación NASA». Había catálogo y diseño local con siete escenas GCOV Pantanal verificadas en octubre. Se recuperaron catálogo y documentación sin copiar los 13 GB al nuevo Git. IDs/fechas/hashes provienen de ese inventario; no se afirma una nueva verificación completa de hashes si no se ejecutó.

## Desafío y premios

Enunciado aportado y página del equipo: Dancing with the SARs 2026, app interactiva NISAR y comunicación de cambios de superficie. Solicita resultado abierto; resolver licencia/acceso antes de entregar, manteniendo privado ahora por instrucción del propietario.

La página oficial de premios se consultó en navegador (el extractor web falló). Distingue diez categorías y selección local/global. Orientación propuesta: uso válido de ciencia, acceso a datos y relato ambiental; no es garantía de premio ni regla universal de estilo de código.

## Datos

ASF recomienda GCOV para exploración de retrodispersión GIS. HHHH/HVHV son intensidades: 10 log10 para dB, no 20 log10. frequencyA/frequencyB del LSAR son subbandas; no equivalen a L/S.

Preservar VALIDATED/PROVISIONAL/BETA y versión. Earthdata Login para descarga autenticada. Harmony puede proporcionar extracción COG según producto/servicio disponible. S3 directo tiene restricciones de región us-west-2; derivados propios evitan imponer esa región al visor.

## GitHub NASA

Se consultaron NASA, Earthdata Search y CONTRIBUTING. No se encontró un único estilo de código preferido por NASA. Earthdata Search es referencia de descubrimiento/visualización. Sus reglas de discusión previa y tickets EDSC son específicas para contribuir a ese repositorio; no se copian a SARWatch.

Adoptamos funciones científicas pequeñas, unidades explícitas, pruebas de nodata/diferencias, contratos, trazabilidad y revisión por PR. ISCE3 es referencia InSAR avanzada; no es necesaria para visualizar GCOV geocodificado.

## Equipo

Software Detective: sesión activa de propietario, seis miembros, cupos completos y ninguna solicitud pendiente. No se muestran correos de los demás. No copiar contactos privados al repositorio ni asumir equivalencia de alias con GitHub. Invitaciones pendientes de cuentas verificadas.

## Fuentes primarias

- https://www.spaceappschallenge.org/2026/challenges/dancing-with-the-sars/
- https://www.spaceappschallenge.org/awards/
- https://github.com/nasa
- https://github.com/nasa/earthdata-search
- https://github.com/nasa/earthdata-search/blob/main/CONTRIBUTING.md
- https://github.com/isce-framework/isce3
- https://nisar-docs.asf.alaska.edu/using-overview/
- https://nisar-docs.asf.alaska.edu/asf-search/
- https://nisar-docs.asf.alaska.edu/earthdata-search/
- https://nisar-docs.asf.alaska.edu/earthaccess/
