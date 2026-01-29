"""PyQt5 main window for the RCS calculator."""

from __future__ import annotations
from mpl_toolkits.mplot3d.axes3d import Axes3D

from pathlib import Path
from typing import List, Optional, Mapping, cast  # ← added Mapping, cast

import matplotlib
matplotlib.use("Qt5Agg")  # ← force PyQt5 backend

import matplotlib.pyplot as plt
import numpy as np
import trimesh
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg  # ← Qt5 backend  # type: ignore[reportPrivateImportUsage]
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from PyQt5 import QtCore, QtWidgets

from rcs.materials import MaterialDatabase
from rcs.project_io import ProjectState, load_project, save_project
from rcs.radar_profiles import RADAR_PROFILES, RadarProfile
from rcs.rcs_engine import (
    BAND_DEFAULTS,
    EngineMount,
    FrequencySweep,
    Material,
    Propeller,
    RCSEngine,
    SimulationResult,
    SimulationSettings,
)
from rcs.templates import TemplateLibrary

def _update_band_defaults(self) -> None:
    # Help Pylance by making the type explicit
    bands: Mapping[str, tuple[float, float]] = cast(
        Mapping[str, tuple[float, float]],
        BAND_DEFAULTS,
    )
    band = self.band_combo.currentText()
    start, stop = bands.get(band, bands["S"])
    self.single_freq.setValue((start + stop) / 2 / 1e9)
    self.sweep_start.setValue(start / 1e9)
    self.sweep_stop.setValue(stop / 1e9)


