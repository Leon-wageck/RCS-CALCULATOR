"""Template storage and matching utilities for NCTR-style signatures."""

from __future__ import annotations

from dataclasses import dataclass, asdict
import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple, Union

import numpy as np

from .rcs_engine import SimulationResult


@dataclass
class SignatureTemplate:
    name: str
    target_class: str
    band: str
    frequencies_hz: List[float]
    azimuth_deg: List[float]
    elevation_deg: List[float]
    polarization: str
    rcs_dbsm: List[List[List[float]]]
    meta: Dict

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_json(cls, text: str) -> "SignatureTemplate":
        data = json.loads(text)
        return cls(
            name=data["name"],
            target_class=data.get("class", data.get("target_class", "unknown")),
            band=data["band"],
            frequencies_hz=data["frequencies_hz"],
            azimuth_deg=data["azimuth_deg"],
            elevation_deg=data["elevation_deg"],
            polarization=data.get("polarization", "H"),
            rcs_dbsm=data["rcs_dbsm"],
            meta=data.get("meta", {}),
        )


class TemplateLibrary:
    """Manage a directory of signature templates.

    By default templates are stored in a user-writable directory under the
    current user's home folder to avoid permission errors when the working
    directory is read-only.
    """

    def __init__(self, directory: Union[str, Path, None] = None) -> None:
        preferred = Path(directory) if directory else Path.home() / ".rcs" / "templates"
        self.directory = self._ensure_directory(preferred, directory_provided=directory is not None)

    def _ensure_directory(self, path: Path, *, directory_provided: bool) -> Path:
        try:
            path.mkdir(parents=True, exist_ok=True)
            return path
        except PermissionError:
            if directory_provided:
                # Caller explicitly requested this directory; propagate the error.
                raise
            fallback = Path.home() / ".rcs" / "templates"
            fallback.mkdir(parents=True, exist_ok=True)
            return fallback

    def list_templates(self) -> List[Path]:
        return sorted(self.directory.glob("*.json"))

    def load_template(self, path: Path) -> SignatureTemplate:
        return SignatureTemplate.from_json(path.read_text())

    def save_template(self, template: SignatureTemplate, *, filename: Optional[str] = None) -> Path:
        fname = filename or f"{template.name}.json"
        path = self.directory / fname
        path.write_text(template.to_json())
        return path

    def create_from_result(
        self,
        result: SimulationResult,
        name: str,
        target_class: str,
        meta: Optional[Dict] = None,
    ) -> SignatureTemplate:
        meta = meta or {}
        meta.setdefault("radar_profile", result.radar_profile)
        meta.setdefault("target_speed_mps", result.target_speed_mps)
        return SignatureTemplate(
            name=name,
            target_class=target_class,
            band=result.band,
            frequencies_hz=result.frequencies_hz.tolist(),
            azimuth_deg=result.azimuth_deg.tolist(),
            elevation_deg=result.elevation_deg.tolist(),
            polarization=result.polarization,
            rcs_dbsm=result.rcs_dbsm.tolist(),
            meta=meta,
        )

    def match(self, result: SimulationResult) -> List[Tuple[SignatureTemplate, float]]:
        matches: List[Tuple[SignatureTemplate, float]] = []
        for path in self.list_templates():
            template = self.load_template(path)
            if template.band != result.band:
                continue
            tpl_arr = np.array(template.rcs_dbsm)
            res = self._resample_to_template(result, template)
            rmse = float(np.sqrt(np.mean((tpl_arr - res) ** 2)))
            matches.append((template, rmse))
        matches.sort(key=lambda x: x[1])
        return matches

    def _resample_to_template(self, result: SimulationResult, template: SignatureTemplate) -> np.ndarray:
        target_freqs = np.array(template.frequencies_hz)
        target_az = np.array(template.azimuth_deg)
        target_el = np.array(template.elevation_deg)

        res_freqs = result.frequencies_hz
        res_az = result.azimuth_deg
        res_el = result.elevation_deg

        freq_interp = np.interp(target_freqs, res_freqs, np.arange(len(res_freqs)))
        freq_idx = np.clip(freq_interp, 0, len(res_freqs) - 1)

        az_interp = np.interp(target_az, res_az, np.arange(len(res_az)))
        az_idx = np.clip(az_interp, 0, len(res_az) - 1)

        el_interp = np.interp(target_el, res_el, np.arange(len(res_el)))
        el_idx = np.clip(el_interp, 0, len(res_el) - 1)

        resampled = np.zeros((len(target_freqs), len(target_el), len(target_az)))
        for fi, f_val in enumerate(freq_idx):
            f0, f1 = int(np.floor(f_val)), min(int(np.ceil(f_val)), len(res_freqs) - 1)
            f_alpha = f_val - f0
            for ei, e_val in enumerate(el_idx):
                e0, e1 = int(np.floor(e_val)), min(int(np.ceil(e_val)), len(res_el) - 1)
                e_alpha = e_val - e0
                for ai, a_val in enumerate(az_idx):
                    a0, a1 = int(np.floor(a_val)), min(int(np.ceil(a_val)), len(res_az) - 1)
                    a_alpha = a_val - a0
                    v000 = result.rcs_dbsm[f0, e0, a0]
                    v001 = result.rcs_dbsm[f0, e0, a1]
                    v010 = result.rcs_dbsm[f0, e1, a0]
                    v011 = result.rcs_dbsm[f0, e1, a1]
                    v100 = result.rcs_dbsm[f1, e0, a0]
                    v101 = result.rcs_dbsm[f1, e0, a1]
                    v110 = result.rcs_dbsm[f1, e1, a0]
                    v111 = result.rcs_dbsm[f1, e1, a1]
                    v00 = v000 * (1 - a_alpha) + v001 * a_alpha
                    v01 = v010 * (1 - a_alpha) + v011 * a_alpha
                    v10 = v100 * (1 - a_alpha) + v101 * a_alpha
                    v11 = v110 * (1 - a_alpha) + v111 * a_alpha
                    v0 = v00 * (1 - e_alpha) + v01 * e_alpha
                    v1 = v10 * (1 - e_alpha) + v11 * e_alpha
                    resampled[fi, ei, ai] = v0 * (1 - f_alpha) + v1 * f_alpha
        return resampled


__all__ = ["SignatureTemplate", "TemplateLibrary"]
