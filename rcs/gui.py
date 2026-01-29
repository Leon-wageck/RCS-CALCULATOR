"""Tkinter-based GUI for RCS simulation and visualization."""

from __future__ import annotations

import csv
import os
import threading
import traceback
from pathlib import Path
from typing import Optional, Tuple

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np
import tkinter as tk
import trimesh
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from tkinter import filedialog, messagebox, ttk

from .materials import MATERIAL_DB
from .math_utils import rotation_matrix
from .nctr import simulate_nctr_signature
from .physics import build_ray_intersector, robust_freq_sweep, simulate_rcs
from .presets import RADAR_PRESETS


def _homogeneous_rotation(rotation: np.ndarray) -> np.ndarray:
    """Create a 4x4 homogeneous transform from a 3x3 rotation."""
    transform = np.eye(4)
    transform[:3, :3] = rotation
    return transform


class RadarGUI:
    """Encapsulated GUI controller."""

    def __init__(self, master: tk.Tk):
        self.master = master
        master.title("Radar RCS Simulation")
        master.geometry("800x600")
        master.minsize(700, 500)
        master.configure(bg="#222831")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TLabel", background="#222831", foreground="#eeeeee", font=("Segoe UI", 11))
        style.configure("TButton", font=("Segoe UI", 11), padding=6)
        style.configure("TCheckbutton", background="#222831", foreground="#eeeeee", font=("Segoe UI", 11))
        style.configure("TMenubutton", font=("Segoe UI", 11))

        self.main_frame = ttk.Frame(master, padding=20, style="TFrame")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        self.main_frame.columnconfigure(1, weight=1)
        self.main_frame.rowconfigure(tuple(range(13)), weight=1)

        self._build_controls()

        self.mesh: Optional[trimesh.Trimesh] = None
        self.last_rcs: Optional[np.ndarray] = None
        self.last_az: Optional[np.ndarray] = None
        self.last_el: Optional[np.ndarray] = None
        self.last_nctr: Optional[Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]] = None

    # ------------------------------------------------------------------
    # UI construction
    def _build_controls(self) -> None:
        ttk.Label(self.main_frame, text="3D-Modell (STL, OBJ, GLB):").grid(row=0, column=0, sticky="e", pady=4)
        self.file_label = ttk.Label(self.main_frame, text="Keine Datei", style="TLabel")
        self.file_label.grid(row=0, column=1, sticky="ew", pady=4)
        ttk.Button(self.main_frame, text="Laden", command=self.load_file).grid(row=0, column=2, padx=5, pady=4)

        ttk.Label(self.main_frame, text="Material:").grid(row=1, column=0, sticky="e", pady=4)
        self.material_var = tk.StringVar(self.master, value="Aluminium")
        material_menu = ttk.OptionMenu(self.main_frame, self.material_var, "Aluminium", *MATERIAL_DB.keys())
        material_menu.grid(row=1, column=1, sticky="ew", pady=4)

        ttk.Label(self.main_frame, text="Radarprofil:").grid(row=2, column=0, sticky="e", pady=4)
        self.preset_var = tk.StringVar(self.master, value="NATO – X-Band (10 GHz)")
        preset_menu = ttk.OptionMenu(
            self.main_frame,
            self.preset_var,
            "NATO – X-Band (10 GHz)",
            *RADAR_PRESETS.keys(),
            command=self.apply_preset,
        )
        preset_menu.grid(row=2, column=1, sticky="ew", pady=4)

        ttk.Label(self.main_frame, text="Frequenz (MHz):").grid(row=3, column=0, sticky="e", pady=4)
        self.freq_scale = tk.Scale(self.main_frame, from_=100, to=20000, orient=tk.HORIZONTAL, bg="#393e46", fg="#eeeeee", highlightbackground="#222831")
        self.freq_scale.set(10000)
        self.freq_scale.grid(row=3, column=1, sticky="ew", pady=4)

        ttk.Label(self.main_frame, text="Max. Reflexionen:").grid(row=4, column=0, sticky="e", pady=4)
        self.refl_slider = tk.Scale(self.main_frame, from_=1, to=10, orient=tk.HORIZONTAL, bg="#393e46", fg="#eeeeee", highlightbackground="#222831")
        self.refl_slider.set(3)
        self.refl_slider.grid(row=4, column=1, sticky="ew", pady=4)

        ttk.Label(self.main_frame, text="Elevation-Schnitt (°):").grid(row=5, column=0, sticky="e", pady=4)
        self.el_slider = tk.Scale(self.main_frame, from_=-90, to=90, orient=tk.HORIZONTAL, bg="#393e46", fg="#eeeeee", highlightbackground="#222831")
        self.el_slider.set(0)
        self.el_slider.grid(row=5, column=1, sticky="ew", pady=4)

        ttk.Label(self.main_frame, text="Yaw (°):").grid(row=6, column=0, sticky="e", pady=4)
        self.yaw = tk.Scale(self.main_frame, from_=-180, to=180, orient=tk.HORIZONTAL, bg="#393e46", fg="#eeeeee", highlightbackground="#222831")
        self.yaw.set(0)
        self.yaw.grid(row=6, column=1, sticky="ew", pady=4)

        ttk.Label(self.main_frame, text="Pitch (°):").grid(row=7, column=0, sticky="e", pady=4)
        self.pitch = tk.Scale(self.main_frame, from_=-90, to=90, orient=tk.HORIZONTAL, bg="#393e46", fg="#eeeeee", highlightbackground="#222831")
        self.pitch.set(0)
        self.pitch.grid(row=7, column=1, sticky="ew", pady=4)

        ttk.Label(self.main_frame, text="Roll (°):").grid(row=8, column=0, sticky="e", pady=4)
        self.roll = tk.Scale(self.main_frame, from_=-180, to=180, orient=tk.HORIZONTAL, bg="#393e46", fg="#eeeeee", highlightbackground="#222831")
        self.roll.set(0)
        self.roll.grid(row=8, column=1, sticky="ew", pady=4)

        self.show_model = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            self.main_frame, text="Modell anzeigen", variable=self.show_model, style="TCheckbutton"
        ).grid(row=9, column=0, sticky="w", pady=4)

        ttk.Button(self.main_frame, text="NCTR-Vorschau", command=self.preview_nctr).grid(
            row=10, column=0, sticky="ew", pady=4
        )
        ttk.Button(self.main_frame, text="NCTR Export", command=self.export_nctr_signature).grid(
            row=10, column=1, sticky="ew", pady=4
        )

        self.live_mode = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            self.main_frame,
            text="Live Simulation (experimentell)",
            variable=self.live_mode,
            style="TCheckbutton",
            command=self.toggle_live_mode,
        ).grid(row=12, column=0, columnspan=2, sticky="w", pady=4)

        ttk.Button(self.main_frame, text="Simulation starten", command=self.run_simulation).grid(row=13, column=0, columnspan=2, sticky="ew", pady=8)
        ttk.Button(
            self.main_frame,
            text="Frequenz-Sweep",
            command=lambda: robust_freq_sweep(
                self.mesh,
                MATERIAL_DB[self.material_var.get()],
                self.refl_slider.get(),
                lambda func: self.master.after(0, func),
            ),
        ).grid(row=14, column=0, sticky="ew", pady=4)
        ttk.Button(self.main_frame, text="Heatmap exportieren", command=self.export_heatmap).grid(row=14, column=1, sticky="ew", pady=4)

    # ------------------------------------------------------------------
    # Event handlers
    def apply_preset(self, selection: str) -> None:
        if selection in RADAR_PRESETS:
            self.freq_scale.set(RADAR_PRESETS[selection])

    def load_file(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("3D-Dateien", "*.stl *.obj *.glb *.gltf")])
        if not path:
            return
        try:
            mesh = trimesh.load_mesh(path, force="mesh")

            if not isinstance(mesh, trimesh.Trimesh):
                if isinstance(mesh, trimesh.Scene):
                    mesh = trimesh.util.concatenate([g for g in mesh.geometry.values() if isinstance(g, trimesh.Trimesh)])
                else:
                    raise ValueError("Unbekannter Mesh-Typ geladen.")

            mesh.remove_unreferenced_vertices()
            mesh.update_faces(mesh.nondegenerate_faces())

            if len(mesh.faces) > 50000:
                mesh = mesh.simplify_quadratic_decimation(50000)

            mesh.ray = build_ray_intersector(mesh)

            self.mesh = mesh
            self.file_label.config(text=os.path.basename(path))
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Fehler beim Laden", f"Das Modell konnte nicht geladen werden:\n{exc}")
            self.mesh = None
            self.file_label.config(text="Keine Datei")

    def toggle_live_mode(self) -> None:
        callbacks: List[Tuple[tk.Scale, str]] = [
            (self.freq_scale, "<ButtonRelease-1>"),
            (self.refl_slider, "<ButtonRelease-1>"),
            (self.el_slider, "<ButtonRelease-1>"),
            (self.yaw, "<ButtonRelease-1>"),
            (self.pitch, "<ButtonRelease-1>"),
            (self.roll, "<ButtonRelease-1>"),
        ]
        if self.live_mode.get():
            for widget, event in callbacks:
                widget.bind(event, self.live_update)
            self.material_var.trace_add("write", lambda *_: self.live_update())
            self.preset_var.trace_add("write", lambda *_: self.live_update())
        else:
            for widget, event in callbacks:
                widget.unbind(event)

    def live_update(self, event=None) -> None:  # noqa: ANN001
        if self.mesh is None or not self.live_mode.get():
            return

        def worker() -> None:
            try:
                material = MATERIAL_DB[self.material_var.get()]
                freq = self.freq_scale.get() / 1000
                refl = self.refl_slider.get()
                rotated = self._rotated_mesh()
                az, el, rcs = simulate_rcs(rotated, material, refl, freq, max_workers=os.cpu_count())
                self.last_rcs = rcs
                self.last_az = az
                self.last_el = el
                self.master.after(0, self.plot_2d)
                self.master.after(0, lambda: self.plot_3d(rotated))
                export_dir = Path.home() / "Documents" / "RCS_Live_Exports"
                export_dir.mkdir(parents=True, exist_ok=True)
                self.export_csv(export_dir, live=True)
                self.export_heatmap(export_dir, live=True)
            except Exception:
                traceback.print_exc()

        threading.Thread(target=worker, daemon=True).start()

    def run_simulation(self) -> None:
        if self.mesh is None:
            messagebox.showwarning("Kein Modell", "Kein Modell geladen.")
            return
        try:
            material = MATERIAL_DB[self.material_var.get()]
            freq = self.freq_scale.get() / 1000
            refl = self.refl_slider.get()
            rotated = self._rotated_mesh()
            az, el, rcs = simulate_rcs(rotated, material, refl, freq, max_workers=os.cpu_count())
            self.last_rcs = rcs
            self.last_az = az
            self.last_el = el
            self.plot_2d()
            self.plot_3d(rotated)
            self.export_csv()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Fehler bei Simulation", f"Fehler während der Simulation:\n{exc}")

    def preview_nctr(self) -> None:
        if self.mesh is None:
            messagebox.showwarning("Kein Modell", "Kein Modell geladen.")
            return

        try:
            material = MATERIAL_DB[self.material_var.get()]
            freq = self.freq_scale.get() / 1000
            rotated = self._rotated_mesh()
            prf = 1800.0
            times, doppler_freqs, spec_db, envelope = simulate_nctr_signature(
                rotated,
                material,
                freq,
                yaw=self.yaw.get(),
                pitch=self.pitch.get(),
                roll=self.roll.get(),
                prf=prf,
            )
            self.last_nctr = (times, doppler_freqs, spec_db, envelope)

            fig, (ax_env, ax_spec) = plt.subplots(2, 1, figsize=(8, 6))
            ax_env.plot(np.arange(len(envelope)) / prf, envelope)
            ax_env.set_title("Puls-Hüllkurve (dB)")
            ax_env.set_xlabel("Zeit (s)")
            ax_env.set_ylabel("Amplitude")
            ax_env.grid(True, alpha=0.3)

            t_grid, f_grid = np.meshgrid(times, doppler_freqs)
            pcm = ax_spec.pcolormesh(t_grid, f_grid, spec_db, shading="auto", cmap="magma")
            ax_spec.set_title("NCTR Mikrodoppler-Spektrogramm")
            ax_spec.set_xlabel("Zeit (s)")
            ax_spec.set_ylabel("Dopplerfrequenz (Hz)")
            fig.colorbar(pcm, ax=ax_spec, label="Leistung (dB)")
            fig.tight_layout()
            plt.show()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("NCTR-Fehler", f"Die NCTR-Simulation ist fehlgeschlagen:\n{exc}")

    # ------------------------------------------------------------------
    # Visualization helpers
    def _rotated_mesh(self) -> trimesh.Trimesh:
        rotation = rotation_matrix(self.yaw.get(), self.pitch.get(), self.roll.get())
        rotated = self.mesh.copy()
        rotated.apply_transform(_homogeneous_rotation(rotation))
        rotated.ray = build_ray_intersector(rotated)
        return rotated

    def plot_2d(self) -> None:
        if self.last_rcs is None:
            return
        idx = int(np.argmin(np.abs(self.last_el - self.el_slider.get())))
        fig = plt.figure()
        ax = fig.add_subplot(111, polar=True)
        ax.plot(np.radians(self.last_az), self.last_rcs[idx], label=f"Elevation {self.last_el[idx]}°")
        ax.set_theta_zero_location("N")
        ax.set_theta_direction(-1)
        ax.set_title("2D Radar Cross Section")
        ax.legend()
        try:
            img = mpimg.imread("aircraft_shadow.png")
            axins = fig.add_axes([0.3, 0.3, 0.4, 0.4], polar=True, zorder=-1)
            axins.imshow(img, extent=[0, 2 * np.pi, 0, np.max(self.last_rcs)], aspect="auto", alpha=0.3)
            axins.axis("off")
        except Exception:
            pass
        plt.show()

    def plot_3d(self, mesh: trimesh.Trimesh) -> None:
        if self.last_rcs is None:
            return
        az_rad = np.radians(self.last_az)
        el_rad = np.radians(self.last_el)
        az_grid, el_grid = np.meshgrid(az_rad, el_rad)
        r_raw = 10 ** (self.last_rcs / 10.0)
        model_radius = np.linalg.norm(mesh.bounding_box.extents) / 2
        r = r_raw / np.max(r_raw) * model_radius * 4
        x = r * np.cos(el_grid) * np.cos(az_grid)
        y = r * np.cos(el_grid) * np.sin(az_grid)
        z = r * np.sin(el_grid)
        fig = plt.figure()
        ax = fig.add_subplot(111, projection="3d")
        surf = ax.plot_surface(
            x,
            y,
            z,
            facecolors=plt.cm.viridis((r_raw - r_raw.min()) / (r_raw.max() - r_raw.min())),
            rstride=1,
            cstride=1,
            alpha=0.5,
        )
        mappable = plt.cm.ScalarMappable(cmap=plt.cm.viridis)
        mappable.set_array(r_raw)
        fig.colorbar(mappable, ax=ax, shrink=0.5, aspect=10, label="RCS (linear)")
        if self.show_model.get():
            ax.add_collection3d(Poly3DCollection(mesh.vertices[mesh.faces], facecolor="gray", edgecolor="k", alpha=0.2))
        ax.set_box_aspect([1, 1, 1])
        ax.set_title("3D RCS Plot")
        plt.show()

    # ------------------------------------------------------------------
    # Export helpers
    def export_csv(self, export_dir: Optional[Path] = None, live: bool = False) -> None:
        if self.last_rcs is None:
            return
        if export_dir is None and not live:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".csv", filetypes=[("CSV files", "*.csv")], title="Speichern unter..."
            )
            if not file_path:
                return
        elif export_dir is not None:
            file_path = os.path.join(export_dir, "rcs_export.csv")
        else:
            file_path = "rcs_export.csv"
        try:
            with open(file_path, mode="w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Azimuth (°)", "Elevation (°)", "RCS (dBsm)"])
                for i, el_val in enumerate(self.last_el):
                    for j, az_val in enumerate(self.last_az):
                        writer.writerow([az_val, el_val, self.last_rcs[i, j]])
            if not live:
                messagebox.showinfo("Export erfolgreich", f"RCS-Daten wurden als {os.path.basename(file_path)} gespeichert.")
        except Exception as exc:  # noqa: BLE001
            if not live:
                messagebox.showerror("Fehler beim Export", f"Fehler beim Exportieren der CSV:\n{exc}")

    def export_heatmap(self, export_dir: Optional[Path] = None, live: bool = False) -> None:
        if self.last_rcs is None:
            return

        def worker() -> None:
            try:
                if export_dir is None and not live:
                    file_path = filedialog.asksaveasfilename(
                        defaultextension=".png", filetypes=[("PNG files", "*.png")], title="Speichern unter..."
                    )
                    if not file_path:
                        return
                elif export_dir is not None:
                    file_path = os.path.join(export_dir, "rcs_heatmap.png")
                else:
                    file_path = "rcs_heatmap.png"
                extent = [
                    float(self.last_az[0]),
                    float(self.last_az[-1]),
                    float(self.last_el[0]),
                    float(self.last_el[-1]),
                ]
                plt.imshow(self.last_rcs, extent=extent, aspect="auto", cmap="hot", origin="lower")
                plt.colorbar(label="RCS (dBsm)")
                plt.title("RCS Heatmap")
                plt.xlabel("Azimuth")
                plt.ylabel("Elevation")
                plt.savefig(file_path)
                plt.close()
                if not live:
                    self.master.after(
                        0, lambda: messagebox.showinfo("Export erfolgreich", f"Heatmap wurde als {os.path.basename(file_path)} gespeichert.")
                    )
            except Exception as exc:  # noqa: BLE001
                if not live:
                    self.master.after(0, lambda e=exc: messagebox.showerror("Fehler beim Export", f"Fehler beim Exportieren der Heatmap:\n{e}"))

        threading.Thread(target=worker, daemon=True).start()

    def export_nctr_signature(self) -> None:
        if self.last_nctr is None:
            messagebox.showwarning("Kein NCTR", "Bitte zuerst eine NCTR-Vorschau berechnen.")
            return

        times, doppler_freqs, spec_db, envelope = self.last_nctr
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV files", "*.csv")], title="NCTR-Signatur speichern"
        )
        if not file_path:
            return

        try:
            with open(file_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["time_s"] + [f"doppler_{freq:.1f}Hz" for freq in doppler_freqs])
                for t_idx, t_val in enumerate(times):
                    writer.writerow([t_val, *spec_db[:, t_idx]])

                writer.writerow([])
                writer.writerow(["pulse_envelope_db"])
                writer.writerow([f"{val:.4f}" for val in envelope])

            messagebox.showinfo("Export erfolgreich", f"NCTR-Signatur gespeichert als {os.path.basename(file_path)}")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Exportfehler", f"NCTR-Daten konnten nicht gespeichert werden:\n{exc}")


def run_app() -> None:
    root = tk.Tk()
    RadarGUI(root)
    root.mainloop()


__all__ = ["RadarGUI", "run_app"]
