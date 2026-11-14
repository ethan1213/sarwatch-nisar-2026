"""Experiment records: what was run, on which data, with which versions. Local JSON files."""
import json
import platform
import subprocess
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

TRACKED = ("numpy", "scipy", "scikit-learn", "lightgbm", "scikit-image", "rasterio", "MAPIE")


def environment():
    versions = {}
    for name in TRACKED:
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = None
    try:
        sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True, timeout=10).stdout.strip()
    except Exception:
        sha = None
    return {"python": platform.python_version(), "platform": platform.platform(), "git_sha": sha, "packages": versions}


def record(name, payload, root="experiments"):
    """Write <root>/<utc timestamp>_<name>.json and return its path. Fails on unserialisable data."""
    if not name or any(c in name for c in '/:*?"<>| ') or '\\' in name:
        raise ValueError("Nombre de experimento inválido")
    required = ("dataset", "split", "metrics")
    missing = [k for k in required if k not in payload]
    if missing:
        raise ValueError(f"El registro requiere {missing}")
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = root / f"{stamp}_{name}.json"
    body = {"name": name, "recorded_utc": datetime.now(timezone.utc).isoformat(), "environment": environment(), **payload}
    path.write_text(json.dumps(body, ensure_ascii=False, indent=2, default=_jsonable), encoding="utf-8")
    return path


def _jsonable(value):
    import numpy as np
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"No serializable: {type(value).__name__}")
