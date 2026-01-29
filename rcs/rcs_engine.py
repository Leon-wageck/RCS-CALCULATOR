"""Core RCS simulation routines and data containers.

This module exposes a relatively simple public API that is used by the GUI:

- :class:`SimulationSettings`
- :class:`Material`
- :class:`EngineMount`
- :class:`Propeller`
- :class:`SimulationResult`
- :class:`RCSEngine`

Internally we provide three conceptual simulation modes:

1. "Fast"       – facet-based physical–optics only (fast, low RAM)
2. "Realistic"  – facet PO + edge/corner diffraction + simple engine/propeller
3. "SBR"        – experimental shooting-and-bouncing-rays (multi-bounce)

All distances are metres, all frequencies are Hz.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Callable, Iterable, List, Optional, Tuple, Any

import numpy as np
import trimesh

from .diffraction import (
    SharpEdge,
    build_sharp_edges,
    corner_field,
    edge_diffraction_field,
)
from .facet_po import facet_rcs
from .math_utils import direction_grid, frequency_loss
from .physics import MIN_ENERGY, build_ray_intersector


BAND_DEFAULTS = {
    "L": (1.0e9, 2.0e9),
    "S": (2.0e9, 4.0e9),
    "C": (4.0e9, 8.0e9),
    "X": (8.0e9, 12.0e9),
}


# ---------------------------------------------------------------------------
# helpers


def to_dbsm(rcs_lin: np.ndarray) -> np.ndarray:
    """Convert linear RCS (m²) to dBsm.

    Values are clipped to a very small floor to avoid log singularities.
    """
    return 10.0 * np.log10(np.maximum(rcs_lin, 1e-20))


@dataclass
class FrequencySweep:
    """Frequency sweep definition."""

    start_hz: float
    stop_hz: float
    steps: int

    def as_array(self) -> np.ndarray:
        return np.linspace(self.start_hz, self.stop_hz, self.steps)


@dataclass
class SimulationSettings:
    """Parameters for an RCS simulation run.

    Attributes
    ----------
    method:
        String selector for the simulation backend. Accepted values (case
        insensitive):

        - ``"fast"``, ``"facet_po"`` – facet physical optics only
        - ``"lo"``, ``"realistic_lo"`` – facet PO + diffraction + engines/props
        - ``"sbr"``, ``"ray"`` – experimental shooting & bouncing rays
    """

    band: str
    polarization: str
    max_reflections: int
    method: str = "fast"
    engines: List["EngineMount"] = field(default_factory=list)
    propellers: List["Propeller"] = field(default_factory=list)
    frequency_hz: Optional[float] = None
    sweep: Optional[FrequencySweep] = None
    azimuth_start: float = 0.0
    azimuth_stop: float = 360.0
    azimuth_step: float = 5.0
    elevation_start: float = -90.0
    elevation_stop: float = 90.0
    elevation_step: float = 5.0
    elevation_slice_deg: Optional[float] = None
    azimuth_slice_deg: Optional[float] = None
    target_speed_mps: float = 0.0
    radar_profile: Optional[str] = None
    tx_yaw_deg: Optional[float] = None
    tx_elev_deg: Optional[float] = None
    max_workers: Optional[int] = None  # kept for backwards compatibility

    def frequencies(self) -> np.ndarray:
        if self.frequency_hz is not None:
            return np.array([self.frequency_hz], dtype=float)
        if self.sweep is not None:
            return self.sweep.as_array().astype(float)
        start, stop = BAND_DEFAULTS.get(self.band, BAND_DEFAULTS["S"])
        return np.array([(start + stop) * 0.5], dtype=float)

    def azimuths(self) -> np.ndarray:
        return np.arange(self.azimuth_start, self.azimuth_stop + 1e-6, self.azimuth_step)

    def elevations(self) -> np.ndarray:
        return np.arange(self.elevation_start, self.elevation_stop + 1e-6, self.elevation_step)


@dataclass
class Material:
    """Material properties used by the simplified RCS engine."""

    name: str
    epsilon_real: float
    epsilon_imag: float
    conductivity: float
    reflectivity: float
    reflectivity_h: Optional[float] = None
    reflectivity_v: Optional[float] = None
    reflectivity_hh: Optional[float] = None
    reflectivity_vv: Optional[float] = None
    reflectivity_hv: Optional[float] = None
    reflectivity_vh: Optional[float] = None

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class SimulationResult:
    """Container for RCS outputs."""

    band: str
    polarization: str
    frequencies_hz: np.ndarray
    azimuth_deg: np.ndarray
    elevation_deg: np.ndarray
    rcs_dbsm: np.ndarray  # shape (f, el, az)
    target_speed_mps: float
    radar_profile: Optional[str] = None
    doppler_hz: Optional[np.ndarray] = None

    def slice_for_elevation(self, elevation: float) -> Tuple[np.ndarray, np.ndarray]:
        idx = int(np.argmin(np.abs(self.elevation_deg - elevation)))
        return self.azimuth_deg, self.rcs_dbsm[:, idx, :]


@dataclass
class EngineMount:
    """Simple powerplant cavity model that boosts RCS when illuminated on-axis."""

    x: float
    y: float
    z: float
    radius_m: float = 0.5
    length_m: float = 1.0
    yaw_deg: float = 0.0

    def axis(self) -> np.ndarray:
        yaw = np.radians(self.yaw_deg)
        return np.array([np.cos(yaw), np.sin(yaw), 0.0])


@dataclass
class Propeller:
    """Parametric propeller disk representation with RPM and blade density."""

    x: float
    y: float
    z: float
    radius_m: float = 1.0
    blade_count: int = 3
    rpm: float = 1200.0
    yaw_deg: float = 0.0

    def axis(self) -> np.ndarray:
        yaw = np.radians(self.yaw_deg)
        return np.array([np.cos(yaw), np.sin(yaw), 0.0])


# ---------------------------------------------------------------------------
# main engine


class RCSEngine:
    """High-level interface for computing RCS."""

    def __init__(self) -> None:
        self._stop_requested = False

    # lifecycle -------------------------------------------------------------

    def request_stop(self) -> None:
        self._stop_requested = True

    def reset(self) -> None:
        self._stop_requested = False

    # core computation ------------------------------------------------------

    def compute(
        self,
        mesh: trimesh.Trimesh,
        material: Material,
        settings: SimulationSettings,
        *,
        progress: Optional[Callable[[int], None]] = None,
    ) -> SimulationResult:
        """Run an RCS simulation.

        The heavy lifting is done per *elevation ring* instead of over the full
        azimuth–elevation grid at once. This keeps peak memory usage low while
        leaving angular resolution completely unchanged.
        """
        if mesh is None:
            raise ValueError("A mesh must be provided for simulation.")

        # Normalise method selector
        method_key = (settings.method or "fast").lower()
        if method_key in {"fast", "facet_po"}:
            mode = "fast"
        elif method_key in {"lo", "realistic_lo", "realistic"}:
            mode = "lo"
        elif method_key in {"sbr", "ray", "raytracing", "experimental_sbr"}:
            mode = "sbr"
        else:
            mode = "fast"

        freqs = settings.frequencies()
        az = settings.azimuths()
        el = settings.elevations()

        # Allocate final result cube; this is intentionally small compared to
        # any intermediate facet/ray operations.
        rcs_all = np.zeros((len(freqs), len(el), len(az)), dtype=float)
        doppler_all: Optional[np.ndarray]
        doppler_all = np.zeros(len(freqs), dtype=float) if settings.target_speed_mps else None

        # Basic geometry / bounds -------------------------------------------
        # Use trimesh helpers when available, otherwise fall back to extents.
        if hasattr(mesh, "bounding_sphere"):
            bs = mesh.bounding_sphere
            center = np.asarray(getattr(bs, "center", mesh.centroid), dtype=float)
            radius = float(getattr(getattr(bs, "primitive", None), "radius", 0.0) or 0.0)
        else:
            center = np.asarray(mesh.centroid, dtype=float)
            radius = 0.0

        if not np.isfinite(radius) or radius <= 0.0:
            ext = getattr(mesh, "extents", None)
            if ext is not None:
                radius = float(np.linalg.norm(ext)) * 0.5
        if not np.isfinite(radius) or radius <= 0.0:
            radius = 1.0

        distance = radius * 6.0 + 1.0

        # Optional monostatic TX position (otherwise we fly a virtual sphere
        # centered on the model)
        if settings.tx_yaw_deg is not None and settings.tx_elev_deg is not None:
            tx_dir = self._direction_from_angles(settings.tx_yaw_deg, settings.tx_elev_deg)
            origin_center = center - distance * tx_dir
            origin_distance = 0.0
        else:
            origin_center = center
            origin_distance = distance

        # Small bundle of slightly offset rays to reduce aliasing in SBR mode
        bundle_offsets = np.linspace(-0.6, 0.6, 3) * radius
        bundle_grid = np.array([(ox, oy) for ox in bundle_offsets for oy in bundle_offsets])

        # Pre-compute mesh helpers used in several modes
        centers = mesh.triangles.mean(axis=1)
        face_normals = mesh.face_normals
        area_faces = mesh.area_faces

        edges: Tuple[SharpEdge, ...] = ()
        if mode in {"lo", "sbr"}:
            edges = tuple(build_sharp_edges(mesh))

        # Select effective scalar reflectivity for the current polarisation
        reflectivity = self._select_reflectivity(material, settings.polarization)

        # Only construct ray intersector when needed
        ray_intersector: Any = None
        if mode == "sbr":
            try:
                mesh.ray = build_ray_intersector(mesh)
            except ModuleNotFoundError as exc:  # environment dependent
                raise RuntimeError(
                    "SBR / ray-tracing mode requires the optional 'rtree' dependency.\n"
                    "Install it with 'pip install rtree' or switch to 'Fast' / 'Realistic LO' mode."
                ) from exc
            ray_intersector = mesh.ray

        # Frequency loop ----------------------------------------------------
        for fi, freq_hz in enumerate(freqs):
            if self._stop_requested:
                break

            freq_ghz = freq_hz / 1e9
            wavelength = self._compute_wavelength(freq_hz)
            k = 2.0 * np.pi / wavelength
            loss_per_reflection = frequency_loss(freq_ghz)

            if doppler_all is not None:
                doppler_all[fi] = 2.0 * settings.target_speed_mps * freq_hz / 3e8

            # Elevation rings ------------------------------------------------
            for ei, elev in enumerate(el):
                if self._stop_requested:
                    break

                # Build directions for this elevation only; shape (N_az, 3)
                dirs_ring = direction_grid(az, np.array([elev], dtype=float))[0]

                if mode == "fast":
                    # pure facet physical optics
                    rcs_lin_ring = facet_rcs(mesh, reflectivity, freq_hz, dirs_ring)

                elif mode == "lo":
                    # facet PO +
                    rcs_lin_ring = facet_rcs(mesh, reflectivity, freq_hz, dirs_ring)

                    # add diffraction from edges & corners
                    if edges:
                        diff_power = self._diffraction_ring(
                            mesh,
                            dirs_ring,
                            edges,
                            centers,
                            face_normals,
                            area_faces,
                            k,
                            reflectivity,
                        )
                        rcs_lin_ring = rcs_lin_ring + diff_power

                    # add simple engines / props
                    rcs_lin_ring = self._apply_powerplant_signatures(
                        dirs_ring, rcs_lin_ring, reflectivity, settings
                    )

                else:  # mode == "sbr"
                    rcs_lin_ring = self._trace_direction_block(
                        mesh=mesh,
                        directions=dirs_ring,
                        bundle_grid=bundle_grid,
                        max_reflections=settings.max_reflections,
                        reflectivity=reflectivity,
                        loss_per_reflection=loss_per_reflection,
                        k=k,
                        edges=edges,
                        centers=centers,
                        stop_cb=lambda: self._stop_requested,
                        origin_center=origin_center,
                        origin_distance=origin_distance,
                        ray_intersector=ray_intersector,
                        area_faces=area_faces,
                        face_normals=face_normals,
                    )

                    # Simple engine / prop enhancement on top of SBR
                    rcs_lin_ring = self._apply_powerplant_signatures(
                        dirs_ring, rcs_lin_ring, reflectivity, settings
                    )

                # store in final cube
                rcs_all[fi, ei, :] = to_dbsm(rcs_lin_ring)

            if progress:
                progress(int((fi + 1) / max(len(freqs), 1) * 100))

        # Produce final result object
        return SimulationResult(
            band=settings.band,
            polarization=settings.polarization,
            frequencies_hz=freqs,
            azimuth_deg=az,
            elevation_deg=el,
            rcs_dbsm=rcs_all,
            target_speed_mps=settings.target_speed_mps,
            radar_profile=settings.radar_profile,
            doppler_hz=doppler_all,
        )

    # ------------------------------------------------------------------
    # sub-routines used by several modes

    def _diffraction_ring(
        self,
        mesh: trimesh.Trimesh,
        directions: np.ndarray,
        edges: Iterable[SharpEdge],
        centers: np.ndarray,
        face_normals: np.ndarray,
        area_faces: np.ndarray,
        k: float,
        reflectivity: float,
    ) -> np.ndarray:
        """Return diffraction power for each direction in ``directions``."""

        edges_tuple: Tuple[SharpEdge, ...] = tuple(edges)
        if not edges_tuple:
            return np.zeros(len(directions), dtype=float)

        power = np.zeros(len(directions), dtype=float)
        for i, direction in enumerate(directions):
            k_hat = direction / (np.linalg.norm(direction) + 1e-12)
            illum_mask = (face_normals @ -k_hat) > 0.0
            edge_term = edge_diffraction_field(edges_tuple, k_hat, k, mesh)
            corner_term = corner_field(
                k_hat,
                face_normals,
                area_faces,
                centers,
                k,
                illuminated_mask=illum_mask,
            )
            power[i] = reflectivity * np.abs(edge_term + corner_term) ** 2

        return power

    def _apply_powerplant_signatures(
        self,
        directions: np.ndarray,
        rcs_lin: np.ndarray,
        reflectivity: float,
        settings: SimulationSettings,
    ) -> np.ndarray:
        """Blend simplified engine intake and propeller disk responses."""

        if not settings.engines and not settings.propellers:
            return rcs_lin

        enhanced = rcs_lin.astype(float, copy=True)

        if settings.engines:
            for engine in settings.engines:
                axis = engine.axis()
                alignment = np.clip(directions @ axis, 0.0, 1.0)
                area = float(np.pi * engine.radius_m**2)
                cavity_gain = 1.5 + (engine.length_m / max(engine.radius_m, 1e-3))
                enhanced += reflectivity * area * cavity_gain * alignment**2

        if settings.propellers:
            for prop in settings.propellers:
                axis = prop.axis()
                alignment = np.clip(directions @ axis, 0.0, 1.0)
                disk_area = float(np.pi * prop.radius_m**2)
                blade_fill = min(1.0, prop.blade_count * 0.15)
                tip_speed = 2.0 * np.pi * prop.radius_m * prop.rpm / 60.0
                doppler_gain = 1.0 + min(tip_speed / 200.0, 3.0) * 0.25
                enhanced += reflectivity * disk_area * blade_fill * alignment * doppler_gain

        return enhanced

    # --- SBR core worker ---------------------------------------------------

    def _trace_direction_block(
        self,
        mesh: trimesh.Trimesh,
        directions: np.ndarray,
        bundle_grid: np.ndarray,
        max_reflections: int,
        reflectivity: float,
        loss_per_reflection: float,
        k: float,
        edges: Iterable[SharpEdge],
        centers: np.ndarray,
        stop_cb: Callable[[], bool],
        origin_center: np.ndarray,
        origin_distance: float,
        ray_intersector: Any,
        area_faces: np.ndarray,
        face_normals: np.ndarray,
    ) -> np.ndarray:
        """Trace a batch of directions and return their linear RCS contributions."""

        results = np.zeros(len(directions), dtype=float)
        edges_tuple: Tuple[SharpEdge, ...] = tuple(edges)

        for idx, direction in enumerate(directions):
            if stop_cb():
                break

            origin = origin_center - origin_distance * direction
            specular_sum = 0.0j
            basis_u, basis_v = self._orthonormal_basis(direction)

            bundle_origins = (
                origin + bundle_grid[:, 0:1] * basis_u + bundle_grid[:, 1:2] * basis_v
            )

            for ray_origin in bundle_origins:
                energy = 1.0
                path_length = 0.0
                ray_dir = direction

                for _ in range(max_reflections):
                    try:
                        locs, _, tri_idx = ray_intersector.intersects_location(
                            ray_origin[np.newaxis, :],
                            ray_dir[np.newaxis, :],
                            multiple_hits=False,
                        )
                    except Exception:
                        # If the backend fails (e.g. missing acceleration modules)
                        # treat this path as non-contributing instead of crashing.
                        break

                    if len(locs) == 0:
                        break

                    hit = locs[0]
                    face_index = int(tri_idx[0])
                    normal = face_normals[face_index]

                    reflect_dir = ray_dir - 2.0 * float(np.dot(ray_dir, normal)) * normal
                    reflect_dir /= np.linalg.norm(reflect_dir) + 1e-12

                    path_length += float(np.linalg.norm(hit - ray_origin))

                    alignment = float(np.dot(reflect_dir, -ray_dir))
                    if alignment > 0.95:
                        area_term = area_faces[face_index] * (float(np.dot(normal, -ray_dir))) ** 2
                        total_path = self._path_to_receiver(path_length, hit, origin, direction)
                        phase = self._monostatic_phase(k, total_path)
                        specular_sum += energy * area_term * np.exp(1j * phase)

                    energy *= reflectivity * loss_per_reflection
                    if energy < MIN_ENERGY:
                        break

                    ray_origin = hit + 1e-4 * reflect_dir
                    ray_dir = reflect_dir

            # Diffraction contribution for this direction
            if edges_tuple:
                k_hat = direction / (np.linalg.norm(direction) + 1e-12)
                illum_mask = (face_normals @ -k_hat) > 0.0
                edge_term = edge_diffraction_field(edges_tuple, k_hat, k, mesh)
                corner_term = corner_field(
                    k_hat,
                    face_normals,
                    area_faces,
                    centers,
                    k,
                    illuminated_mask=illum_mask,
                )
                diffraction_power = reflectivity * np.abs(edge_term + corner_term) ** 2
            else:
                diffraction_power = 0.0

            averaged_specular = specular_sum / max(len(bundle_grid), 1)
            specular_power = float(np.abs(averaged_specular) ** 2)
            results[idx] = max(specular_power + diffraction_power, 1e-12)

        return results

    # --- geometry helpers --------------------------------------------------

    @staticmethod
    def _orthonormal_basis(direction: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Return two unit vectors spanning the plane perpendicular to *direction*."""
        w = direction / (np.linalg.norm(direction) + 1e-12)
        if abs(float(w[2])) < 0.9:
            helper = np.array([0.0, 0.0, 1.0])
        else:
            helper = np.array([0.0, 1.0, 0.0])
        u = np.cross(helper, w)
        u /= np.linalg.norm(u) + 1e-12
        v = np.cross(w, u)
        v /= np.linalg.norm(v) + 1e-12
        return u, v

    @staticmethod
    def _compute_wavelength(freq_hz: float) -> float:
        """Return the free-space wavelength (metres) for ``freq_hz``."""
        c = 3.0e8
        return c / max(freq_hz, 1e-9)

    @staticmethod
    def _monostatic_phase(k: float, total_path_length: float) -> float:
        """Propagation phase for a given total path length."""
        return k * total_path_length

    @staticmethod
    def _direction_from_angles(yaw_deg: float, elev_deg: float) -> np.ndarray:
        """Convert azimuth/elevation angles in degrees to a unit vector."""
        az = np.radians(yaw_deg)
        el = np.radians(elev_deg)
        return np.array(
            [
                np.cos(el) * np.cos(az),
                np.cos(el) * np.sin(az),
                np.sin(el),
            ]
        )

    @staticmethod
    def _path_to_receiver(
        path_length: float,
        hit: np.ndarray,
        rx_origin: np.ndarray,
        rx_dir: np.ndarray,
    ) -> float:
        """Approximate Tx→hit plus hit→Rx path length for phase."""
        del rx_dir  # orientation is implicit in ``rx_origin``
        return path_length + float(np.linalg.norm(hit - rx_origin))

    # --- material / polarisation handling ---------------------------------

    @staticmethod
    def _select_reflectivity(material: Material, polarization: str) -> float:
        """Choose an effective scalar reflectivity for the desired polarisation."""

        def _get_optional(attr: str) -> Optional[float]:
            if hasattr(material, attr):
                value = getattr(material, attr)
            elif hasattr(material, "get"):
                try:
                    value = material.get(attr)  # type: ignore[call-arg]
                except TypeError:
                    value = None
            else:
                value = None

            if value is None:
                return None
            try:
                return float(value)
            except (TypeError, ValueError):
                return None

        base = _get_optional("reflectivity") or 1.0

        pol = polarization.upper().replace("-", "").replace("/", "").strip()

        refl_hh = _get_optional("reflectivity_hh")
        refl_vv = _get_optional("reflectivity_vv")
        refl_h = _get_optional("reflectivity_h")
        refl_v = _get_optional("reflectivity_v")

        if refl_hh is None:
            refl_hh = refl_h if refl_h is not None else base
        if refl_vv is None:
            refl_vv = refl_v if refl_v is not None else base

        if not np.isfinite(refl_hh) or refl_hh < 0.0:
            refl_hh = base
        if not np.isfinite(refl_vv) or refl_vv < 0.0:
            refl_vv = base

        refl_hv = _get_optional("reflectivity_hv")
        refl_vh = _get_optional("reflectivity_vh")

        if refl_hv is None and refl_vh is None:
            cross_default = 0.1 * (refl_hh + refl_vv) * 0.5
            refl_hv = cross_default
            refl_vh = cross_default
        else:
            if refl_hv is None:
                refl_hv = refl_vh if refl_vh is not None else 0.0
            if refl_vh is None:
                refl_vh = refl_hv if refl_hv is not None else 0.0

        if not np.isfinite(refl_hv) or refl_hv < 0.0:
            refl_hv = 0.0
        if not np.isfinite(refl_vh) or refl_vh < 0.0:
            refl_vh = 0.0

        if pol in {"H", "HH"}:
            return max(float(refl_hh), 0.0)
        if pol in {"V", "VV"}:
            return max(float(refl_vv), 0.0)
        if pol in {"HV", "VH", "X", "XPOL", "CROSS"}:
            return max(float(0.5 * (refl_hv + refl_vh)), 0.0)
        if pol in {"RL", "LR", "RC", "LC", "C", "CIRC"}:
            return max(float(0.5 * (refl_hh + refl_vv)), 0.0)

        return max(float(0.5 * (refl_hh + refl_vv)), 0.0)


__all__ = [
    "BAND_DEFAULTS",
    "FrequencySweep",
    "SimulationSettings",
    "Material",
    "EngineMount",
    "Propeller",
    "SimulationResult",
    "RCSEngine",
    "to_dbsm",
]
