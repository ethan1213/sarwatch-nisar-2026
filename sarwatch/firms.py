"""FIRMS CSV normalization. Hotspot detections are not incident or burned-area labels."""
import csv
import io
import math


def parse_csv(text, sensor, bbox):
    reader = csv.DictReader(io.StringIO(text))
    required = {'latitude', 'longitude', 'acq_date', 'acq_time', 'confidence', 'frp'}
    if not required.issubset(reader.fieldnames or []):
        raise ValueError('Respuesta FIRMS sin las columnas esperadas')
    west, south, east, north = bbox
    detections, seen = [], set()
    for row in reader:
        try:
            lat, lon = float(row['latitude']), float(row['longitude'])
            frp = float(row['frp']) if row['frp'] else None
            if not math.isfinite(lat) or not math.isfinite(lon) or not (west <= lon <= east and south <= lat <= north):
                continue
            time = row['acq_time'].zfill(4)
            if len(time) != 4 or not time.isdigit() or int(time[:2]) > 23 or int(time[2:]) > 59:
                raise ValueError('Hora UTC inválida')
            utc = row['acq_date'] + 'T' + time[:2] + ':' + time[2:] + ':00Z'
            confidence = row['confidence'].lower()
            confidence = {'low': 'l', 'nominal': 'n', 'high': 'h'}.get(confidence, confidence)
            if confidence not in {'l', 'n', 'h'}:
                raise ValueError('Confianza VIIRS no reconocida')
            key = (sensor, utc, lat, lon)
            if key in seen:
                continue
            seen.add(key)
            detections.append({'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [lon, lat]},
                               'properties': {'sensor': sensor, 'utc': utc, 'confidence': confidence,
                                              'frp_mw': frp if frp is not None and math.isfinite(frp) else None,
                                              'product_version': row.get('version'), 'nominal_pixel_m': 375}})
        except (TypeError, KeyError, ValueError) as exc:
            raise ValueError('Fila FIRMS inválida; no se publica una descarga parcial') from exc
    return detections
