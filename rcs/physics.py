"""Core radar cross-section computations and helpers."""

from __future__ import annotations

import concurrent.futures
from functools import partial
from typing import List, Optional, Tuple

import numpy as np
import trimesh

from .math_utils import frequency_loss, spherical_directions


MIN_ENERGY = 1e-6


def build_ray_intersector(mesh: trimesh.Trimesh):
    """Create a ray-mesh intersector using the fastest available backend."""
    try:
        from trimesh.ray.ray_pyembree import RayMeshIntersector

        return RayMeshIntersector(mesh)
    except Exception:
        try:
            # ``ray_triangle`` relies on an R-tree accelerator. Surface this as a
            # clear error instead of bubbling up a low-level ``ModuleNotFound``
            # from trimesh internals so the GUI can present an actionable
            # message.
            import rtree  # noqa: F401

            from trimesh.ray.ray_triangle import RayMeshIntersector

            return RayMeshIntersector(mesh)
        except ModuleNotFoundError as exc:  # pragma: no cover - environment specific
            raise ModuleNotFoundError(
                "Missing optional dependency 'rtree'. Install it via 'pip install rtree' "
                "to enable ray-tracing based simulations."
            ) from exc


def trace_ray(mesh: trimesh.Trimesh, origin: np.ndarray, direction: np.ndarray, max_depth: int, reflectivity: float, freq_ghz: float) -> float:
    """Trace a single ray with multiple reflections and return linear RCS contribution."""
    rays = mesh.ray
    energy = 1.0
    rcs = 0.0
    loss_per_reflection = frequency_loss(freq_ghz)
    area_faces = mesh.area_faces
    face_normals = mesh.face_normals

    for _ in range(max_depth):
        try:
            locs, _, tri_idx = rays.intersects_location(np.array([origin]), np.array([direction]), multiple_hits=False)
        except Exception:
            break

        if len(locs) == 0:
            break

        hit = locs[0]
        face_index = tri_idx[0]
        normal = face_normals[face_index]
        reflect_dir = direction - 2 * np.dot(direction, normal) * normal
        reflect_dir /= np.linalg.norm(reflect_dir)

        alignment = np.dot(reflect_dir, -direction)
        if alignment > 0.95:
            contrib = energy * area_faces[face_index] * (np.dot(normal, -direction)) ** 2
            rcs += contrib

        energy *= reflectivity * loss_per_reflection
        if energy < MIN_ENERGY:
            break

        origin = hit + 1e-4 * reflect_dir
        direction = reflect_dir

    return rcs


def _simulate_chunk(mesh: trimesh.Trimesh, reflectivity: float, freq_ghz: float, max_reflections: int, origins: np.ndarray, directions: np.ndarray) -> np.ndarray:
    trace = partial(trace_ray, mesh, max_depth=max_reflections, reflectivity=reflectivity, freq_ghz=freq_ghz)
    return np.fromiter((trace(origin=orig, direction=dir_vec) for orig, dir_vec in zip(origins, directions)), dtype=float)


def _material_reflectivity(material: object) -> float:
    """Return a material's reflectivity for legacy dicts or dataclasses."""

    if hasattr(material, "reflectivity"):
        return float(getattr(material, "reflectivity"))

    if hasattr(material, "get"):
        value = material.get("reflectivity")  # type: ignore[call-arg]
        if value is not None:
            return float(value)

    if isinstance(material, dict) and "reflectivity" in material:
        return float(material["reflectivity"])

    raise TypeError("Material must provide a 'reflectivity' attribute or key.")


def simulate_rcs(
    mesh: trimesh.Trimesh,
    material: object,
    max_reflections: int,
    freq_ghz: float,
    az_steps: int = 360,
    el_steps: int = 181,
    max_workers: Optional[int] = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Simulate RCS for a mesh using a grid of incoming directions."""
    if mesh is None or not hasattr(mesh, "bounding_sphere"):
        raise ValueError("Kein gültiges 3D-Mesh geladen.")

    if not hasattr(mesh, "ray"):
        mesh.ray = build_ray_intersector(mesh)

    az, el, dirs = spherical_directions(az_steps, el_steps)
    origins = mesh.bounding_sphere.center + 100 * (-dirs.reshape(-1, 3))
    directions = dirs.reshape(-1, 3)
    reflectivity = _material_reflectivity(material)

    chunk_size = 2048
    rcs_lin = np.zeros(len(directions), dtype=float)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for start in range(0, len(origins), chunk_size):
            end = start + chunk_size
            future = executor.submit(
                _simulate_chunk,
                mesh,
                reflectivity,
                freq_ghz,
                max_reflections,
                origins[start:end],
                directions[start:end],
            )
            futures[future] = slice(start, end)

        for fut in concurrent.futures.as_completed(futures):
            result = fut.result()
            sl = futures[fut]
            rcs_lin[sl] = result

    rcs_lin = np.clip(rcs_lin.reshape(dirs.shape[:2]), 1e-10, None)
    rcs_db = 10 * np.log10(rcs_lin)
    rcs_db += np.random.normal(0, 2, rcs_db.shape)
    return az, el, rcs_db


def robust_freq_sweep(mesh: trimesh.Trimesh, material: dict, max_reflections: int, master_callback=None) -> None:
    """Run an averaged frequency sweep while keeping the UI responsive."""
    import matplotlib.pyplot as plt
    import traceback
    from tkinter import messagebox

    if mesh is None:
        print("[Frequenz-Sweep] Kein Mesh geladen.")
        if master_callback:
            master_callback(lambda: messagebox.showerror("Fehler", "Kein 3D-Modell geladen."))
        return

    freqs = np.linspace(1, 35, 30)
    values: List[float] = []

    for f in freqs:
        try:
            _, _, rcs = simulate_rcs(mesh, material, max_reflections, f, az_steps=90, el_steps=91)
            mid_el = rcs.shape[0] // 2
            avg_rcs = float(np.mean(rcs[mid_el]))
            values.append(avg_rcs)
        except Exception as e:  # noqa: BLE001
            print(f"[freq_sweep] Fehler bei {f} GHz:", e)
            traceback.print_exc()
            values.append(-100)

    def plot_result() -> None:
        plt.plot(freqs, values)
        plt.xlabel("Frequenz (GHz)")
        plt.ylabel("RCS (dBsm)")
        plt.title("Frequenz-Sweep")
        plt.grid(True)
        plt.show()

    if master_callback:
        master_callback(plot_result)
    else:
        plot_result()


__all__ = ["simulate_rcs", "trace_ray", "robust_freq_sweep", "build_ray_intersector"]
