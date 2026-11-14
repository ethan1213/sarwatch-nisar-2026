"""Thermal context from GOES ABI: fixed-grid navigation, hot-spot classes, zonal statistics, anomalies.

GOES ABI measures brightness temperature in the mid-infrared (3.9 um, band 7) and thermal infrared
(11.2 um, band 14) every 10 minutes at 2 km nadir resolution. SAR does not measure temperature: these
layers are a separate, coarser observation that is never resampled into the NISAR backscatter.
"""
import numpy as np

# ABI L2 FDC "Mask" codes. 30-35 are the temporally filtered versions of 10-15.
FIRE_CLASSES = {10: "foco procesado", 11: "foco saturado", 12: "foco parcialmente cubierto por nube", 13: "probabilidad alta", 14: "probabilidad media", 15: "probabilidad baja"}
CONFIDENT_FIRE = (10, 11, 13)  # processed, saturated, high probability
CLOUD_CODES = (150, 151, 152, 153, 200, 201, 205, 210, 215, 220, 225, 230, 240, 245)
NO_FIRE_CODE = 100


def fire_class(mask):
    """Collapse FDC mask codes to 10-15 (0 = not a fire pixel)."""
    code = np.asarray(mask).astype(np.int32)
    code = np.where((code >= 30) & (code <= 35), code - 20, code)
    return np.where((code >= 10) & (code <= 15), code, 0).astype(np.int16)


def _geometry(proj):
    r_eq, r_pol = float(proj["semi_major_axis"]), float(proj["semi_minor_axis"])
    return r_eq, r_pol, float(proj["perspective_point_height"]) + r_eq, np.radians(float(proj["longitude_of_projection_origin"]))


def scan_angles(lat, lon, proj):
    """ABI fixed-grid scan angles (x east-west, y north-south, radians) of geodetic points (GRS80).

    NaN for points the satellite cannot see (behind the Earth's limb).
    """
    r_eq, r_pol, height, lon0 = _geometry(proj)
    lat, lon = np.radians(np.asarray(lat, dtype=np.float64)), np.radians(np.asarray(lon, dtype=np.float64))
    phi = np.arctan((r_pol**2 / r_eq**2) * np.tan(lat))
    r_c = r_pol / np.sqrt(1 - (1 - r_pol**2 / r_eq**2) * np.cos(phi) ** 2)
    s_x = height - r_c * np.cos(phi) * np.cos(lon - lon0)
    s_y = -r_c * np.cos(phi) * np.sin(lon - lon0)
    s_z = r_c * np.sin(phi)
    visible = height * (height - s_x) >= s_y**2 + (r_eq**2 / r_pol**2) * s_z**2
    x, y = np.arcsin(-s_y / np.sqrt(s_x**2 + s_y**2 + s_z**2)), np.arctan(s_z / s_x)
    return np.where(visible, x, np.nan), np.where(visible, y, np.nan)


def latlon(x, y, proj):
    """Geodetic latitude and longitude (degrees) of ABI scan angles; NaN off the Earth disk."""
    r_eq, r_pol, height, lon0 = _geometry(proj)
    x, y = np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.float64)
    a = np.sin(x) ** 2 + np.cos(x) ** 2 * (np.cos(y) ** 2 + (r_eq**2 / r_pol**2) * np.sin(y) ** 2)
    b = -2 * height * np.cos(x) * np.cos(y)
    with np.errstate(invalid="ignore"):
        r_s = (-b - np.sqrt(b**2 - 4 * a * (height**2 - r_eq**2))) / (2 * a)
    s_x, s_y, s_z = r_s * np.cos(x) * np.cos(y), -r_s * np.sin(x), r_s * np.cos(x) * np.sin(y)
    lat = np.degrees(np.arctan((r_eq**2 / r_pol**2) * s_z / np.sqrt((height - s_x) ** 2 + s_y**2)))
    return lat, np.degrees(lon0 - np.arctan(s_y / (height - s_x)))


def aoi_window(bbox, axis_x, axis_y, proj, pad=1):
    """(row0, row1, col0, col1) of the fixed grid covering a WGS84 bbox.

    axis_x and axis_y are (scale, offset, size) of the file's x and y coordinates; pad adds whole pixels.
    """
    west, south, east, north = bbox
    lons, lats = np.meshgrid(np.linspace(west, east, 9), np.linspace(south, north, 9))
    x, y = scan_angles(lats, lons, proj)
    cols, rows = (x - axis_x[1]) / axis_x[0], (y - axis_y[1]) / axis_y[0]
    if not (np.isfinite(cols).all() and np.isfinite(rows).all()):
        raise ValueError("AOI fuera del disco visible del satélite")
    row0, row1 = int(np.floor(rows.min())) - pad, int(np.ceil(rows.max())) + pad + 1
    col0, col1 = int(np.floor(cols.min())) - pad, int(np.ceil(cols.max())) + pad + 1
    if row0 < 0 or col0 < 0 or row1 > axis_y[2] or col1 > axis_x[2]:
        raise ValueError("AOI fuera de la grilla del producto")
    return row0, row1, col0, col1


