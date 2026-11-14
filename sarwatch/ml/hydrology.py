"""D8 flow routing from a DEM: flow direction, flow accumulation and a simple sub-basin label.

Standard, deterministic algorithm (steepest single-direction descent, elevation-sorted
accumulation; cf. Jenson & Domingue 1988 for the flat/pit-handling literature — pits are
treated here as sinks, not filled, which is the conservative choice for a hazard proxy).
Runs on a coarsened grid by default: flow accumulation at native 20 m over a full AOI is not
needed to rank which sub-basins concentrate water fastest, and coarsening keeps this fast
in pure Python/NumPy without extra dependencies.
"""
import numpy as np

NEIGHBORS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
DISTANCE_FACTOR = [np.sqrt(2), 1, np.sqrt(2), 1, 1, np.sqrt(2), 1, np.sqrt(2)]
NO_DIRECTION = -1


def coarsen_mean(values, factor):
    """Block-mean downsample by an integer factor; edges that don't divide evenly are trimmed."""
    values = np.asarray(values, dtype=np.float64)
    if factor < 1:
        raise ValueError("factor debe ser >= 1")
    if factor == 1:
        return values.copy()
    rows = (values.shape[0] // factor) * factor
    cols = (values.shape[1] // factor) * factor
    trimmed = values[:rows, :cols]
    with np.errstate(invalid="ignore"):
        blocks = trimmed.reshape(rows // factor, factor, cols // factor, factor)
        return np.nanmean(blocks, axis=(1, 3))


def flow_direction(dem):
    """Index 0-7 into NEIGHBORS of the steepest downslope neighbor, or NO_DIRECTION for a sink/edge/NaN."""
    dem = np.asarray(dem, dtype=np.float64)
    rows, cols = dem.shape
    direction = np.full(dem.shape, NO_DIRECTION, dtype=np.int8)
    steepest = np.zeros(dem.shape, dtype=np.float64)
    for k, (dr, dc) in enumerate(NEIGHBORS):
        shifted = np.full(dem.shape, np.nan)
        src_r0, src_r1 = max(0, dr), rows + min(0, dr)
        src_c0, src_c1 = max(0, dc), cols + min(0, dc)
        dst_r0, dst_r1 = max(0, -dr), rows + min(0, -dr)
        dst_c0, dst_c1 = max(0, -dc), cols + min(0, -dc)
        shifted[dst_r0:dst_r1, dst_c0:dst_c1] = dem[src_r0:src_r1, src_c0:src_c1]
        drop = dem - shifted
        slope = drop / DISTANCE_FACTOR[k]
        better = np.isfinite(slope) & (slope > steepest)
        direction[better] = k
        steepest[better] = slope[better]
    direction[~np.isfinite(dem)] = NO_DIRECTION
    return direction


def flow_accumulation(dem, direction=None):
    """Number of upstream cells draining through each cell (including itself); NaN DEM -> 0.

    Processes cells in decreasing elevation order so every upstream contribution is added to a
    cell before that cell's own (now-complete) total is passed to its downstream neighbor.
    """
    dem = np.asarray(dem, dtype=np.float64)
    if direction is None:
        direction = flow_direction(dem)
    rows, cols = dem.shape
    accumulation = np.isfinite(dem).astype(np.float64)
    finite = np.isfinite(dem)
    order = np.argsort(-np.where(finite, dem, -np.inf).ravel(), kind="stable")
    flat_dem = dem.ravel()
    flat_dir = direction.ravel()
    flat_acc = accumulation.ravel()
    for idx in order:
        if not np.isfinite(flat_dem[idx]):
            continue
        k = flat_dir[idx]
        if k == NO_DIRECTION:
            continue
        dr, dc = NEIGHBORS[k]
        r, c = divmod(idx, cols)
        tr, tc = r + dr, c + dc
        if 0 <= tr < rows and 0 <= tc < cols:
            flat_acc[tr * cols + tc] += flat_acc[idx]
    return accumulation


def outlets(direction, accumulation, min_accumulation):
    """Cells whose accumulation exceeds a threshold and that are themselves a sink or whose
    downstream neighbor does not clear the threshold (i.e. the highest point of a channel)."""
    rows, cols = direction.shape
    candidates = np.argwhere(accumulation >= min_accumulation)
    if candidates.size == 0:
        return np.zeros((0, 2), dtype=int)
    return candidates


def subbasin_labels(direction, seed_mask):
    """Label every cell with the id of the first seed cell reached by following flow direction
    downstream from it (iterative path-following with memoisation); 0 = no seed reached."""
    rows, cols = direction.shape
    seed_id = np.zeros(direction.shape, dtype=np.int32)
    seed_id[seed_mask] = np.arange(1, int(seed_mask.sum()) + 1)
    labels = seed_id.copy()  # seed cells are their own basin outlet; the walk below never visits them
    for r in range(rows):
        for c in range(cols):
            if labels[r, c] or seed_id[r, c]:
                continue
            path = []
            rr, cc = r, c
            while True:
                if seed_id[rr, cc]:
                    label = seed_id[rr, cc]
                    break
                if labels[rr, cc]:
                    label = labels[rr, cc]
                    break
                path.append((rr, cc))
                k = direction[rr, cc]
                if k == NO_DIRECTION:
                    label = 0
                    break
                dr, dc = NEIGHBORS[k]
                nr, nc = rr + dr, cc + dc
                if not (0 <= nr < rows and 0 <= nc < cols):
                    label = 0
                    break
                rr, cc = nr, nc
            for pr, pc in path:
                labels[pr, pc] = label
    return labels
