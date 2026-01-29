"""Mathematical helpers for geometry and coordinate transforms."""

from __future__ import annotations

from typing import Tuple

import numpy as np


def rotation_matrix(yaw: float, pitch: float, roll: float) -> np.ndarray:
    """Return a combined rotation matrix (yaw, pitch, roll in degrees)."""
    y, p, r = np.radians([yaw, pitch, roll])

    # Aerospace convention: yaw (z), pitch (y), roll (x)
    r_yaw = np.array(
        [[np.cos(y), -np.sin(y), 0], [np.sin(y), np.cos(y), 0], [0, 0, 1]]
    )
    r_pitch = np.array(
        [[np.cos(p), 0, np.sin(p)], [0, 1, 0], [-np.sin(p), 0, np.cos(p)]]
    )
    r_roll = np.array(
        [[1, 0, 0], [0, np.cos(r), -np.sin(r)], [0, np.sin(r), np.cos(r)]]
    )

    return r_yaw @ r_pitch @ r_roll


def spherical_directions(
    az_steps: int, el_steps: int
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Create azimuth/elevation grids and corresponding direction vectors."""
    az = np.linspace(0, 360, az_steps, endpoint=False)
    el = np.linspace(-90, 90, el_steps)
    az_grid, el_grid = np.meshgrid(az, el)
    dirs = np.stack(
        (
            np.cos(np.radians(el_grid)) * np.cos(np.radians(az_grid)),
            np.cos(np.radians(el_grid)) * np.sin(np.radians(az_grid)),
            np.sin(np.radians(el_grid)),
        ),
        axis=-1,
    )
    dirs /= np.linalg.norm(dirs, axis=-1, keepdims=True) + 1e-12
    return az, el, dirs


def direction_grid(azimuth_deg: np.ndarray, elevation_deg: np.ndarray) -> np.ndarray:
    """Build a grid of unit direction vectors from azimuth/elevation arrays."""

    az_grid, el_grid = np.meshgrid(azimuth_deg, elevation_deg)
    dirs = np.stack(
        (
            np.cos(np.radians(el_grid)) * np.cos(np.radians(az_grid)),
            np.cos(np.radians(el_grid)) * np.sin(np.radians(az_grid)),
            np.sin(np.radians(el_grid)),
        ),
        axis=-1,
    )
    return dirs / (np.linalg.norm(dirs, axis=-1, keepdims=True) + 1e-12)


def frequency_loss(freq_ghz: float, min_loss: float = 0.2) -> float:
    """Calculate frequency-dependent attenuation per reflection."""
    return max(0.8 - 0.02 * (freq_ghz - 1), min_loss)


__all__ = ["rotation_matrix", "spherical_directions", "direction_grid", "frequency_loss"]
