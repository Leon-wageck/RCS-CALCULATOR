"""Physical-optics style facet summation inspired by PyPOFacets."""

from __future__ import annotations

import numpy as np
import trimesh


def facet_rcs(
    mesh: trimesh.Trimesh,
    reflectivity: float,
    frequency_hz: float,
    directions: np.ndarray,
) -> np.ndarray:
    """Estimate monostatic RCS by summing illuminated facet responses.

    This follows a simplified physical-optics idea similar to PyPOFacets: each
    facet that faces the radar contributes based on its projected area and a
    flat-plate approximation (``sigma = 4*pi*A^2/lambda^2 * cos(theta)^2``).
    The calculation is vectorised across all look directions for efficiency.
    """

    wavelength = 3e8 / max(frequency_hz, 1e-9)
    area = mesh.area_faces.reshape(-1, 1)
    normals = mesh.face_normals / (np.linalg.norm(mesh.face_normals, axis=1, keepdims=True) + 1e-12)

    dirs = np.asarray(directions, dtype=float)
    norms = np.linalg.norm(dirs, axis=1, keepdims=True)
    dirs = dirs / (norms + 1e-12)

    # Directions point from radar to target; invert to get incidence toward faces.
    look = -dirs.T  # shape (3, M)
    cos_theta = normals @ look
    cos_theta = np.clip(cos_theta, 0.0, 1.0)

    # Reflectivity scales how much of the incoming energy is preserved per facet.
    base = (4.0 * np.pi / (wavelength**2)) * (area**2)
    contribution = base * (cos_theta**2) * reflectivity
    rcs_lin = contribution.sum(axis=0)
    return np.maximum(rcs_lin, 1e-12)


__all__ = ["facet_rcs"]
