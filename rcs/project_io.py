"""Project save/load helpers."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional, Union

from .rcs_engine import EngineMount, FrequencySweep, Propeller, SimulationSettings


@dataclass
class ProjectState:
    mesh_path: Optional[str]
    settings: SimulationSettings
    material_name: str


def save_project(path: Union[str, Path], state: ProjectState) -> None:
    settings_dict = asdict(state.settings)
    if state.settings.sweep:
        settings_dict["sweep"] = asdict(state.settings.sweep)
    payload = {
        "mesh_path": state.mesh_path,
        "material_name": state.material_name,
        "settings": settings_dict,
    }
    Path(path).write_text(json.dumps(payload, indent=2))


def load_project(path: Union[str, Path]) -> ProjectState:
    data = json.loads(Path(path).read_text())
    settings_data = data["settings"]
    sweep_data = settings_data.pop("sweep", None)
    engines_data = settings_data.pop("engines", [])
    prop_data = settings_data.pop("propellers", [])
    sweep_obj = None
    if sweep_data:
        sweep_obj = FrequencySweep(sweep_data["start_hz"], sweep_data["stop_hz"], sweep_data["steps"])
    settings = SimulationSettings(**settings_data)
    settings.sweep = sweep_obj
    settings.engines = [EngineMount(**eng) for eng in engines_data]
    settings.propellers = [Propeller(**prop) for prop in prop_data]
    return ProjectState(mesh_path=data.get("mesh_path"), settings=settings, material_name=data.get("material_name", ""))


__all__ = ["ProjectState", "save_project", "load_project"]