class SimulationWorker(QtCore.QThread):
    progress = QtCore.pyqtSignal(int)
    finished = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str)

    def __init__(
        self,
        engine: RCSEngine,
        mesh: trimesh.Trimesh,
        material: Material,
        settings: SimulationSettings,
    ) -> None:
        super().__init__()
        self.engine = engine
        self.mesh = mesh
        self.material = material
        self.settings = settings

    def run(self) -> None:  # noqa: D401
        try:
            self.engine.reset()
            result = self.engine.compute(
                self.mesh,
                self.material,
                self.settings,
                progress=self.progress.emit,
            )
            self.finished.emit(result)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class PlotCanvas(FigureCanvasQTAgg):
    def __init__(self) -> None:
        self.figure = Figure(figsize=(5, 4))
        super().__init__(self.figure)
        self.ax = self.figure.add_subplot(111)

    def clear(self) -> None:
        self.figure.clf()
        self.ax = self.figure.add_subplot(111)
        self.draw_idle()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        # cache attributes here
        self._az_grid = None
        self._el_grid = None
        self._az_deg_grid = None
        self._el_deg_grid = None

        self._rcs_lin = None
        self._rcs_norm = None
        self._rcs_radius = None
        self.setWindowTitle("Radar RCS Studio")
        self.resize(1200, 800)

        self.material_db = MaterialDatabase()
        self.template_lib = TemplateLibrary()
        self.engine = RCSEngine()

        self.mesh: Optional[trimesh.Trimesh] = None
        self.mesh_path: Optional[Path] = None
        self.result: Optional[SimulationResult] = None
        self.engines: List[EngineMount] = []
        self.propellers: List[Propeller] = []

        self._build_ui()
        self._connect_actions()
        self._refresh_powerplant_tables()
        self._update_band_defaults()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QHBoxLayout(central)

        self.controls = self._build_controls()
        layout.addWidget(self.controls, 0)

        self.tabs = QtWidgets.QTabWidget()
        layout.addWidget(self.tabs, 1)

        # Model preview tab
        self.model_canvas = PlotCanvas()
        model_tab = QtWidgets.QWidget()
        model_layout = QtWidgets.QVBoxLayout(model_tab)
        model_layout.addWidget(self.model_canvas)
        self.tabs.addTab(model_tab, "3D Model")

        # 2D polar plot tab
        self.polar_canvas = PlotCanvas()
        polar_tab = QtWidgets.QWidget()
        polar_layout = QtWidgets.QVBoxLayout(polar_tab)
        controls = QtWidgets.QHBoxLayout()
        self.elevation_spin = QtWidgets.QDoubleSpinBox()
        self.elevation_spin.setRange(-90, 90)
        self.elevation_spin.setValue(0.0)
        controls.addWidget(QtWidgets.QLabel("Elevation slice (deg):"))
        controls.addWidget(self.elevation_spin)
        self.scale_mode = QtWidgets.QComboBox()
        self.scale_mode.addItems(["dBsm", "Linear"])
        controls.addWidget(QtWidgets.QLabel("Scale:"))
        controls.addWidget(self.scale_mode)
        controls.addStretch(1)
        polar_layout.addLayout(controls)
        polar_layout.addWidget(self.polar_canvas)
        self.tabs.addTab(polar_tab, "2D Polar")

                # 3D RCS plot
        self.rcs3d_canvas = PlotCanvas()
        rcs_tab = QtWidgets.QWidget()
        rcs_layout = QtWidgets.QVBoxLayout(rcs_tab)
        rcs_controls = QtWidgets.QHBoxLayout()

        self.freq_selector = QtWidgets.QComboBox()
        self.freq_selector.setEnabled(False)
        rcs_controls.addWidget(QtWidgets.QLabel("Display freq:"))
        rcs_controls.addWidget(self.freq_selector)

        # NEW: 3D scale mode selector
        self.rcs3d_scale_mode = QtWidgets.QComboBox()
        self.rcs3d_scale_mode.addItems(
            [
                "dB (radius & color)",
                "Linear (radius & color)",
                "Linear (fixed radius, color only)",
            ]
        )
        rcs_controls.addWidget(QtWidgets.QLabel("3D scale:"))
        rcs_controls.addWidget(self.rcs3d_scale_mode)

        self.clip_min = QtWidgets.QDoubleSpinBox()
        self.clip_min.setRange(-100, 100)
        self.clip_min.setValue(-40)
        self.clip_max = QtWidgets.QDoubleSpinBox()
        self.clip_max.setRange(-20, 100)
        self.clip_max.setValue(20)
        rcs_controls.addWidget(QtWidgets.QLabel("Min dB:"))
        rcs_controls.addWidget(self.clip_min)
        rcs_controls.addWidget(QtWidgets.QLabel("Max dB:"))
        rcs_controls.addWidget(self.clip_max)
        rcs_controls.addStretch(1)

        rcs_layout.addLayout(rcs_controls)
        rcs_layout.addWidget(self.rcs3d_canvas)
        self.tabs.addTab(rcs_tab, "3D RCS")


        # Heatmap tab
        self.heatmap_canvas = PlotCanvas()
        heatmap_tab = QtWidgets.QWidget()
        heatmap_layout = QtWidgets.QVBoxLayout(heatmap_tab)
        heat_controls = QtWidgets.QHBoxLayout()
        self.heatmap_freq_selector = QtWidgets.QComboBox()
        self.heatmap_freq_selector.setEnabled(False)
        heat_controls.addWidget(QtWidgets.QLabel("Display freq:"))
        heat_controls.addWidget(self.heatmap_freq_selector)
        self.heat_clip_min = QtWidgets.QDoubleSpinBox()
        self.heat_clip_min.setRange(-120, 120)
        self.heat_clip_min.setValue(-60)
        self.heat_clip_min.setSingleStep(1)
        self.heat_clip_max = QtWidgets.QDoubleSpinBox()
        self.heat_clip_max.setRange(-120, 120)
        self.heat_clip_max.setValue(40)
        self.heat_clip_max.setSingleStep(1)
        heat_controls.addWidget(QtWidgets.QLabel("Clip min (dB):"))
        heat_controls.addWidget(self.heat_clip_min)
        heat_controls.addWidget(QtWidgets.QLabel("Clip max (dB):"))
        heat_controls.addWidget(self.heat_clip_max)
        heat_controls.addStretch(1)
        heatmap_layout.addLayout(heat_controls)
        heatmap_layout.addWidget(self.heatmap_canvas)
        self.tabs.addTab(heatmap_tab, "Heatmap")

        # Templates tab
        self.templates_table = QtWidgets.QTableWidget(0, 4)
        self.templates_table.setHorizontalHeaderLabels(
            ["Name", "Class", "Band", "Score"]
        )
        template_tab = QtWidgets.QWidget()
        template_layout = QtWidgets.QVBoxLayout(template_tab)
        btns = QtWidgets.QHBoxLayout()
        self.refresh_templates_btn = QtWidgets.QPushButton("Refresh")
        self.create_template_btn = QtWidgets.QPushButton("Create from result")
        self.match_template_btn = QtWidgets.QPushButton("Run template matching")
        btns.addWidget(self.refresh_templates_btn)
        btns.addWidget(self.create_template_btn)
        btns.addWidget(self.match_template_btn)
        btns.addStretch(1)
        template_layout.addLayout(btns)
        template_layout.addWidget(self.templates_table)
        self.tabs.addTab(template_tab, "Templates")

        # Status bar elements
        self.progress = QtWidgets.QProgressBar()
        self.status_label = QtWidgets.QLabel("Ready")
        status = QtWidgets.QStatusBar()
        status.addWidget(self.progress, 1)
        status.addWidget(self.status_label, 1)
        self.setStatusBar(status)

    def _populate_radar_presets(self) -> None:
        self.radar_combo.clear()
        profiles: Mapping[str, RadarProfile] = cast(
            Mapping[str, RadarProfile], RADAR_PROFILES
        )
        for name in sorted(profiles.keys()):
            self.radar_combo.addItem(name)

    def _build_controls(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(widget)

        # File chooser
        file_layout = QtWidgets.QHBoxLayout()
        self.file_label = QtWidgets.QLabel("No file loaded")
        self.file_btn = QtWidgets.QPushButton("Open STL")
        file_layout.addWidget(self.file_label)
        file_layout.addWidget(self.file_btn)
        form.addRow("Model:", file_layout)

        # Radar presets
        self.radar_combo = QtWidgets.QComboBox()
        self._populate_radar_presets()
        form.addRow("Radar preset:", self.radar_combo)

        # Band
        self.band_combo = QtWidgets.QComboBox()
        self.band_combo.addItems(["L", "S", "C", "X"])
        form.addRow("Band:", self.band_combo)

        # Frequency controls
        freq_layout = QtWidgets.QGridLayout()
        self.freq_mode = QtWidgets.QComboBox()
        self.freq_mode.addItems(["Single", "Sweep"])
        freq_layout.addWidget(QtWidgets.QLabel("Mode"), 0, 0)
        freq_layout.addWidget(self.freq_mode, 0, 1)
        self.single_freq = QtWidgets.QDoubleSpinBox()
        self.single_freq.setRange(0.5, 40.0)
        self.single_freq.setSuffix(" GHz")
        self.single_freq.setValue(10.0)
        freq_layout.addWidget(self.single_freq, 1, 0, 1, 2)
        self.sweep_start = QtWidgets.QDoubleSpinBox()
        self.sweep_start.setRange(0.5, 40.0)
        self.sweep_stop = QtWidgets.QDoubleSpinBox()
        self.sweep_stop.setRange(0.5, 40.0)
        self.sweep_steps = QtWidgets.QSpinBox()
        self.sweep_steps.setRange(2, 200)
        self.sweep_steps.setValue(5)
        freq_layout.addWidget(QtWidgets.QLabel("Start (GHz)"), 2, 0)
        freq_layout.addWidget(self.sweep_start, 2, 1)
        freq_layout.addWidget(QtWidgets.QLabel("Stop (GHz)"), 3, 0)
        freq_layout.addWidget(self.sweep_stop, 3, 1)
        freq_layout.addWidget(QtWidgets.QLabel("Steps"), 4, 0)
        freq_layout.addWidget(self.sweep_steps, 4, 1)
        form.addRow("Frequency:", freq_layout)

        # Angles
        self.az_start = QtWidgets.QDoubleSpinBox()
        self.az_start.setRange(0, 360)
        self.az_stop = QtWidgets.QDoubleSpinBox()
        self.az_stop.setRange(0, 360)
        self.az_stop.setValue(360)
        self.az_step = QtWidgets.QDoubleSpinBox()
        self.az_step.setRange(0.5, 45)
        self.az_step.setSingleStep(0.5)
        self.az_step.setValue(5)
        self.el_start = QtWidgets.QDoubleSpinBox()
        self.el_start.setRange(-90, 90)
        self.el_start.setValue(-90)
        self.el_stop = QtWidgets.QDoubleSpinBox()
        self.el_stop.setRange(-90, 90)
        self.el_stop.setValue(90)
        self.el_step = QtWidgets.QDoubleSpinBox()
        self.el_step.setRange(0.5, 30)
        self.el_step.setSingleStep(0.5)
        self.el_step.setValue(5)
        angle_grid = QtWidgets.QGridLayout()
        angle_grid.addWidget(QtWidgets.QLabel("Az start"), 0, 0)
        angle_grid.addWidget(self.az_start, 0, 1)
        angle_grid.addWidget(QtWidgets.QLabel("Az stop"), 1, 0)
        angle_grid.addWidget(self.az_stop, 1, 1)
        angle_grid.addWidget(QtWidgets.QLabel("Az step"), 2, 0)
        angle_grid.addWidget(self.az_step, 2, 1)
        angle_grid.addWidget(QtWidgets.QLabel("El start"), 3, 0)
        angle_grid.addWidget(self.el_start, 3, 1)
        angle_grid.addWidget(QtWidgets.QLabel("El stop"), 4, 0)
        angle_grid.addWidget(self.el_stop, 4, 1)
        angle_grid.addWidget(QtWidgets.QLabel("El step"), 5, 0)
        angle_grid.addWidget(self.el_step, 5, 1)
        form.addRow("Angles:", angle_grid)

        # Platform speed
        self.speed_spin = QtWidgets.QDoubleSpinBox()
        self.speed_spin.setRange(0, 1500)
        self.speed_spin.setSuffix(" m/s")
        self.speed_spin.setSingleStep(10)
        self.speed_spin.setValue(250)
        form.addRow("Aircraft speed:", self.speed_spin)

        # Polarization / reflections
        self.pol_combo = QtWidgets.QComboBox()
        self.pol_combo.addItems(["H", "V"])
        form.addRow("Polarization:", self.pol_combo)
        self.reflections_spin = QtWidgets.QSpinBox()
        self.reflections_spin.setRange(1, 10)
        self.reflections_spin.setValue(3)
        form.addRow("Max reflections:", self.reflections_spin)

        self.method_combo = QtWidgets.QComboBox()
        self.method_combo.addItem("Fast Approximation (facet PO)", "fast")
        self.method_combo.addItem("Realistic LO Mode", "lo")
        self.method_combo.addItem("Experimental SBR (ray tracing)", "sbr")
        form.addRow("RCS method:", self.method_combo)

        # Material selection
        self.material_combo = QtWidgets.QComboBox()
        self.material_combo.addItems(self.material_db.names())
        form.addRow("Material:", self.material_combo)

        powerplant_group = QtWidgets.QGroupBox("Powerplant / propulsor modeling")
        pp_layout = QtWidgets.QVBoxLayout(powerplant_group)
        self.engine_table = QtWidgets.QTableWidget(0, 6)
        self.engine_table.setHorizontalHeaderLabels(
            ["X", "Y", "Z", "Radius (m)", "Length (m)", "Yaw (deg)"]
        )
        header = self.engine_table.horizontalHeader()
        if header is not None:
            header.setStretchLastSection(True)
        pp_layout.addWidget(QtWidgets.QLabel("Engines / intakes"))
        pp_layout.addWidget(self.engine_table)
        engine_btns = QtWidgets.QHBoxLayout()
        self.add_engine_btn = QtWidgets.QPushButton("Add engine")
        self.edit_engine_btn = QtWidgets.QPushButton("Edit")
        self.remove_engine_btn = QtWidgets.QPushButton("Remove")
        engine_btns.addWidget(self.add_engine_btn)
        engine_btns.addWidget(self.edit_engine_btn)
        engine_btns.addWidget(self.remove_engine_btn)
        engine_btns.addStretch(1)
        pp_layout.addLayout(engine_btns)

        self.prop_table = QtWidgets.QTableWidget(0, 6)
        self.prop_table.setHorizontalHeaderLabels(
            ["X", "Y", "Z", "Radius (m)", "Blades", "RPM"]
        )
        prop_header = self.prop_table.horizontalHeader()
        if prop_header is not None:
            prop_header.setStretchLastSection(True)
        pp_layout.addWidget(QtWidgets.QLabel("Propellers"))
        pp_layout.addWidget(self.prop_table)
        prop_btns = QtWidgets.QHBoxLayout()
        self.add_prop_btn = QtWidgets.QPushButton("Add propeller")
        self.edit_prop_btn = QtWidgets.QPushButton("Edit")
        self.remove_prop_btn = QtWidgets.QPushButton("Remove")
        prop_btns.addWidget(self.add_prop_btn)
        prop_btns.addWidget(self.edit_prop_btn)
        prop_btns.addWidget(self.remove_prop_btn)
        prop_btns.addStretch(1)
        pp_layout.addLayout(prop_btns)

        form.addRow(powerplant_group)

        # Buttons
        self.run_btn = QtWidgets.QPushButton("Run simulation")
        self.stop_btn = QtWidgets.QPushButton("Stop")
        form.addRow(self.run_btn, self.stop_btn)

        return widget

    def _connect_actions(self) -> None:
        self.file_btn.clicked.connect(self._open_mesh)
        self.band_combo.currentTextChanged.connect(self._update_band_defaults)
        self.radar_combo.currentTextChanged.connect(self._on_radar_profile_changed)
        self.run_btn.clicked.connect(self._run_simulation)
        self.stop_btn.clicked.connect(self._stop_simulation)
        self.create_template_btn.clicked.connect(self._create_template)
        self.match_template_btn.clicked.connect(self._match_templates)
        self.refresh_templates_btn.clicked.connect(self._refresh_templates)
        self.elevation_spin.valueChanged.connect(self._update_polar_plot)
        self.scale_mode.currentTextChanged.connect(self._update_polar_plot)
        self.clip_min.valueChanged.connect(self._update_rcs_plot)
        self.clip_max.valueChanged.connect(self._update_rcs_plot)
        self.freq_selector.currentIndexChanged.connect(self._update_rcs_plot)
        self.rcs3d_scale_mode.currentTextChanged.connect(self._update_rcs_plot)
        self.heat_clip_min.valueChanged.connect(self._update_heatmap_plot)
        self.heat_clip_max.valueChanged.connect(self._update_heatmap_plot)
        self.heatmap_freq_selector.currentIndexChanged.connect(self._update_heatmap_plot)

        # Powerplant controls
        self.add_engine_btn.clicked.connect(self._add_engine)
        self.edit_engine_btn.clicked.connect(self._edit_engine)
        self.remove_engine_btn.clicked.connect(self._remove_engine)
        self.add_prop_btn.clicked.connect(self._add_prop)
        self.edit_prop_btn.clicked.connect(self._edit_prop)
        self.remove_prop_btn.clicked.connect(self._remove_prop)

        # Menu bar
        menu_bar = self.menuBar()
        if menu_bar is not None:
            file_menu = menu_bar.addMenu("File")
            if file_menu is not None:
                open_action = file_menu.addAction("Open STL")
                save_project_action = file_menu.addAction("Save Project")
                load_project_action = file_menu.addAction("Load Project")
                export_csv_action = file_menu.addAction("Export CSV")
                export_plot_action = file_menu.addAction("Export Plots")
                exit_action = file_menu.addAction("Exit")

                if open_action is not None:
                    open_action.triggered.connect(self._open_mesh)
                if save_project_action is not None:
                    save_project_action.triggered.connect(self._save_project)
                if load_project_action is not None:
                    load_project_action.triggered.connect(self._load_project)
                if export_csv_action is not None:
                    export_csv_action.triggered.connect(self._export_csv)
            materials_menu = menu_bar.addMenu("Materials")
            if materials_menu is not None:
                edit_materials_action = materials_menu.addAction("Edit materials")
                if edit_materials_action is not None:
                    edit_materials_action.triggered.connect(self._edit_materials)

            if export_csv_action is not None:
                export_csv_action.triggered.connect(self._export_csv)
            if export_plot_action is not None:
                export_plot_action.triggered.connect(self._export_plots)
            if exit_action is not None:
                exit_action.triggered.connect(self._on_exit)

            templates_menu = menu_bar.addMenu("Templates / NCTR")
            if templates_menu is not None:
                templates_menu.addAction(
                    self.create_template_btn.text(), self._create_template
                )
                templates_menu.addAction(
                    self.match_template_btn.text(), self._match_templates
                )

    # ------------------------------------------------------------------
    def _update_band_defaults(self) -> None:
        bands: Mapping[str, tuple[float, float]] = cast(
            Mapping[str, tuple[float, float]], BAND_DEFAULTS
        )
        band = self.band_combo.currentText()
        start, stop = bands.get(band, bands["S"])
        self.single_freq.setValue((start + stop) / 2 / 1e9)
        self.sweep_start.setValue(start / 1e9)
        self.sweep_stop.setValue(stop / 1e9)

    def _on_radar_profile_changed(self, name: str) -> None:
        profiles: Mapping[str, RadarProfile] = cast(
            Mapping[str, RadarProfile], RADAR_PROFILES
        )
        profile: Optional[RadarProfile] = profiles.get(name)
        if profile is None or name.startswith("Custom"):
            return

        self.band_combo.setCurrentText(profile.band)
        preferred_pol = profile.polarization.split("/")[0] if profile.polarization else ""
        if preferred_pol:
            idx = self.pol_combo.findText(preferred_pol)
            if idx >= 0:
                self.pol_combo.setCurrentIndex(idx)
        if profile.max_reflections:
            self.reflections_spin.setValue(profile.max_reflections)
        if profile.default_speed_mps is not None:
            self.speed_spin.setValue(profile.default_speed_mps)

        if profile.sweep_start_ghz and profile.sweep_stop_ghz:
            self.freq_mode.setCurrentText("Sweep")
            self.sweep_start.setValue(profile.sweep_start_ghz)
            self.sweep_stop.setValue(profile.sweep_stop_ghz)
            if profile.sweep_steps:
                self.sweep_steps.setValue(profile.sweep_steps)
        elif profile.frequency_ghz:
            self.freq_mode.setCurrentText("Single")
            self.single_freq.setValue(profile.frequency_ghz)

    def _open_mesh(self) -> None:
        path_str, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Open STL",
            str(Path.home()),
            "Mesh (*.stl *.obj *.glb *.gltf)",
        )
        if not path_str:
            return

        path = Path(path_str)
        try:
            mesh_obj = trimesh.load_mesh(path, force="mesh")

            mesh_t: trimesh.Trimesh
            if isinstance(mesh_obj, trimesh.Scene):
                parts = [
                    g
                    for g in mesh_obj.geometry.values()
                    if isinstance(g, trimesh.Trimesh)
                ]
                if not parts:
                    raise ValueError("Scene contains no Trimesh geometry.")
                mesh_t = trimesh.util.concatenate(parts)  # type: ignore[arg-type]
            elif isinstance(mesh_obj, trimesh.Trimesh):
                mesh_t = mesh_obj
            else:
                raise ValueError("Unsupported mesh type loaded.")

            mesh_t.remove_unreferenced_vertices()
            mesh_t.update_faces(mesh_t.nondegenerate_faces())

            if len(mesh_t.faces) > 50000:
                simplify = getattr(
                    mesh_t, "simplify_quadratic_decimation", None
                )  # type: ignore[attr-defined]
                if callable(simplify):
                    mesh_t = simplify(50000)  # type: ignore[misc]

            self.mesh = mesh_t
            self.mesh_path = path
            self.file_label.setText(path.name)
            self._draw_mesh_preview()
        except Exception as exc:  # noqa: BLE001
            QtWidgets.QMessageBox.critical(
                self,
                "Error loading mesh",
                f"Failed to load mesh:\n{exc}",
            )
            self.mesh = None
            self.mesh_path = None
            self.file_label.setText("No file loaded")
            self.model_canvas.clear()

    def _refresh_powerplant_tables(self) -> None:
        self.engine_table.setRowCount(0)
        for eng in self.engines:
            row = self.engine_table.rowCount()
            self.engine_table.insertRow(row)
            for col, value in enumerate(
                [eng.x, eng.y, eng.z, eng.radius_m, eng.length_m, eng.yaw_deg]
            ):
                self.engine_table.setItem(
                    row, col, QtWidgets.QTableWidgetItem(f"{value:.2f}")
                )

        self.prop_table.setRowCount(0)
        for prop in self.propellers:
            row = self.prop_table.rowCount()
            self.prop_table.insertRow(row)
            values = [
                prop.x,
                prop.y,
                prop.z,
                prop.radius_m,
                prop.blade_count,
                prop.rpm,
            ]
            for col, value in enumerate(values):
                fmt = "{:.2f}" if isinstance(value, float) else "{}"
                self.prop_table.setItem(
                    row, col, QtWidgets.QTableWidgetItem(fmt.format(value))
                )

    def _prompt_engine(self, existing: Optional[EngineMount] = None) -> Optional[EngineMount]:
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Engine / intake")
        form = QtWidgets.QFormLayout(dialog)
        x = QtWidgets.QDoubleSpinBox()
        y = QtWidgets.QDoubleSpinBox()
        z = QtWidgets.QDoubleSpinBox()
        for widget in (x, y, z):
            widget.setRange(-50.0, 50.0)
            widget.setDecimals(2)
        radius = QtWidgets.QDoubleSpinBox()
        radius.setRange(0.05, 10.0)
        radius.setValue(0.5)
        length = QtWidgets.QDoubleSpinBox()
        length.setRange(0.05, 20.0)
        length.setValue(1.0)
        yaw = QtWidgets.QDoubleSpinBox()
        yaw.setRange(-180.0, 180.0)
        yaw.setDecimals(1)

        if existing:
            x.setValue(existing.x)
            y.setValue(existing.y)
            z.setValue(existing.z)
            radius.setValue(existing.radius_m)
            length.setValue(existing.length_m)
            yaw.setValue(existing.yaw_deg)

        form.addRow("X (m)", x)
        form.addRow("Y (m)", y)
        form.addRow("Z (m)", z)
        form.addRow("Radius (m)", radius)
        form.addRow("Length (m)", length)
        form.addRow("Yaw (deg)", yaw)
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        form.addRow(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            return EngineMount(
                x=x.value(),
                y=y.value(),
                z=z.value(),
                radius_m=radius.value(),
                length_m=length.value(),
                yaw_deg=yaw.value(),
            )
        return None

    def _prompt_prop(self, existing: Optional[Propeller] = None) -> Optional[Propeller]:
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Propeller")
        form = QtWidgets.QFormLayout(dialog)
        x = QtWidgets.QDoubleSpinBox()
        y = QtWidgets.QDoubleSpinBox()
        z = QtWidgets.QDoubleSpinBox()
        for widget in (x, y, z):
            widget.setRange(-50.0, 50.0)
            widget.setDecimals(2)
        radius = QtWidgets.QDoubleSpinBox()
        radius.setRange(0.1, 20.0)
        radius.setValue(1.0)
        blades = QtWidgets.QSpinBox()
        blades.setRange(2, 10)
        rpm = QtWidgets.QDoubleSpinBox()
        rpm.setRange(0.0, 6000.0)
        rpm.setValue(1200.0)
        rpm.setDecimals(1)
        yaw = QtWidgets.QDoubleSpinBox()
        yaw.setRange(-180.0, 180.0)
        yaw.setDecimals(1)

        if existing:
            x.setValue(existing.x)
            y.setValue(existing.y)
            z.setValue(existing.z)
            radius.setValue(existing.radius_m)
            blades.setValue(existing.blade_count)
            rpm.setValue(existing.rpm)
            yaw.setValue(existing.yaw_deg)

        form.addRow("X (m)", x)
        form.addRow("Y (m)", y)
        form.addRow("Z (m)", z)
        form.addRow("Radius (m)", radius)
        form.addRow("Blade count", blades)
        form.addRow("RPM", rpm)
        form.addRow("Yaw (deg)", yaw)
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        form.addRow(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            return Propeller(
                x=x.value(),
                y=y.value(),
                z=z.value(),
                radius_m=radius.value(),
                blade_count=blades.value(),
                rpm=rpm.value(),
                yaw_deg=yaw.value(),
            )
        return None

    def _add_engine(self) -> None:
        engine = self._prompt_engine()
        if engine:
            self.engines.append(engine)
            self._refresh_powerplant_tables()

    def _edit_engine(self) -> None:
        row = self.engine_table.currentRow()
        if row < 0 or row >= len(self.engines):
            return
        updated = self._prompt_engine(self.engines[row])
        if updated:
            self.engines[row] = updated
            self._refresh_powerplant_tables()

    def _remove_engine(self) -> None:
        row = self.engine_table.currentRow()
        if row < 0 or row >= len(self.engines):
            return
        self.engines.pop(row)
        self._refresh_powerplant_tables()

    def _add_prop(self) -> None:
        prop = self._prompt_prop()
        if prop:
            self.propellers.append(prop)
            self._refresh_powerplant_tables()

    def _edit_prop(self) -> None:
        row = self.prop_table.currentRow()
        if row < 0 or row >= len(self.propellers):
            return
        updated = self._prompt_prop(self.propellers[row])
        if updated:
            self.propellers[row] = updated
            self._refresh_powerplant_tables()

    def _remove_prop(self) -> None:
        row = self.prop_table.currentRow()
        if row < 0 or row >= len(self.propellers):
            return
        self.propellers.pop(row)
        self._refresh_powerplant_tables()

    def _settings_from_ui(self) -> SimulationSettings:
        sweep = None
        if self.freq_mode.currentText() == "Sweep":
            sweep = FrequencySweep(
                start_hz=self.sweep_start.value() * 1e9,
                stop_hz=self.sweep_stop.value() * 1e9,
                steps=self.sweep_steps.value(),
            )
        freq = None if sweep else self.single_freq.value() * 1e9
        radar_profile = self.radar_combo.currentText()
        if radar_profile.startswith("Custom"):
            radar_profile = None
        return SimulationSettings(
            band=self.band_combo.currentText(),
            polarization=self.pol_combo.currentText(),
            max_reflections=self.reflections_spin.value(),
            method=self.method_combo.currentData(),
            engines=list(self.engines),
            propellers=list(self.propellers),
            frequency_hz=freq,
            sweep=sweep,
            azimuth_start=self.az_start.value(),
            azimuth_stop=self.az_stop.value(),
            azimuth_step=self.az_step.value(),
            elevation_start=self.el_start.value(),
            elevation_stop=self.el_stop.value(),
            elevation_step=self.el_step.value(),
            target_speed_mps=self.speed_spin.value(),
            radar_profile=radar_profile,
        )

    def _run_simulation(self) -> None:
        if self.mesh is None:
            QtWidgets.QMessageBox.warning(
                self, "No mesh", "Please load a 3D model first."
            )
            return
        settings = self._settings_from_ui()
        material = self.material_db.get(self.material_combo.currentText())
        self.status_label.setText("Running simulation...")
        self.progress.setValue(0)
        self.worker = SimulationWorker(self.engine, self.mesh, material, settings)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.finished.connect(self._on_simulation_finished)
        self.worker.failed.connect(self._on_simulation_failed)
        self.worker.start()

    def _stop_simulation(self) -> None:
        self.engine.request_stop()
        self.status_label.setText("Stopping...")

    def _on_simulation_failed(self, message: str) -> None:
        QtWidgets.QMessageBox.critical(self, "Simulation failed", message)
        self.status_label.setText("Failed")
        # ------------------------------------------------------------------
    def _precompute_plot_cache(self) -> None:
        """Precompute grids and RCS arrays so UI plots are fast and non-blocking."""

        if self.result is None:
            self._az_grid = None
            self._el_grid = None
            self._az_deg_grid = None
            self._el_deg_grid = None
            self._rcs_lin = None
            self._rcs_norm = None
            self._rcs_radius = None
            return

        # Angle grids
        az_deg = self.result.azimuth_deg
        el_deg = self.result.elevation_deg

        az_rad = np.radians(az_deg)
        el_rad = np.radians(el_deg)

        self._az_grid, self._el_grid = np.meshgrid(az_rad, el_rad)
        self._az_deg_grid, self._el_deg_grid = np.meshgrid(az_deg, el_deg)

        # RCS in linear domain (σ in m^2), shape (F, E, A)
        rcs_db = self.result.rcs_dbsm
        lin = 10.0 ** (rcs_db / 10.0)
        lin = np.maximum(lin, 1e-12)

        # Normalize per frequency (so 3D & heatmap haben 0–1 Skala intern)
        max_per_freq = np.nanmax(lin, axis=(1, 2), keepdims=True)
        max_per_freq[max_per_freq <= 0.0] = 1.0

        self._rcs_lin = lin
        self._rcs_norm = lin / max_per_freq
        self._rcs_radius = np.cbrt(self._rcs_norm)  # compressed dynamic range for 3D

    def _on_simulation_finished(self, result: SimulationResult) -> None:
        self.result = result
        self.status_label.setText("Simulation complete")
        self.progress.setValue(100)

        # >>> NEU: Plot-Cache vorberechnen
        self._precompute_plot_cache()
        # <<<

        self._populate_frequency_selector(result.frequencies_hz)
        self._update_polar_plot()
        self._update_rcs_plot()
        self._update_heatmap_plot()
        self._draw_mesh_preview()

    def _on_exit(self) -> None:
        """Slot wrapper so connect() sees a void-returning callable."""
        self.close()

    # ------------------------------------------------------------------
    def _draw_mesh_preview(self) -> None:
        self.model_canvas.clear()
        ax = self.model_canvas.figure.add_subplot(111, projection="3d")
        if self.mesh is None:
            self.model_canvas.draw_idle()
            return
        mesh = self.mesh
        ax.add_collection3d(  # type: ignore[attr-defined]
            Poly3DCollection(
                mesh.vertices[mesh.faces],
                facecolor="#6baed6",
                edgecolor="k",
                alpha=0.4,
            )
        )
        bounds = mesh.bounds
        max_range = (bounds[1] - bounds[0]).max()
        mid = (bounds[1] + bounds[0]) / 2
        ax.set_xlim(mid[0] - max_range / 2, mid[0] + max_range / 2)
        ax.set_ylim(mid[1] - max_range / 2, mid[1] + max_range / 2)
        ax.set_zlim(mid[2] - max_range / 2, mid[2] + max_range / 2)  # type: ignore[attr-defined]
        ax.set_title("Model preview")
        self.model_canvas.draw_idle()

    def _update_polar_plot(self) -> None:
        if self.result is None:
            return
        self.polar_canvas.clear()
        ax = self.polar_canvas.figure.add_subplot(111, polar=True)
        az, rcs = self.result.slice_for_elevation(self.elevation_spin.value())
        for idx, freq in enumerate(self.result.frequencies_hz):
            values = rcs[idx]
            if self.scale_mode.currentText() == "Linear":
                values = 10 ** (values / 10)
            ax.plot(np.radians(az), values, label=f"{freq/1e9:.2f} GHz")
        ax.set_theta_zero_location("N")  # type: ignore[attr-defined]
        ax.set_theta_direction(-1)  # type: ignore[attr-defined]
        ax.legend()
        ax.set_title(
            f"Polar plot ({self.result.band}-band, {self.result.polarization})"
        )
        self.polar_canvas.draw_idle()

    def _populate_frequency_selector(self, freqs: np.ndarray) -> None:
        self.freq_selector.blockSignals(True)
        self.freq_selector.clear()
        for freq in freqs:
            self.freq_selector.addItem(f"{freq/1e9:.2f} GHz")
        self.freq_selector.setEnabled(len(freqs) > 1)
        self.freq_selector.setCurrentIndex(0)
        self.freq_selector.blockSignals(False)

        self.heatmap_freq_selector.blockSignals(True)
        self.heatmap_freq_selector.clear()
        for freq in freqs:
            self.heatmap_freq_selector.addItem(f"{freq/1e9:.2f} GHz")
        self.heatmap_freq_selector.setEnabled(len(freqs) > 1)
        self.heatmap_freq_selector.setCurrentIndex(0)
        self.heatmap_freq_selector.blockSignals(False)
    class MainWindow(QtWidgets.QMainWindow):
        def __init__(self) -> None:
            super().__init__()
        ...
    
    # ... andere Methoden ...

    def _update_heatmap_plot(self) -> None:
        # dein Heatmap-Code
        ...

    def _update_rcs_plot(self) -> None:
        if self.result is None:
            return
        if self._rcs_radius is None or self._az_grid is None or self._el_grid is None:
            return

        self.rcs3d_canvas.clear()
        ax = self.rcs3d_canvas.figure.add_subplot(111, projection="3d")

        freq_idx = self.freq_selector.currentIndex()
        freq_idx = max(0, min(freq_idx, self._rcs_radius.shape[0] - 1))

        # Full dB array for selected frequency (unclipped)
        rcs_db_full = self.result.rcs_dbsm[freq_idx]

        scale_mode = self.rcs3d_scale_mode.currentText()

        # --- Choose radius / color mapping depending on mode ---
        if scale_mode == "dB (radius & color)":
            # dB clipping
            rcs_db = np.clip(rcs_db_full, self.clip_min.value(), self.clip_max.value())
            r_lin = 10.0 ** (rcs_db / 10.0)
            r_lin = np.maximum(r_lin, 1e-12)
            r_norm = r_lin / (np.nanmax(r_lin) + 1e-12)
            radius = np.cbrt(r_norm)

            face_values_for_color = rcs_db
            color_label = "RCS (dBsm)"

        elif scale_mode == "Linear (radius & color)":
            # Komplett linear, direkt aus Cache
            r_norm = self._rcs_norm[freq_idx]
            radius = self._rcs_radius[freq_idx]

            face_values_for_color = r_norm
            color_label = "RCS (linear, normalized)"

        elif scale_mode == "Linear (fixed radius, color only)":
            # Einheitssphäre, Farbe = linear norm
            r_norm = self._rcs_norm[freq_idx]
            radius = np.ones_like(r_norm)

            face_values_for_color = r_norm
            color_label = "RCS (linear, normalized)"

        else:
            # Fallback: wie früher – dB basierter Radius, dB Farben
            rcs_db = np.clip(rcs_db_full, self.clip_min.value(), self.clip_max.value())
            r_lin = 10.0 ** (rcs_db / 10.0)
            r_lin = np.maximum(r_lin, 1e-12)
            r_norm = r_lin / (np.nanmax(r_lin) + 1e-12)
            radius = np.cbrt(r_norm)

            face_values_for_color = rcs_db
            color_label = "RCS (dBsm)"

        # Cartesian coordinates from spherical angles + radius field
        x = radius * np.cos(self._el_grid) * np.cos(self._az_grid)
        y = radius * np.cos(self._el_grid) * np.sin(self._az_grid)
        z = radius * np.sin(self._el_grid)

        # Normalize colors 0–1 for colormap
        v_min = np.nanmin(face_values_for_color)
        v_max = np.nanmax(face_values_for_color)
        if v_max - v_min < 1e-12:
            norm_vals = np.zeros_like(face_values_for_color)
        else:
            norm_vals = (face_values_for_color - v_min) / (v_max - v_min)

        cmap = plt.cm.get_cmap("viridis")
        facecolors = cmap(norm_vals)

        ax.plot_surface(
            x,
            y,
            z,
            facecolors=facecolors,
            rstride=1,
            cstride=1,
            linewidth=0.0,
            antialiased=True,
            alpha=0.9,
        )

        mappable = plt.cm.ScalarMappable(cmap=cmap)
        mappable.set_array(face_values_for_color)
        self.rcs3d_canvas.figure.colorbar(
            mappable,
            ax=ax,
            shrink=0.5,
            aspect=10,
            label=color_label,
        )

        title = f"3D RCS at {self.result.frequencies_hz[freq_idx]/1e9:.2f} GHz"
        if self.result.radar_profile:
            title += f" – {self.result.radar_profile}"
        if self.result.target_speed_mps:
            title += f" @ {self.result.target_speed_mps:.0f} m/s"
        ax.set_title(title)
        ax.set_box_aspect((1, 1, 1))
        self.rcs3d_canvas.draw_idle()


    def _update_heatmap_plot(self) -> None:
        if self.result is None:
            return
        if self._az_deg_grid is None or self._el_deg_grid is None:
            return

        self.heatmap_canvas.clear()
        ax = self.heatmap_canvas.figure.add_subplot(111)

        freq_idx = self.heatmap_freq_selector.currentIndex()
        freq_idx = max(0, min(freq_idx, self.result.frequencies_hz.shape[0] - 1))

        rcs_db = self.result.rcs_dbsm[freq_idx].copy()
        rcs_db = np.clip(rcs_db, self.heat_clip_min.value(), self.heat_clip_max.value())

        pcm = ax.pcolormesh(
            self._az_deg_grid,
            self._el_deg_grid,
            rcs_db,
            shading="auto",
            cmap="inferno",
        )
        self.heatmap_canvas.figure.colorbar(pcm, ax=ax, label="RCS (dBsm)")

        ax.set_xlabel("Azimuth (deg)")
        ax.set_ylabel("Elevation (deg)")

        title = f"RCS heatmap at {self.result.frequencies_hz[freq_idx]/1e9:.2f} GHz"
        if self.result.radar_profile:
            title += f" – {self.result.radar_profile}"
        ax.set_title(title)

        self.heatmap_canvas.draw_idle()


    # ------------------------------------------------------------------
    def _refresh_templates(self) -> None:
        self.templates_table.setRowCount(0)
        for path in self.template_lib.list_templates():
            template = self.template_lib.load_template(path)
            row = self.templates_table.rowCount()
            self.templates_table.insertRow(row)
            self.templates_table.setItem(
                row, 0, QtWidgets.QTableWidgetItem(template.name)
            )
            self.templates_table.setItem(
                row, 1, QtWidgets.QTableWidgetItem(template.target_class)
            )
            self.templates_table.setItem(
                row, 2, QtWidgets.QTableWidgetItem(template.band)
            )
            self.templates_table.setItem(
                row, 3, QtWidgets.QTableWidgetItem("-")
            )

    def _create_template(self) -> None:
        if self.result is None:
            QtWidgets.QMessageBox.information(
                self, "No result", "Run a simulation first."
            )
            return
        name, ok = QtWidgets.QInputDialog.getText(self, "Template name", "Name")
        if not ok or not name:
            return
        cls, ok = QtWidgets.QInputDialog.getText(self, "Target class", "Class")
        if not ok or not cls:
            return
        template = self.template_lib.create_from_result(
            self.result, name=name, target_class=cls
        )
        path = self.template_lib.save_template(template)
        QtWidgets.QMessageBox.information(self, "Template saved", f"Saved to {path}")
        self._refresh_templates()

    def _match_templates(self) -> None:
        if self.result is None:
            QtWidgets.QMessageBox.warning(
                self, "No result", "Run a simulation first."
            )
            return
        matches = self.template_lib.match(self.result)
        self.templates_table.setRowCount(0)
        for template, score in matches:
            row = self.templates_table.rowCount()
            self.templates_table.insertRow(row)
            self.templates_table.setItem(
                row, 0, QtWidgets.QTableWidgetItem(template.name)
            )
            self.templates_table.setItem(
                row, 1, QtWidgets.QTableWidgetItem(template.target_class)
            )
            self.templates_table.setItem(
                row, 2, QtWidgets.QTableWidgetItem(template.band)
            )
            self.templates_table.setItem(
                row, 3, QtWidgets.QTableWidgetItem(f"{score:.2f}")
            )

    # ------------------------------------------------------------------
    def _save_project(self) -> None:
        path_str, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save project", str(Path.home()), "Project (*.json)"
        )
        if not path_str:
            return
        state = ProjectState(
            mesh_path=str(self.mesh_path) if self.mesh_path else None,
            settings=self._settings_from_ui(),
            material_name=self.material_combo.currentText(),
        )
        save_project(path_str, state)

    def _load_project(self) -> None:
        path_str, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Load project", str(Path.home()), "Project (*.json)"
        )
        if not path_str:
            return
        state = load_project(path_str)
        self.band_combo.setCurrentText(state.settings.band)
        self.pol_combo.setCurrentText(state.settings.polarization)
        self.reflections_spin.setValue(state.settings.max_reflections)
        idx = self.method_combo.findData(state.settings.method or "ray")
        if idx >= 0:
            self.method_combo.setCurrentIndex(idx)
        if state.settings.sweep:
            self.freq_mode.setCurrentText("Sweep")
            self.sweep_start.setValue(state.settings.sweep.start_hz / 1e9)
            self.sweep_stop.setValue(state.settings.sweep.stop_hz / 1e9)
            self.sweep_steps.setValue(state.settings.sweep.steps)
        else:
            self.freq_mode.setCurrentText("Single")
            if state.settings.frequency_hz:
                self.single_freq.setValue(state.settings.frequency_hz / 1e9)
        self.speed_spin.setValue(state.settings.target_speed_mps)
        profiles: Mapping[str, RadarProfile] = cast(
            Mapping[str, RadarProfile], RADAR_PROFILES
        )
        if state.settings.radar_profile and state.settings.radar_profile in profiles:
            self.radar_combo.setCurrentText(state.settings.radar_profile)
        else:
            self.radar_combo.setCurrentText("Custom (manual)")
        self.az_start.setValue(state.settings.azimuth_start)
        self.az_stop.setValue(state.settings.azimuth_stop)
        self.az_step.setValue(state.settings.azimuth_step)
        self.el_start.setValue(state.settings.elevation_start)
        self.el_stop.setValue(state.settings.elevation_stop)
        self.el_step.setValue(state.settings.elevation_step)
        self.engines = list(state.settings.engines)
        self.propellers = list(state.settings.propellers)
        self._refresh_powerplant_tables()
        if state.material_name in self.material_db.materials:
            self.material_combo.setCurrentText(state.material_name)
        if state.mesh_path and Path(state.mesh_path).exists():
            self.mesh_path = Path(state.mesh_path)
            self._open_mesh_from_path(self.mesh_path)

    def _open_mesh_from_path(self, path: Path) -> None:
        try:
            mesh_obj = trimesh.load_mesh(path, force="mesh")

            mesh_t: trimesh.Trimesh
            if isinstance(mesh_obj, trimesh.Scene):
                parts = [
                    g
                    for g in mesh_obj.geometry.values()
                    if isinstance(g, trimesh.Trimesh)
                ]
                if not parts:
                    raise ValueError("Scene contains no Trimesh geometry.")
                mesh_t = trimesh.util.concatenate(parts)  # type: ignore[arg-type]
            elif isinstance(mesh_obj, trimesh.Trimesh):
                mesh_t = mesh_obj
            else:
                raise ValueError("Unsupported mesh type loaded.")

            mesh_t.remove_unreferenced_vertices()
            mesh_t.update_faces(mesh_t.nondegenerate_faces())
            self.mesh = mesh_t
            self.file_label.setText(path.name)
            self._draw_mesh_preview()
        except Exception as exc:  # noqa: BLE001
            QtWidgets.QMessageBox.critical(
                self,
                "Error loading mesh",
                f"Failed to load mesh from project:\n{exc}",
            )

    def _export_csv(self) -> None:
        if self.result is None:
            QtWidgets.QMessageBox.warning(
                self, "No result", "Run a simulation first."
            )
            return
        path_str, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export CSV", str(Path.home()), "CSV (*.csv)"
        )
        if not path_str:
            return
        path = Path(path_str)
        with path.open("w", encoding="utf-8") as fh:
            fh.write(
                "band,frequency_hz,azimuth_deg,elevation_deg,polarization,rcs_linear,rcs_db\n"
            )
            for fi, freq in enumerate(self.result.frequencies_hz):
                for ei, el in enumerate(self.result.elevation_deg):
                    for ai, az in enumerate(self.result.azimuth_deg):
                        rcs_db = self.result.rcs_dbsm[fi, ei, ai]
                        rcs_lin = 10 ** (rcs_db / 10)
                        fh.write(
                            f"{self.result.band},{freq},{az},{el},"
                            f"{self.result.polarization},{rcs_lin},{rcs_db}\n"
                        )

    def _export_plots(self) -> None:
        if self.result is None:
            QtWidgets.QMessageBox.warning(
                self, "No result", "Run a simulation first."
            )
            return
        path_str, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export plots", str(Path.home()), "PNG (*.png)"
        )
        if not path_str:
            return
        base = Path(path_str)
        self.polar_canvas.figure.savefig(base)
        rcs_path = base.with_name(base.stem + "_3d.png")
        self.rcs3d_canvas.figure.savefig(rcs_path)
        heatmap_path = base.with_name(base.stem + "_heatmap.png")
        self.heatmap_canvas.figure.savefig(heatmap_path)

    def _edit_materials(self) -> None:
        dialog = MaterialsDialog(self.material_db, parent=self)
        if dialog.exec_():
            self.material_combo.clear()
            self.material_combo.addItems(self.material_db.names())


