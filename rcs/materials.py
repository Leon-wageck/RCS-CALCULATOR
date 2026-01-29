"""Material definitions and helper database wrapper."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .rcs_engine import Material


@dataclass(frozen=True)
class _LegacyMaterial:
    """Internal legacy representation used to seed the editable Material database.

    sigma:
        Conductivity [S/m].
    eps_r:
        Relative permittivity (real part).
    tan_delta:
        Loss tangent (imaginary part approximated via eps_r * tan_delta).
    reflectivity:
        Baseline scalar reflectivity (power-domain, 0..1).

    Optional fields allow simple anisotropic / polarimetric presets. If left
    as None, they fall back to the scalar reflectivity via the conversion step.

    reflectivity_h / reflectivity_v:
        Directional reflectivity for H and V polarizations.

    reflectivity_hv / reflectivity_vh:
        Cross-polar reflectivities (H->V and V->H) in the power domain.
    """

    sigma: float
    eps_r: float
    tan_delta: float
    reflectivity: float
    reflectivity_h: float | None = None
    reflectivity_v: float | None = None
    reflectivity_hv: float | None = None
    reflectivity_vh: float | None = None


MATERIAL_DB: Dict[str, _LegacyMaterial] = {
    # --- Metals / high-conductivity skins ---
    "Aluminium": _LegacyMaterial(sigma=3.5e7, eps_r=1.0, tan_delta=0.0, reflectivity=0.99),
    "Aluminium – Lackiert": _LegacyMaterial(
        sigma=3.5e7, eps_r=2.5, tan_delta=0.02, reflectivity=0.97
    ),
    "Stahl": _LegacyMaterial(sigma=1e7, eps_r=1.0, tan_delta=0.0, reflectivity=0.98),
    "Titan": _LegacyMaterial(sigma=2.4e6, eps_r=1.0, tan_delta=0.0, reflectivity=0.95),
    "Kupfer": _LegacyMaterial(sigma=5.8e7, eps_r=1.0, tan_delta=0.0, reflectivity=0.99),
    "Gold": _LegacyMaterial(sigma=4.1e7, eps_r=1.0, tan_delta=0.0, reflectivity=0.995),

    # --- Conductive composites / structural materials ---
    "Carbon": _LegacyMaterial(sigma=1e4, eps_r=5.0, tan_delta=0.05, reflectivity=0.6),
    "Graphit": _LegacyMaterial(sigma=1e3, eps_r=12.0, tan_delta=0.1, reflectivity=0.5),
    "CFRP Flugzeughaut": _LegacyMaterial(
        sigma=5e3, eps_r=7.0, tan_delta=0.08, reflectivity=0.55
    ),
    "CFRP Sandwichpanel": _LegacyMaterial(
        sigma=1e3, eps_r=5.5, tan_delta=0.06, reflectivity=0.45
    ),
    "GFK Strukturpanel": _LegacyMaterial(
        sigma=1e-5, eps_r=4.5, tan_delta=0.04, reflectivity=0.35
    ),

    # --- Dielectrics, radomes, canopies ---
    "PVC": _LegacyMaterial(sigma=1e-15, eps_r=3.0, tan_delta=0.02, reflectivity=0.3),
    "Polycarbonat": _LegacyMaterial(sigma=1e-15, eps_r=2.9, tan_delta=0.015, reflectivity=0.28),
    "Glas – Cockpitkanzel": _LegacyMaterial(
        sigma=1e-14, eps_r=6.5, tan_delta=0.02, reflectivity=0.35
    ),
    "Radom – Low-Loss": _LegacyMaterial(
        sigma=1e-8, eps_r=3.2, tan_delta=0.01, reflectivity=0.2
    ),
    "Radom – Breitband": _LegacyMaterial(
        sigma=5e-8, eps_r=4.0, tan_delta=0.03, reflectivity=0.18
    ),

    # --- RAM / stealth coatings ---
    "Gummi (RAM)": _LegacyMaterial(sigma=1e-5, eps_r=10.0, tan_delta=0.3, reflectivity=0.1),
    "RAM – Iron Ball Paint": _LegacyMaterial(
        sigma=1e-4, eps_r=10.0, tan_delta=0.15, reflectivity=0.25
    ),
    "RAM – Carbon Nanotube": _LegacyMaterial(
        sigma=1e2, eps_r=12.0, tan_delta=0.1, reflectivity=0.1
    ),
    "RAM – Conductive Polymer": _LegacyMaterial(
        sigma=1e0, eps_r=5.0, tan_delta=0.3, reflectivity=0.2
    ),
    "RAM – Magnetic Ferrite": _LegacyMaterial(
        sigma=1e-2, eps_r=13.0, tan_delta=0.5, reflectivity=0.15
    ),
    "RAM – Foam Layer": _LegacyMaterial(
        sigma=1e-6, eps_r=1.5, tan_delta=0.05, reflectivity=0.3
    ),
    "RAM – Dallenbach Layer": _LegacyMaterial(
        sigma=1e-5, eps_r=7.0, tan_delta=0.2, reflectivity=0.05
    ),
    "RAM – Jaumann Layer": _LegacyMaterial(
        sigma=1e-4, eps_r=9.0, tan_delta=0.4, reflectivity=0.05
    ),
    "MagRAM": _LegacyMaterial(sigma=1e-4, eps_r=15.0, tan_delta=0.25, reflectivity=0.05),
    "Metamaterial RAM": _LegacyMaterial(
        sigma=1e-7, eps_r=25.0, tan_delta=0.4, reflectivity=0.01
    ),
    "Carbon Nanotube Foam": _LegacyMaterial(
        sigma=1e1, eps_r=7.5, tan_delta=0.03, reflectivity=0.15
    ),
    "Spray-on Polymer RAM": _LegacyMaterial(
        sigma=5e-3, eps_r=9.0, tan_delta=0.12, reflectivity=0.2
    ),

    # --- Functional layers / AESA panels / patch arrays ---
    "AESA Panel – H-dominant": _LegacyMaterial(
        sigma=1e4,
        eps_r=3.0,
        tan_delta=0.02,
        reflectivity=0.75,
        reflectivity_h=0.8,
        reflectivity_v=0.6,
        reflectivity_hv=0.05,
        reflectivity_vh=0.05,
    ),
    "AESA Panel – Breitband": _LegacyMaterial(
        sigma=5e4,
        eps_r=3.5,
        tan_delta=0.03,
        reflectivity=0.7,
        reflectivity_h=0.78,
        reflectivity_v=0.62,
        reflectivity_hv=0.06,
        reflectivity_vh=0.06,
    ),
    "Microstrip Patch Array": _LegacyMaterial(
        sigma=2e5,
        eps_r=2.2,
        tan_delta=0.015,
        reflectivity=0.65,
        reflectivity_h=0.7,
        reflectivity_v=0.5,
        reflectivity_hv=0.03,
        reflectivity_vh=0.03,
    ),

    # --- Misc / fluids / internal volumes ---
    "Kerosin (Jet A)": _LegacyMaterial(
        sigma=1e-6, eps_r=2.0, tan_delta=0.02, reflectivity=0.1
    ),
    "Wasser – Süßwasser": _LegacyMaterial(
        sigma=5e-4, eps_r=78.0, tan_delta=0.15, reflectivity=0.5
    ),
    "Wasser – Meerwasser": _LegacyMaterial(
        sigma=4.0, eps_r=75.0, tan_delta=0.2, reflectivity=0.9
    ),
}


class MaterialDatabase:
    """Simple material store with editable entries."""

    def __init__(self) -> None:
        self.materials: Dict[str, Material] = {
            name: self._convert_legacy(name, legacy)
            for name, legacy in MATERIAL_DB.items()
        }

    @staticmethod
    def _convert_legacy(name: str, legacy: _LegacyMaterial) -> Material:
        """Convert from the compact legacy description to the full Material."""
        epsilon_imag = legacy.eps_r * legacy.tan_delta
        return Material(
            name=name,
            epsilon_real=legacy.eps_r,
            epsilon_imag=epsilon_imag,
            conductivity=legacy.sigma,
            reflectivity=legacy.reflectivity,
            reflectivity_h=legacy.reflectivity_h,
            reflectivity_v=legacy.reflectivity_v,
            # Let the RCS engine's _select_reflectivity fall back HH/VV from
            # H/V/base when these are None:
            reflectivity_hh=None,
            reflectivity_vv=None,
            reflectivity_hv=legacy.reflectivity_hv,
            reflectivity_vh=legacy.reflectivity_vh,
        )

    # Public API used by the GUI
    def names(self) -> List[str]:
        return list(self.materials.keys())

    def as_list(self) -> List[Material]:
        return list(self.materials.values())

    def get(self, name: str) -> Material:
        return self.materials[name]

    def add_material(self, material: Material) -> None:
        """Insert or replace a material by its name."""
        self.materials[material.name] = material

    def update_material(self, name: str, **kwargs) -> None:
        """Update an existing material in-place.

        Only the fields provided in kwargs are changed; everything else
        remains as in the existing Material entry.
        """
        if name not in self.materials:
            raise KeyError(f"Unknown material '{name}'")

        current = self.materials[name]
        data = current.as_dict()
        data.update(kwargs)
        updated = Material(**data)

        if updated.name != name:
            self.materials.pop(name, None)
        self.materials[updated.name] = updated

    def delete_material(self, name: str) -> None:
        self.materials.pop(name, None)


__all__ = ["MATERIAL_DB", "MaterialDatabase"]
