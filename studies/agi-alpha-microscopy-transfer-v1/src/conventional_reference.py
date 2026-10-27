# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import itertools
from typing import Any

import numpy as np
from scipy import ndimage


def conventional_moments(
    labels: np.ndarray, spacing: np.ndarray, origin: np.ndarray, affine: np.ndarray
) -> dict[str, Any]:
    ids, counts = np.unique(labels, return_counts=True)
    keep = ids != 0
    ids, counts = ids[keep], counts[keep]
    if not len(ids):
        return {"label_count": 0, "objects": []}
    centers = np.asarray(ndimage.center_of_mass(np.ones(labels.shape, dtype=np.uint8), labels, ids))
    physical = centers * spacing + origin
    mapped = physical @ affine[:-1, :-1].T + affine[:-1, -1]
    native_measure = counts * np.prod(spacing)
    mapped_measure = native_measure * abs(np.linalg.det(affine[:-1, :-1]))
    return {
        "label_count": len(ids),
        "objects": [
            {
                "label_id": int(label),
                "voxel_count": int(counts[i]),
                "native_measure": float(native_measure[i]),
                "mapped_measure": float(mapped_measure[i]),
                "native_centroid_um": physical[i].tolist(),
                "mapped_centroid_um": mapped[i].tolist(),
            }
            for i, label in enumerate(ids)
        ],
    }


def common_grid(
    labels: np.ndarray,
    spacing: np.ndarray,
    origin: np.ndarray,
    affine: np.ndarray,
    target_step: float,
    max_voxels: int = 30_000_000,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    d = labels.ndim
    corners = np.asarray(list(itertools.product(*[(-0.5, n - 0.5) for n in labels.shape])))
    mapped = (corners * spacing + origin) @ affine[:-1, :-1].T + affine[:-1, -1]
    target_spacing = np.full(d, target_step)
    target_origin = np.floor(mapped.min(axis=0) / target_spacing) * target_spacing
    shape = np.ceil((mapped.max(axis=0) - target_origin) / target_spacing).astype(int) + 1
    if np.prod(shape) > max_voxels:
        raise ValueError("target raster exceeds scoped voxel budget")
    inv = np.linalg.inv(affine[:-1, :-1])
    matrix = np.diag(1 / spacing) @ inv @ np.diag(target_spacing)
    offset = (inv @ (target_origin - affine[:-1, -1]) - origin) / spacing
    output = ndimage.affine_transform(
        labels, matrix, offset=offset, output_shape=tuple(shape), order=0, mode="constant", cval=0, prefilter=False
    )
    return output, target_spacing, target_origin


def compare(expected: dict[str, Any], actual: dict[str, Any]) -> dict[str, Any]:
    truth = {x["label_id"]: x for x in expected["objects"]}
    got = {x["label_id"]: x for x in actual["objects"]}
    shared = sorted(set(truth) & set(got))
    relative = [abs(truth[x]["mapped_measure"] - got[x]["mapped_measure"]) / truth[x]["mapped_measure"] for x in shared]
    errors = [max(abs(np.asarray(truth[x]["mapped_centroid_um"]) - got[x]["mapped_centroid_um"])) for x in shared]
    return {
        "same_label_ids": set(truth) == set(got),
        "missing_labels": sorted(set(truth) - set(got)),
        "max_relative_measure_error": float(max(relative, default=0)),
        "median_relative_measure_error": float(np.median(relative)) if relative else 0.0,
        "max_centroid_error_um": float(max(errors, default=0)),
        "labels_over_one_percent": sum(x > 0.01 for x in relative),
        "accepted_numeric": bool(
            set(truth) == set(got) and max(relative, default=0) <= 1e-9 and max(errors, default=0) <= 1e-8
        ),
    }
