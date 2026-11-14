"""Windowed CPU inference for an exported segmentation model (ONNX). The model is optional and evaluated
with scripts/evaluate_detection.py before it may be shown; this module only runs it tile by tile."""
import numpy as np

NODATA = 255


def normalize_channels(stack, means, stds):
    """(C, H, W) float32 standardisation with NaN preserved."""
    stack = np.asarray(stack, dtype=np.float32)
    means = np.asarray(means, dtype=np.float32)[:, None, None]
    stds = np.asarray(stds, dtype=np.float32)[:, None, None]
    if stack.shape[0] != means.shape[0]:
        raise ValueError("Canales y estadísticas de normalización no coinciden")
    return (stack - means) / stds


def windows(height, width, size=512, overlap=64):
    """Yield (row0, row1, col0, col1) covering the grid with overlap; edges are clipped, never padded silently."""
    if size <= overlap:
        raise ValueError("size debe superar overlap")
    step = size - overlap
    rows = list(range(0, max(height - size, 0) + 1, step))
    cols = list(range(0, max(width - size, 0) + 1, step))
    if rows[-1] + size < height:
        rows.append(height - size)
    if cols[-1] + size < width:
        cols.append(width - size)
    for r in rows:
        for c in cols:
            yield r, min(r + size, height), c, min(c + size, width)


def predict_tiles(run, stack, size=512, overlap=64, threshold=0.5):
    """Run `run(tile) -> probability (h, w)` over overlapping windows; average overlaps; NaN inputs -> NODATA.

    `run` receives a (C, h, w) float32 tile with NaN replaced by 0 and must return water probabilities.
    Returns (probability, mask) where mask is uint8 1/0/255.
    """
    stack = np.asarray(stack, dtype=np.float32)
    _, height, width = stack.shape
    valid = np.isfinite(stack).all(axis=0)
    accum = np.zeros((height, width), dtype=np.float32)
    count = np.zeros((height, width), dtype=np.float32)
    for r0, r1, c0, c1 in windows(height, width, size, overlap):
        tile = np.nan_to_num(stack[:, r0:r1, c0:c1], nan=0.0)
        proba = np.asarray(run(tile), dtype=np.float32)
        if proba.shape != (r1 - r0, c1 - c0):
            raise ValueError("La salida del modelo no coincide con la ventana")
        accum[r0:r1, c0:c1] += proba
        count[r0:r1, c0:c1] += 1
    with np.errstate(invalid="ignore", divide="ignore"):
        probability = np.where(count > 0, accum / count, np.nan)
    probability[~valid] = np.nan
    mask = np.full((height, width), NODATA, dtype=np.uint8)
    mask[valid] = (probability[valid] > threshold).astype(np.uint8)
    return probability.astype(np.float32), mask


def onnx_runner(model_path, input_name=None):
    """Return run(tile) for an ONNX model expecting (1, C, h, w) and producing logits or probabilities (1, 1|2, h, w)."""
    import onnxruntime as ort
    session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
    name = input_name or session.get_inputs()[0].name

    def run(tile):
        output = session.run(None, {name: tile[None].astype(np.float32)})[0]
        if output.ndim == 4 and output.shape[1] == 2:
            logits = output[0]
            exp = np.exp(logits - logits.max(axis=0, keepdims=True))
            return (exp / exp.sum(axis=0, keepdims=True))[1]
        values = output[0, 0] if output.ndim == 4 else output[0]
        return 1 / (1 + np.exp(-values)) if values.min() < 0 or values.max() > 1 else values

    return run
