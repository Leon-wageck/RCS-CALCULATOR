"""Heuristic edge diffraction and corner enhancement helpers.

These routines are intentionally lightweight and phenomenological; they are not
full GTD/UTD solutions. The goal is to inject physically plausible edge and
corner returns into simplified RCS estimators so that boxy targets exhibit broad
lobes, nulls, and strong trihedral peaks instead of only narrow specular
needles.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Iterable, List, Optional, Tuple

import numpy as np
import trimesh

from .physics import build_ray_intersector

# ---------------------------------------------------------------------------
# Tunable heuristics
EDGE_SHARPNESS_DEG = 25.0
"""Minimum dihedral angle (degrees) for an edge to contribute diffraction."""

EDGE_DIFFRACTION_GAIN = 0.2
"""Amplitude gain for edge diffraction. Empirical, order-of-magnitude only."""

EDGE_VISIBILITY_BIAS = 0.1
"""Bias added to the illuminated test to keep grazing edges contributive."""

CORNER_ORTHOGONALITY = 0.25
"""Maximum absolute dot product for normals to be considered orthogonal."""

CORNER_GAIN = 1.8
"""Amplitude gain for trihedral-style corner enhancement (heuristic)."""


@dataclass(frozen=True)
class SharpEdge:
    """Container describing a sharp edge segment on the mesh."""

    center: np.ndarray
    direction: np.ndarray
    length: float
    normals: Tuple[np.ndarray, np.ndarray]
    faces: Tuple[int, int]

    @property
    def unit(self) -> np.ndarray:
        return self.direction / (np.linalg.norm(self.direction) + 1e-12)


# ---------------------------------------------------------------------------
# Edge utilities

def build_sharp_edges(mesh: trimesh.Trimesh) -> List[SharpEdge]:
    """Extract sharp edges suitable for heuristic diffraction contributions."""

    if mesh.edges is None or len(mesh.edges) == 0:
        return []

    edges: List[SharpEdge] = []
    angles = mesh.face_adjacency_angles
    adjacency = mesh.face_adjacency
    vertices = mesh.vertices
    normals = mesh.face_normals

    if angles is None or adjacency is None:
        return []

    threshold = np.radians(EDGE_SHARPNESS_DEG)
    faces = mesh.faces
    for (f1, f2), angle in zip(adjacency, angles):
        if angle < threshold:
            continue
        shared_verts = np.intersect1d(faces[f1], faces[f2])
        if len(shared_verts) != 2:
            continue
        v0, v1 = vertices[shared_verts]
        direction = v1 - v0
        length = float(np.linalg.norm(direction))
        if length <= 1e-6:
            continue
        center = 0.5 * (v0 + v1)
        edges.append(
            SharpEdge(
                center=center,
                direction=direction,
                length=length,
                normals=(normals[f1], normals[f2]),
                faces=(int(f1), int(f2)),
            )
        )
    return edges


def _edge_visible(edge: SharpEdge, k_hat: np.ndarray, mesh: Optional[trimesh.Trimesh]) -> bool:
    """Rough visibility for an edge given a look direction."""

    k_hat = k_hat / (np.linalg.norm(k_hat) + 1e-12)
    # Require at least one adjacent face to be illuminated.
    k_i = -k_hat
    illum = False
    for normal in edge.normals:
        if np.dot(normal, k_i) + EDGE_VISIBILITY_BIAS > 0.0:
            illum = True
            break
    if not illum:
        return False

    if mesh is None:
        return True

    radius = float(
        getattr(getattr(getattr(mesh, "bounding_sphere", None), "primitive", None), "radius", 0.0)
        or 0.0
    )
    if not np.isfinite(radius) or radius <= 0.0:
        extents = getattr(mesh, "extents", None)
        if extents is not None:
            radius = float(np.linalg.norm(extents)) / 2.0
    if not np.isfinite(radius) or radius <= 0.0:
        radius = 1.0

    origin = edge.center + k_i * (radius * 4.0 + 1.0)
    direction = -k_i
    try:
        locs, _, tri_idx = mesh.ray.intersects_location(  # type: ignore[call-arg]
            np.array([origin]), np.array([direction]), multiple_hits=False
        )
    except Exception:
        return True
    if len(locs) == 0:
        return True
    return int(tri_idx[0]) in edge.faces


def edge_diffraction_field(
    edges: Iterable[SharpEdge],
    k_hat: np.ndarray,
    k: float,
    mesh: Optional[trimesh.Trimesh] = None,
) -> complex:
    """Sum heuristic edge diffraction contributions for a single direction."""

    edge_list = list(edges) if edges is not None else []
    if len(edge_list) == 0:
        return 0.0 + 0.0j

    field = 0.0 + 0.0j
    for edge in edge_list:
        if not _edge_visible(edge, k_hat, mesh):
            continue
        amp = EDGE_DIFFRACTION_GAIN * np.sqrt(max(edge.length, 1e-12))
        phase = np.dot(edge.center, k_hat)
        field += amp * np.exp(1j * k * phase)
    return field


# ---------------------------------------------------------------------------
# Corner utilities

def corner_field(
    k_hat: np.ndarray,
    normals: np.ndarray,
    areas: np.ndarray,
    centers: np.ndarray,
    k: float,
    illuminated_mask: Optional[np.ndarray] = None,
) -> complex:
    """Detect trihedral-like normal triplets and return a heuristic field term."""

    if illuminated_mask is None:
        illuminated_mask = np.ones(len(normals), dtype=bool)
    candidates = np.where(illuminated_mask)[0]
    if len(candidates) < 3:
        return 0.0 + 0.0j

    k_i = -k_hat
    field = 0.0 + 0.0j
    for i, j, l in combinations(candidates, 3):
        n1, n2, n3 = normals[[i, j, l]]
        # All three must face the radar.
        if min(np.dot(n1, k_i), np.dot(n2, k_i), np.dot(n3, k_i)) <= 0:
            continue
        dot12 = abs(np.dot(n1, n2))
        dot13 = abs(np.dot(n1, n3))
        dot23 = abs(np.dot(n2, n3))
        if max(dot12, dot13, dot23) > CORNER_ORTHOGONALITY:
            continue
        effective_area = areas[[i, j, l]].sum()
        corner_center = centers[[i, j, l]].mean(axis=0)
        amp = CORNER_GAIN * effective_area
        field += amp * np.exp(1j * k * np.dot(corner_center, k_hat))

    return field


__all__ = [
    "EDGE_SHARPNESS_DEG",
    "EDGE_DIFFRACTION_GAIN",
    "CORNER_GAIN",
    "SharpEdge",
    "build_sharp_edges",
    "edge_diffraction_field",
    "corner_field",
]
