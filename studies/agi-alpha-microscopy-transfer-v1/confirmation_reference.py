import time

import numpy as np
from scipy import ndimage


def conventional_prepare(labels, spacing):
    started = time.perf_counter()
    ids = np.unique(labels)
    ids = ids[ids != 0]
    ones = np.ones(labels.shape, dtype=np.uint8)
    counts = np.atleast_1d(ndimage.sum_labels(ones, labels=labels, index=ids))
    centroids = np.asarray(ndimage.center_of_mass(ones, labels=labels, index=ids))
    if not len(ids):
        centroids = np.empty((0, labels.ndim))
    return {
        "ids": ids,
        "counts": counts,
        "centroids": centroids * np.asarray(spacing),
        "native_measures": counts * np.prod(spacing),
        "elapsed_seconds": time.perf_counter() - started,
    }


def conventional_map(prepared, linear, translation):
    started = time.perf_counter()
    objects = []
    for label, count, center, volume in zip(
        prepared["ids"], prepared["counts"], prepared["centroids"], prepared["native_measures"], strict=True
    ):
        objects.append({
            "label_id": int(label),
            "voxel_count": int(count),
            "native_measure": float(volume),
            "mapped_measure": float(volume * abs(np.linalg.det(linear))),
            "native_centroid_um": center.tolist(),
            "mapped_centroid_um": (linear @ center + translation).tolist(),
        })
    return {"status": "ACCEPT", "label_count": len(objects), "objects": objects,
            "elapsed_seconds": time.perf_counter() - started}


def coordinate_prepare(labels, spacing):
    result = {}
    for label in np.unique(labels):
        if label != 0:
            points = np.argwhere(labels == label).astype(np.float64) * np.asarray(spacing)
            result[int(label)] = points
    return result


def coordinate_reference(points_by_label, spacing, linear, translation):
    native_voxel = float(spacing[0] * spacing[1] * spacing[2])
    basis = linear @ np.diag(spacing)
    mapped_voxel = abs(float(np.dot(basis[:, 0], np.cross(basis[:, 1], basis[:, 2]))))
    objects = []
    for label, points in points_by_label.items():
        transformed_points = points @ linear.T + translation
        objects.append({
            "label_id": label,
            "voxel_count": len(points),
            "native_measure": len(points) * native_voxel,
            "mapped_measure": len(points) * mapped_voxel,
            "native_centroid_um": points.mean(axis=0).tolist(),
            "mapped_centroid_um": transformed_points.mean(axis=0).tolist(),
        })
    return {"status": "ACCEPT", "label_count": len(objects), "objects": objects}


def compare(result, reference):
    if result.get("status") != "ACCEPT":
        return {"passed": False, "reason": "result_not_accepted", "status": result.get("status")}
    actual = {r["label_id"]: r for r in result["objects"]}
    wanted = {r["label_id"]: r for r in reference["objects"]}
    if len(actual) != len(result["objects"]):
        return {"passed": False, "reason": "duplicate_label_identity"}
    if set(actual) != set(wanted) or result["label_count"] != reference["label_count"]:
        return {"passed": False, "reason": "label_identity_mismatch"}
    measure_error = 0.0
    centroid_error = 0.0
    for label, target in wanted.items():
        if actual[label]["voxel_count"] != target["voxel_count"]:
            return {"passed": False, "reason": "voxel_count_mismatch", "label_id": label}
        for field in ("native_measure", "mapped_measure"):
            if not np.isfinite(actual[label][field]):
                return {"passed": False, "reason": "nonfinite_measure", "label_id": label, "field": field}
            measure_error = max(measure_error, abs(actual[label][field] - target[field]) / abs(target[field]))
        for field in ("native_centroid_um", "mapped_centroid_um"):
            observed = np.asarray(actual[label][field])
            if observed.shape != np.asarray(target[field]).shape or not np.all(np.isfinite(observed)):
                return {"passed": False, "reason": "invalid_centroid", "label_id": label, "field": field}
            centroid_error = max(centroid_error, float(np.max(np.abs(observed - target[field]))))
    return {"passed": measure_error <= 1e-9 and centroid_error <= 1e-8,
            "maximum_relative_measure_error": measure_error,
            "maximum_absolute_centroid_error_um": centroid_error}