def run_app() -> None:
    app = QtWidgets.QApplication([])
    win = MainWindow()
    win.show()
    win._refresh_templates()
    app.exec_()


class MaterialsDialog(QtWidgets.QDialog):
    def __init__(
        self, db: MaterialDatabase, parent: Optional[QtWidgets.QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Materials")
        layout = QtWidgets.QVBoxLayout(self)

        # Name, eps_real, eps_imag, sigma, R, R_H, R_V, R_HV, R_VH
        self.table = QtWidgets.QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels(
            ["Name", "ε'", "ε''", "σ", "R", "R_H", "R_V", "R_HV", "R_VH"]
        )
        layout.addWidget(self.table)
        self._reload()

        btns = QtWidgets.QHBoxLayout()
        add_btn = QtWidgets.QPushButton("Add")
        edit_btn = QtWidgets.QPushButton("Edit")
        delete_btn = QtWidgets.QPushButton("Delete")
        btns.addWidget(add_btn)
        btns.addWidget(edit_btn)
        btns.addWidget(delete_btn)
        btns.addStretch(1)
        layout.addLayout(btns)

        add_btn.clicked.connect(self._add)
        edit_btn.clicked.connect(self._edit)
        delete_btn.clicked.connect(self._delete)

    def _reload(self) -> None:
        self.table.setRowCount(0)
        for mat in self.db.as_list():
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(mat.name))
            self.table.setItem(
                row, 1, QtWidgets.QTableWidgetItem(f"{mat.epsilon_real:.2f}")
            )
            self.table.setItem(
                row, 2, QtWidgets.QTableWidgetItem(f"{mat.epsilon_imag:.2f}")
            )
            self.table.setItem(
                row, 3, QtWidgets.QTableWidgetItem(f"{mat.conductivity:.2e}")
            )
            self.table.setItem(
                row, 4, QtWidgets.QTableWidgetItem(f"{mat.reflectivity:.2f}")
            )
            # Optional polarimetric fields (show blanks if None)
            self.table.setItem(
                row,
                5,
                QtWidgets.QTableWidgetItem(
                    "" if mat.reflectivity_h is None else f"{mat.reflectivity_h:.2f}"
                ),
            )
            self.table.setItem(
                row,
                6,
                QtWidgets.QTableWidgetItem(
                    "" if mat.reflectivity_v is None else f"{mat.reflectivity_v:.2f}"
                ),
            )
            self.table.setItem(
                row,
                7,
                QtWidgets.QTableWidgetItem(
                    "" if mat.reflectivity_hv is None else f"{mat.reflectivity_hv:.2f}"
                ),
            )
            self.table.setItem(
                row,
                8,
                QtWidgets.QTableWidgetItem(
                    "" if mat.reflectivity_vh is None else f"{mat.reflectivity_vh:.2f}"
                ),
            )

    def _add(self) -> None:
        material = self._prompt_material()
        if material:
            self.db.add_material(material)
            self._reload()

    def _edit(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            return
        item = self.table.item(row, 0)
        if item is None:
            return
        name = item.text()
        material = self._prompt_material(name)
        if material:
            # update_material merges dict into existing entry
            self.db.update_material(name, **material.as_dict())
            self._reload()

    def _delete(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            return
        item = self.table.item(row, 0)
        if item is None:
            return
        name = item.text()
        self.db.delete_material(name)
        self._reload()

    def _prompt_material(self, existing: Optional[str] = None) -> Optional[Material]:
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Material")
        form = QtWidgets.QFormLayout(dialog)
        name_edit = QtWidgets.QLineEdit(existing or "")
        eps_r = QtWidgets.QDoubleSpinBox()
        eps_r.setRange(0, 100)
        eps_i = QtWidgets.QDoubleSpinBox()
        eps_i.setRange(0, 100)
        sigma = QtWidgets.QDoubleSpinBox()
        sigma.setRange(0, 1e8)
        sigma.setDecimals(3)
        sigma.setSingleStep(1e4)
        refl = QtWidgets.QDoubleSpinBox()
        refl.setRange(0, 1)
        refl.setSingleStep(0.05)

        refl_h = QtWidgets.QDoubleSpinBox()
        refl_h.setRange(0, 1)
        refl_h.setSingleStep(0.05)

        refl_v = QtWidgets.QDoubleSpinBox()
        refl_v.setRange(0, 1)
        refl_v.setSingleStep(0.05)

        refl_hv = QtWidgets.QDoubleSpinBox()
        refl_hv.setRange(0, 1)
        refl_hv.setSingleStep(0.05)

        refl_vh = QtWidgets.QDoubleSpinBox()
        refl_vh.setRange(0, 1)
        refl_vh.setSingleStep(0.05)

        if existing:
            mat = self.db.get(existing)
            eps_r.setValue(mat.epsilon_real)
            eps_i.setValue(mat.epsilon_imag)
            sigma.setValue(mat.conductivity)
            refl.setValue(mat.reflectivity)
            if mat.reflectivity_h is not None:
                refl_h.setValue(mat.reflectivity_h)
            if mat.reflectivity_v is not None:
                refl_v.setValue(mat.reflectivity_v)
            if mat.reflectivity_hv is not None:
                refl_hv.setValue(mat.reflectivity_hv)
            if mat.reflectivity_vh is not None:
                refl_vh.setValue(mat.reflectivity_vh)

        form.addRow("Name", name_edit)
        form.addRow("ε'", eps_r)
        form.addRow("ε''", eps_i)
        form.addRow("σ", sigma)
        form.addRow("R (scalar)", refl)
        form.addRow("R_H", refl_h)
        form.addRow("R_V", refl_v)
        form.addRow("R_HV", refl_hv)
        form.addRow("R_VH", refl_vh)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        form.addRow(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            return Material(
                name=name_edit.text(),
                epsilon_real=eps_r.value(),
                epsilon_imag=eps_i.value(),
                conductivity=sigma.value(),
                reflectivity=refl.value(),
                reflectivity_h=refl_h.value(),
                reflectivity_v=refl_v.value(),
                reflectivity_hh=None,
                reflectivity_vv=None,
                reflectivity_hv=refl_hv.value(),
                reflectivity_vh=refl_vh.value(),
            )
        return None


__all__ = ["run_app", "MainWindow"]
