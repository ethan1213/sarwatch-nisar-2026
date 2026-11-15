# SARWatch — Biobío fire evidence

SARWatch is an independent satellite evidence explorer for the Biobío region of Chile. Its public interface follows three questions: what happened, what remains, and what can we anticipate?

The January 2026 replay combines hourly GOES-19 thermal anomalies with ERA5 weather context. Each cell is a satellite observation area, not a fire perimeter. A separate recent-detections view uses a saved FIRMS VIIRS query; it is explicitly not a continuous live feed. Current weather forecasts are labelled as model output.

Sentinel-2 optical composites provide a burn-signal reference. NISAR L-band GCOV imagery from February, June and October supports exploration of the subsequent terrain signal. There is no pre-January NISAR acquisition of the same geometry in the selected series, so this is not a radar comparison before and after that fire. Optical burn signals can also reflect seasonal drying, harvest or land-use changes.

An exploratory surveillance-priority model is evaluated on held-out dates and spatial blocks. The interface exposes its limited performance rather than presenting an operational forecast. No language model generates scientific measurements.

React and MapLibre are served by FastAPI on Google Cloud Run. Source data lineage, reproducible scripts, model cards and evaluation reports accompany the code. Credentials and original HDF5 downloads are excluded from the repository.

The project does not provide emergency alerts, safe access routes, confirmed fire boundaries or certified emissions. It is not sponsored or endorsed by NASA, ISRO or NOAA.