def window_geometry(window, axis_x, axis_y, proj):
    """Centre lat/lon (ny, nx) and corner lat/lon (ny+1, nx+1) of the pixels of a window."""
    row0, row1, col0, col1 = window
    xc, yc = axis_x[1] + axis_x[0] * np.arange(col0, col1), axis_y[1] + axis_y[0] * np.arange(row0, row1)
    xe, ye = axis_x[1] + axis_x[0] * (np.arange(col0, col1 + 1) - 0.5), axis_y[1] + axis_y[0] * (np.arange(row0, row1 + 1) - 0.5)
    lat, lon = latlon(*np.meshgrid(xc, yc), proj)
    corner_lat, corner_lon = latlon(*np.meshgrid(xe, ye), proj)
    return lat, lon, corner_lat, corner_lon


def footprint_km(corner_lat, corner_lon):
    """Approximate east-west and north-south ground size (km) of each pixel from its corners."""
    lat_mid = np.radians((corner_lat[:-1, :-1] + corner_lat[1:, 1:]) / 2)
    width = np.abs(corner_lon[:-1, 1:] - corner_lon[:-1, :-1]) * 111.32 * np.cos(lat_mid)
    height = np.abs(corner_lat[1:, :-1] - corner_lat[:-1, :-1]) * 110.57
    return width, height


def decode(raw, attrs):
    """Apply _Unsigned, _FillValue, scale_factor and add_offset of a netCDF variable; fill becomes NaN."""
    raw = np.asarray(raw)
    unsigned = str(attrs.get("_Unsigned", "")).lower() in ("true", "b'true'")
    if unsigned and raw.dtype.kind == "i":
        raw = raw.view(raw.dtype.str.replace("i", "u"))
    values = raw.astype(np.float32)
    fill = attrs.get("_FillValue")
    if fill is not None:
        fill = np.asarray(fill).ravel()[0]
        if unsigned and np.asarray(fill).dtype.kind == "i":
            fill = np.asarray(fill).view(np.asarray(fill).dtype.str.replace("i", "u"))
        values[raw == fill] = np.nan
    scale, offset = attrs.get("scale_factor"), attrs.get("add_offset")
    if scale is not None:
        values = values * np.float32(np.asarray(scale).ravel()[0]) + np.float32(np.asarray(offset if offset is not None else 0).ravel()[0])
    return values


def zonal_stats(values, zones, statistics=("mean", "max", "count")):
    """Per-zone statistics of a 2D field; zones is an integer raster, negative ids are ignored."""
    values, zones = np.asarray(values, dtype=np.float64), np.asarray(zones)
    if values.shape != zones.shape:
        raise ValueError("Valores y zonas con distinta grilla")
    out = {}
    for zone in np.unique(zones[zones >= 0]):
        sample = values[(zones == zone) & np.isfinite(values)]
        row = {"count": int(sample.size)}
        if "mean" in statistics:
            row["mean"] = float(sample.mean()) if sample.size else None
        if "max" in statistics:
            row["max"] = float(sample.max()) if sample.size else None
        out[int(zone)] = row
    return out


def hourly_anomaly(cube, hours, min_samples=5):
    """Robust anomaly of each pixel against its own median for the same UTC hour.

    cube is (time, y, x); hours the UTC hour of each time step. Returns (cube - median) / (1.4826 MAD);
    NaN where fewer than min_samples valid observations exist for that pixel and hour or MAD is zero.
    The diurnal cycle dominates surface temperature, so a pixel is only compared with itself at the same hour.
    """
    cube, hours = np.asarray(cube, dtype=np.float32), np.asarray(hours)
    if cube.shape[0] != hours.shape[0]:
        raise ValueError("Una hora por paso de tiempo")
    out = np.full(cube.shape, np.nan, dtype=np.float32)
    for hour in np.unique(hours):
        index = np.flatnonzero(hours == hour)
        sample = cube[index]
        count = np.isfinite(sample).sum(axis=0)
        with np.errstate(all="ignore"):
            median = np.nanmedian(sample, axis=0)
            mad = 1.4826 * np.nanmedian(np.abs(sample - median), axis=0)
            score = (sample - median) / mad
        score[:, (count < min_samples) | ~(mad > 0)] = np.nan
        out[index] = score
    return out
