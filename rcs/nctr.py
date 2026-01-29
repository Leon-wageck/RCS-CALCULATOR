"""Simplified NCTR (Non-Cooperative Target Recognition) helpers.

The routines in this module generate micro-Doppler and range–Doppler
signatures from a 3D mesh that can be used as lightweight NCTR inputs.
They operate purely on the mesh geometry and do not require additional
dependencies beyond NumPy.
"""

from __future__ import annotations

import numpy as np
import trimesh
from typing import Dict, List, Optional, Tuple, Union

from .math_utils import rotation_matrix


def _vertex_weights(mesh: trimesh.Trimesh) -> np.ndarray:
    """Approximate per-vertex scattering weights using face areas."""

    if not len(mesh.faces):
        return np.ones(len(mesh.vertices))

    weights = np.zeros(len(mesh.vertices))
    areas = mesh.area_faces

    for idx, faces in enumerate(mesh.vertex_faces):
        valid = faces[faces != -1]
        if len(valid):
            weights[idx] = float(np.mean(areas[valid]))
        else:
            # Keep a small baseline weight for isolated or degenerate vertices.
            weights[idx] = 1e-3

    if np.all(weights == 0):
        return np.ones(len(mesh.vertices))

    nonzero = weights[weights > 0]
    if len(nonzero):
        min_positive = float(np.min(nonzero))
        weights[weights == 0] = min_positive

    weights /= np.max(weights)
    min_nonzero = np.min(weights[weights > 0]) if np.any(weights > 0) else 1.0
    weights[weights == 0] = min_nonzero
    return weights


def _spin_matrix(angle_rad: float) -> np.ndarray:
    """Rotation matrix for spinning around the z-axis by ``angle_rad``."""

    c, s = np.cos(angle_rad), np.sin(angle_rad)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], dtype=float)


def _axis_angle_rotation(axis: np.ndarray, angle_rad: float) -> np.ndarray:
    """Rotation matrix for ``angle_rad`` about ``axis`` using Rodrigues' formula."""

    axis = axis / (np.linalg.norm(axis) + 1e-12)
    kx, ky, kz = axis
    c = np.cos(angle_rad)
    s = np.sin(angle_rad)
    v = 1 - c
    return np.array(
        [
            [kx * kx * v + c, kx * ky * v - kz * s, kx * kz * v + ky * s],
            [ky * kx * v + kz * s, ky * ky * v + c, ky * kz * v - kx * s],
            [kz * kx * v - ky * s, kz * ky * v + kx * s, kz * kz * v + c],
        ]
    )


