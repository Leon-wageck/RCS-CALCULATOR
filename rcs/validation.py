"""Lightweight validation helpers for quick sanity checks.

These routines are not formal unit tests but provide reproducible, small
scenarios to visually compare ray-traced and facet-PO RCS, including canonical
reflectors (cube/dihedral/trihedral) and the micro-Doppler model with/without
rotating sub-meshes.
"""

from __future__ import annotations

import dataclasses

import numpy as np
import trimesh
from typing import Dict, Optional

from .facet_po import facet_rcs
from .rcs_engine import Material, RCSEngine, SimulationSettings
from .nctr import simulate_nctr_signature


def _pec_material() -> Material:
    return Material(
        name="PEC",
        epsilon_real=1.0,
        epsilon_imag=0.0,
        conductivity=1e7,
        reflectivity=0.98,
        reflectivity_h=None,
        reflectivity_v=None,
    )


def _cube(size: float = 1.0) -> trimesh.Trimesh:
    return trimesh.creation.box(extents=(size, size, size))


def _dihedral(size: float = 1.0, thickness: float = 0.02) -> trimesh.Trimesh:
    plate_xz = trimesh.creation.box(extents=(size, thickness, size))
    plate_yz = trimesh.creation.box(extents=(thickness, size, size))
    return trimesh.util.concatenate([plate_xz, plate_yz])


def _trihedral(size: float = 1.0, thickness: float = 0.02) -> trimesh.Trimesh:
    plate_xy = trimesh.creation.box(extents=(size, size, thickness))
    return trimesh.util.concatenate([_dihedral(size, thickness), plate_xy])


def _az_sweep(
    mesh: trimesh.Trimesh, freq_hz: float, elevation_deg: float = 0.0, az_step: float = 2.0
) -> Dict[str, np.ndarray]:
    """Compute azimuth RCS cuts for both ray-trace and facet-PO methods."""

    engine = RCSEngine()
    mat = _pec_material()
    settings_common = dict(
        band="X",
        polarization="H",
        max_reflections=3,
        frequency_hz=freq_hz,
        elevation_start=elevation_deg,
        elevation_stop=elevation_deg,
        elevation_step=1.0,
        azimuth_step=az_step,
    )

    settings_ray = SimulationSettings(method="ray", **settings_common)
    settings_facet = SimulationSettings(method="facet_po", **settings_common)

    ray_res = engine.compute(mesh, mat, settings_ray)
    facet_res = engine.compute(mesh, mat, settings_facet)

    azimuths = ray_res.azimuth_deg
    return {
        "az_deg": azimuths,
        "ray_dbsm": ray_res.rcs_dbsm[0, 0],
        "facet_dbsm": facet_res.rcs_dbsm[0, 0],
    }


def canonical_reflector_sweeps(
    freq_hz: float = 10e9, elevation_deg: float = 0.0
) -> Dict[str, Dict[str, np.ndarray]]:
    """Generate azimuth sweeps for cube, dihedral, and trihedral reflectors."""

    cube = _cube()
    dihedral = _dihedral()
    trihedral = _trihedral()

    return {
        "cube": _az_sweep(cube, freq_hz, elevation_deg),
        "dihedral": _az_sweep(dihedral, freq_hz, elevation_deg),
        "trihedral": _az_sweep(trihedral, freq_hz, elevation_deg),
    }