def simulate_nctr_signature(
    mesh: trimesh.Trimesh,
    material: dict,
    freq_ghz: float,
    yaw: float = 0.0,
    pitch: float = 0.0,
    roll: float = 0.0,
    rpm: float = 120.0,
    prf: float = 1800.0,
    pulses: int = 256,
    window: int = 64,
    hop: int = 16,
    rotating_groups: Optional[Dict[str, dict]] = None,
    return_range_doppler: bool = False,
) -> Union[
    Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray],
    Tuple[
        np.ndarray,
        np.ndarray,
        np.ndarray,
        np.ndarray,
        np.ndarray,
        np.ndarray,
        np.ndarray,
    ],
]:
    """Generate a synthetic micro-Doppler (and optional range–Doppler) signature.

    Parameters
    ----------
    mesh:
        Target mesh.
    material:
        Dict-like container with at least ``reflectivity``. Units are unitless.
    freq_ghz:
        Carrier frequency in GHz (free-space propagation assumed).
    yaw, pitch, roll:
        Initial orientation of the target in degrees.
    rpm:
        Spin rate in revolutions per minute used for the bulk-body rotation or
        as a fallback when no ``rotating_groups`` are provided.
    prf:
        Pulse repetition frequency in Hz.
    pulses:
        Number of coherent pulses to synthesise.
    window:
        STFT window length (samples).
    hop:
        Hop size between STFT windows (samples).
    rotating_groups:
        Optional mapping describing independently rotating vertex subsets. Each
        entry should contain ``indices`` (vertex indices), ``rpm`` and ``axis``
        (3-vector). If omitted the whole body spins about the z-axis.
    return_range_doppler:
        When ``True`` also compute a coarse range–Doppler cube using a simple
        range binning scheme.

    Returns
    -------
    times, doppler_freqs, spectrogram, envelope[, range_bins, doppler_freqs, range_doppler]
        Spectrogram values are in dB relative to 1. Micro-Doppler frequencies
        are in Hz. Range bins are in metres if requested.

    Notes
    -----
    This is a geometric micro-Doppler toy model: propagation is line-of-sight
    only, no multipath or clutter is added, and the scattering coefficient is
    purely scalar. It is intended for preview/visualisation rather than
    high-fidelity ATR.
    """

    if mesh is None or not hasattr(mesh, "vertices"):
        raise ValueError("Kein gültiges 3D-Mesh geladen.")

    if pulses < window:
        raise ValueError("Die Fenstergröße darf nicht größer als die Pulsanzahl sein.")

    wavelength = 0.3 / max(freq_ghz, 1e-6)
    verts = mesh.vertices - mesh.centroid
    base_rotation = rotation_matrix(yaw, pitch, roll)
    verts = (base_rotation @ verts.T).T

    look_dir = np.array([1.0, 0.0, 0.0])
    look_dir /= np.linalg.norm(look_dir)

    omega_body = 2 * np.pi * rpm / 60.0
    dt = 1.0 / prf
    reflectivity = 1.0
    if hasattr(material, "reflectivity"):
        reflectivity = float(getattr(material, "reflectivity"))
    elif hasattr(material, "get"):
        reflectivity = float(material.get("reflectivity", 1.0))  # type: ignore[call-arg]

    weights = _vertex_weights(mesh) * reflectivity

    signal = np.zeros(pulses, dtype=complex)
    max_range = float(np.max(np.abs(verts @ look_dir)))
    bin_width = 0.5  # metres
    bin_edges = np.arange(-max_range - bin_width, max_range + 2 * bin_width, bin_width)
    range_bins = 0.5 * (bin_edges[:-1] + bin_edges[1:])
    range_hist = np.zeros((len(range_bins), pulses), dtype=complex)

    # Pre-extract groups
    rotating_groups = rotating_groups or {}
    base_indices = set(range(len(verts)))
    for group in rotating_groups.values():
        for idx in group.get("indices", []):
            base_indices.discard(int(idx))
    static_indices = np.array(sorted(base_indices))

    for pulse_idx in range(pulses):
        t = pulse_idx * dt
        if rotating_groups:
            current = np.zeros_like(verts)
            velocities = np.zeros_like(verts)
            current[static_indices] = verts[static_indices]
            for group in rotating_groups.values():
                indices = np.asarray(group.get("indices", []), dtype=int)
                axis = np.asarray(group.get("axis", [0.0, 0.0, 1.0]), dtype=float)
                if not np.isfinite(axis).all() or np.linalg.norm(axis) < 1e-9:
                    axis = np.array([0.0, 0.0, 1.0])
                rpm_group = float(group.get("rpm", rpm))
                omega_group = 2 * np.pi * rpm_group / 60.0
                rot = _axis_angle_rotation(axis, omega_group * t)
                current[indices] = (rot @ verts[indices].T).T
                omega_vec = axis / (np.linalg.norm(axis) + 1e-12) * omega_group
                velocities[indices] = np.cross(omega_vec, current[indices])
        else:
            spin = _spin_matrix(omega_body * t)
            current = (spin @ verts.T).T
            velocities = np.cross(np.array([0.0, 0.0, omega_body]), current)

        ranges = current @ look_dir
        radial_vel = velocities @ look_dir

        phase = 4 * np.pi / wavelength * ranges
        doppler_phase = 2 * np.pi * (2 * radial_vel / wavelength) * t

        pulse_field = weights * np.exp(1j * (phase + doppler_phase))
        signal[pulse_idx] = np.sum(pulse_field)

        if return_range_doppler:
            bin_idx = np.digitize(ranges, bin_edges) - 1
            valid = (bin_idx >= 0) & (bin_idx < len(range_bins))
            for contrib, b_idx in zip(pulse_field[valid], bin_idx[valid]):
                range_hist[b_idx, pulse_idx] += contrib

    noise = np.random.normal(0, 0.02, size=pulses) + 1j * np.random.normal(0, 0.02, size=pulses)
    signal += noise

    window_func = np.hanning(window)
    specs: List[np.ndarray] = []
    times: List[float] = []

    for start in range(0, pulses - window + 1, hop):
        segment = signal[start : start + window] * window_func
        fft_vals = np.fft.fftshift(np.fft.fft(segment))
        power = 20 * np.log10(np.abs(fft_vals) + 1e-6)
        specs.append(power)
        times.append((start + window / 2) * dt)

    spectrogram = np.array(specs).T
    freqs = np.fft.fftshift(np.fft.fftfreq(window, d=dt))
    envelope = 20 * np.log10(np.abs(signal) + 1e-6)

    if not return_range_doppler:
        return np.array(times), freqs, spectrogram, envelope

    range_specs: List[np.ndarray] = []
    for rng_series in range_hist:
        bin_segments: List[np.ndarray] = []
        for start in range(0, pulses - window + 1, hop):
            segment = rng_series[start : start + window] * window_func
            fft_vals = np.fft.fftshift(np.fft.fft(segment))
            power = 20 * np.log10(np.abs(fft_vals) + 1e-6)
            bin_segments.append(power)
        if bin_segments:
            range_specs.append(np.array(bin_segments).T)
        else:
            range_specs.append(np.zeros((window, 0)))

    range_doppler = np.stack(range_specs, axis=0)
    return (
        np.array(times),
        freqs,
        spectrogram,
        envelope,
        range_bins,
        freqs,
        range_doppler,
    )


__all__ = ["simulate_nctr_signature"]