def compare_flat_plate(size: float = 1.0, freq_hz: float = 10e9) -> Dict[str, np.ndarray]:
    """Compare ray and facet-PO responses for a PEC flat plate.

    Returns a dictionary with azimuth angles in degrees and RCS in dBsm for each
    method at 0 deg elevation. A broadside peak and off-boresight roll-off
    indicate a healthy simulation chain.
    """

    mesh = trimesh.creation.box(extents=(size, size, 0.02))
    engine = RCSEngine()
    settings_ray = SimulationSettings(
        band="X",
        polarization="H",
        max_reflections=2,
        method="ray",
        frequency_hz=freq_hz,
        elevation_start=0.0,
        elevation_stop=0.0,
        elevation_step=1.0,
        azimuth_step=2.0,
    )
    settings_facet = SimulationSettings(
        band="X",
        polarization="H",
        max_reflections=1,
        method="facet_po",
        frequency_hz=freq_hz,
        elevation_start=0.0,
        elevation_stop=0.0,
        elevation_step=1.0,
        azimuth_step=2.0,
    )
    mat = _pec_material()

    ray_res = engine.compute(mesh, mat, settings_ray)
    facet_res = engine.compute(mesh, mat, settings_facet)

    az = ray_res.azimuth_deg
    ray_db = ray_res.rcs_dbsm[0, 0]
    facet_db = facet_res.rcs_dbsm[0, 0]

    return {"az_deg": az, "ray_dbsm": ray_db, "facet_dbsm": facet_db}


def compare_box(freq_hz: float = 10e9) -> Dict[str, np.ndarray]:
    """Contrast ray and facet-PO patterns for a simple PEC cube."""

    mesh = trimesh.creation.box(extents=(1.0, 1.0, 1.0))
    engine = RCSEngine()
    settings = SimulationSettings(
        band="X",
        polarization="H",
        max_reflections=2,
        method="ray",
        frequency_hz=freq_hz,
        elevation_start=0.0,
        elevation_stop=0.0,
        elevation_step=1.0,
        azimuth_step=5.0,
    )
    mat = _pec_material()
    ray_res = engine.compute(mesh, mat, settings)

    settings_po = dataclasses.replace(settings, method="facet_po")
    facet_res = engine.compute(mesh, mat, settings_po)

    return {
        "az_deg": ray_res.azimuth_deg,
        "ray_dbsm": ray_res.rcs_dbsm[0, 0],
        "facet_dbsm": facet_res.rcs_dbsm[0, 0],
    }


def compare_nctr_rotors(mesh: Optional[trimesh.Trimesh] = None) -> Dict[str, np.ndarray]:
    """Compare whole-body spin against a rotating sub-component."""

    if mesh is None:
        mesh = trimesh.creation.box(extents=(1.0, 0.5, 0.5))

    rot_indices = np.arange(len(mesh.vertices) // 2)
    times, freqs, base_spec, _ = simulate_nctr_signature(mesh, {"reflectivity": 1.0}, 10.0)
    _, _, group_spec, _, _, _, _ = simulate_nctr_signature(
        mesh,
        {"reflectivity": 1.0},
        10.0,
        rotating_groups={"rotor": {"indices": rot_indices, "rpm": 1200.0, "axis": [0, 0, 1]}},
        return_range_doppler=True,
    )

    return {"times": times, "freqs": freqs, "baseline": base_spec, "grouped": group_spec}


def plot_canonical_reflectors(freq_hz: float = 10e9, elevation_deg: float = 0.0) -> None:
    """Plot azimuthal RCS for cube, dihedral, and trihedral validation cases."""

    import matplotlib.pyplot as plt

    sweeps = canonical_reflector_sweeps(freq_hz=freq_hz, elevation_deg=elevation_deg)
    fig, axes = plt.subplots(3, 1, figsize=(8, 12), sharex=True)
    for ax, (name, result) in zip(axes, sweeps.items()):
        ax.plot(result["az_deg"], result["ray_dbsm"], label="Ray", lw=1.8)
        ax.plot(result["az_deg"], result["facet_dbsm"], label="Facet PO", lw=1.3, ls="--")
        ax.set_ylabel("RCS (dBsm)")
        ax.set_title(name.capitalize())
        ax.grid(True)
        ax.legend()
    axes[-1].set_xlabel("Azimuth (deg)")
    fig.tight_layout()
    plt.show()


__all__ = [
    "canonical_reflector_sweeps",
    "plot_canonical_reflectors",
    "compare_flat_plate",
    "compare_box",
    "compare_nctr_rotors",
]


if __name__ == "__main__":  # pragma: no cover - manual validation utility
    plot_canonical_reflectors()
