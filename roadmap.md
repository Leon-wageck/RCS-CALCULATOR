

# RCS-CALCULATOR ROADMAP

## Target: Professional Conceptual RCS / Signature Analysis Tool with NCTR Capability

## Product Goal

Build a **professional conceptual RCS and radar-signature analysis tool** that is:

* accurate enough for **high-frequency RCS studies**
* suitable for **NCTR / micro-Doppler research**
* deterministic and reproducible
* visually aligned with engineering standards
* honest about model assumptions and limits
* strong for comparative analysis, research, and development

## Non-Goal

This tool is **not** a full-wave EM solver and does **not** aim to replace CST / FEKO / HFSS for all cases.

The tool should instead become a strong **high-frequency radar signature and NCTR simulation platform** based on:

* Facet Physical Optics
* heuristic diffraction
* SBR / ray-based methods
* coherent return synthesis
* moving-part / micro-Doppler modelling

---

# HIGH-LEVEL DEVELOPMENT PHASES

1. Core Stabilization
2. Solver Accuracy & Model Honesty
3. Professional Visualization
4. Contribution & Interpretability
5. Validation & Trust
6. NCTR / Time-Domain Simulation
7. Comparative Analysis & Workflow Polish

---

# MILESTONE 1 — CORE STABILIZATION

## Goal

Make the new stack the only trusted stack, clean up architecture, and ensure deterministic behavior.

## Issues

### 1. Define official application stack

**Problem:** Old and new stacks coexist.
**Goal:** One official GUI path and one official simulation backend.
**Acceptance Criteria:**

* official startup path documented
* legacy path marked deprecated or archived
* no ambiguity about which frontend/backend is current

### 2. Clean and normalize `main_window.py`

**Problem:** File structure is messy / duplicated / hard to trust.
**Goal:** Make GUI code readable and maintainable.
**Acceptance Criteria:**

* duplicate methods removed
* broken/placeholder code removed
* GUI file split if needed

### 3. Separate GUI responsibilities

**Problem:** Main window likely owns too much.
**Goal:** Split UI, plotting, worker logic, and data flow.
**Acceptance Criteria:**

* plotting logic isolated
* worker/thread logic isolated
* UI state separated from simulation execution

### 4. Remove hidden randomness from simulation outputs

**Problem:** Results must be reproducible.
**Goal:** Same input must produce same output.
**Acceptance Criteria:**

* no random noise in solver output by default
* synthetic noise, if any, is explicit and optional

### 5. Add result completeness and cancellation state

**Problem:** Partial results can look valid.
**Goal:** Make cancellation explicit.
**Acceptance Criteria:**

* `SimulationResult` tracks completed/cancelled/partial
* GUI handles partial results safely

### 6. Improve progress reporting

**Problem:** Progress is coarse and frequency-only.
**Goal:** Better simulation progress feedback.
**Acceptance Criteria:**

* progress updates across frequency and elevation/time
* no 0→100 jump for single-frequency runs

### 7. Remove or quarantine legacy solver path

**Problem:** Old solver code causes confusion and future regressions.
**Goal:** Keep only one supported stack.
**Acceptance Criteria:**

* legacy solver moved to archive or deprecated module
* GUI does not call legacy path

### 8. Add metadata-rich result objects

**Problem:** Results are not self-describing enough.
**Goal:** Make runs reproducible and exportable.
**Acceptance Criteria:**

* result contains solver mode, mesh, material, frequency, timestamp, version
* exports preserve metadata

---

# MILESTONE 2 — SOLVER ACCURACY & MODEL HONESTY

## Goal

Make the solver clearer, more consistent, and more technically honest.

## Issues

### 9. Document solver mode meanings

**Problem:** Fast / Realistic / SBR are unclear.
**Goal:** Explain intended use and limitations.
**Acceptance Criteria:**

* each mode has UI description
* each mode has documented assumptions

### 10. Audit material model vs actual solver use

**Problem:** Material data model implies more physics than used.
**Goal:** Align UI/data with implementation.
**Acceptance Criteria:**

* every material field is either used or documented
* no misleading unused parameters in main workflow

### 11. Fix or relabel polarization handling

**Problem:** Polarization currently collapses to scalar reflectivity.
**Goal:** Be honest and consistent.
**Acceptance Criteria:**

* either proper polarization handling added
* or relabeled as effective reflectivity weighting

### 12. Improve SBR monostatic return logic

**Problem:** Current return detection is heuristic.
**Goal:** Make ray return evaluation more consistent.
**Acceptance Criteria:**

* explicit return alignment model
* receiver acceptance cone or equivalent logic
* documented behavior

### 13. Expose ray bundle density as a setting or preset

**Problem:** SBR quality is fixed and hidden.
**Goal:** Make quality/performance tunable.
**Acceptance Criteria:**

* preview/standard/high-quality ray bundle settings
* configurable through settings or quality presets

### 14. Optimize diffraction candidate handling

**Problem:** Corner diffraction likely scales poorly.
**Goal:** Reduce combinatorial cost.
**Acceptance Criteria:**

* corner candidate generation optimized
* performance improved on dense meshes

### 15. Review engine/propeller signature model

**Problem:** Current model is heuristic.
**Goal:** Keep it useful but clearly defined.
**Acceptance Criteria:**

* model documented as empirical
* parameters exposed cleanly
* no misleading “physical precision” claims

### 16. Improve Doppler model semantics

**Problem:** Current Doppler is oversimplified.
**Goal:** Make output better or label it honestly.
**Acceptance Criteria:**

* nominal Doppler clearly identified
* aspect/radial interpretation documented
* groundwork laid for time-domain Doppler pipeline

### 17. Remove or simplify unused EM parameters

**Problem:** `epsilon` / `conductivity` are not really active in the current solver.
**Goal:** Reduce confusion.
**Acceptance Criteria:**

* unused fields removed from primary UI
* or angle/frequency dependent reflectivity implemented later

---

# MILESTONE 3 — PROFESSIONAL VISUALIZATION

## Goal

Bring the outputs in line with standard engineering RCS representations.

## Issues

### 18. Add standard azimuth/elevation contour view

**Problem:** Angular heatmap is essential for professional use.
**Goal:** Plot `RCS(el, az)` clearly.
**Acceptance Criteria:**

* contour/heatmap view added
* axes labeled
* colorbar in dBsm

### 19. Replace normalized 3D shell default with true absolute RCS shell

**Problem:** Current 3D surface is stylized and can mislead.
**Goal:** Use standard absolute shell by default.
**Acceptance Criteria:**

* default radius derived from linear RCS
* color from dBsm
* absolute view clearly separated from normalized modes

### 20. Keep normalized/compressed shell modes as optional display modes

**Problem:** Stylized visualization is still useful.
**Goal:** Preserve it, but not as the default.
**Acceptance Criteria:**

* display modes explicitly named
* transforms explained in UI

### 21. Add top/front/side/trimetric camera presets

**Problem:** Professional report views need standard perspectives.
**Goal:** One-click standard views.
**Acceptance Criteria:**

* top, front, side, trimetric views available
* export uses same presets

### 22. Add semi-transparent model overlay in 3D RCS shell

**Problem:** Shell lacks geometric context.
**Goal:** Show target and shell together.
**Acceptance Criteria:**

* mesh overlay toggle
* shell centered on model
* orientation visually obvious

### 23. Fix 3D colorbar normalization

**Problem:** Display colors and colorbar normalization may drift.
**Goal:** Ensure visual correctness.
**Acceptance Criteria:**

* explicit shared normalization object used

### 24. Add axis labels and orientation gizmo

**Problem:** Spatial interpretation is weak.
**Goal:** Make 3D plots readable immediately.
**Acceptance Criteria:**

* X/Y/Z labels
* forward/up direction visible
* orientation note in plot or legend

### 25. Add publication/report export presets

**Problem:** Results should export cleanly.
**Goal:** Generate professional-looking figures.
**Acceptance Criteria:**

* PNG/PDF/SVG export
* consistent titles, labels, colorbars
* report-friendly layout

---

# MILESTONE 4 — CONTRIBUTION & INTERPRETABILITY

## Goal

Show where the return likely comes from on the actual model.

## Issues

### 26. Add per-face illumination heatmap

**Problem:** Users need to see illuminated regions.
**Goal:** Color faces by incident illumination.
**Acceptance Criteria:**

* selectable for chosen look direction
* works on current mesh

### 27. Add per-face local scattering proxy heatmap

**Problem:** Need a surface-based contribution view.
**Goal:** Show local facet scattering proxy.
**Acceptance Criteria:**

* face colors represent local contribution estimate
* labeled clearly as proxy

### 28. Add per-face monostatic return contribution proxy

**Problem:** Need to see which faces likely return energy to radar.
**Goal:** Map return-like contributions to the model.
**Acceptance Criteria:**

* uses reflected-direction alignment back to radar
* face heatmap updates for selected angle

### 29. Add reflected-direction arrow overlay

**Problem:** Need local directional insight.
**Goal:** Draw strongest specular reflection vectors.
**Acceptance Criteria:**

* arrows originate from face centers
* threshold/top-percent filtering
* vector direction = reflected direction
* vector magnitude = contribution proxy

### 30. Link angular plots to model contribution views

**Problem:** Hard to connect lobes to geometry.
**Goal:** Click angle, inspect model contributors.
**Acceptance Criteria:**

* selecting point on polar/contour view updates model view
* linked aspect displayed numerically

### 31. Add synchronized aspect inspector

**Problem:** Need clear angle selection workflow.
**Goal:** One selected aspect shared by plots and model.
**Acceptance Criteria:**

* azimuth/elevation shown
* polar cut, contour, and model contribution views stay in sync

---

# MILESTONE 5 — VALIDATION & TRUST

## Goal

Make the tool testable, benchmarked, and credible.

## Issues

### 32. Build canonical validation scene pack

**Problem:** Solver changes need stable reference scenes.
**Goal:** Add standard test targets.
**Acceptance Criteria:**

* flat plate
* cube
* dihedral
* trihedral
* simple aircraft-like body
* rotor/prop test scene

### 33. Add static regression tests

**Problem:** Solver can drift silently.
**Goal:** Lock in basic behavior.
**Acceptance Criteria:**

* symmetry tests
* no NaN/inf
* expected peaks/nulls
* shape/dimension checks

### 34. Add visual regression tests for plot transforms

**Problem:** Plot correctness is also part of trust.
**Goal:** Verify contour and 3D shell transforms.
**Acceptance Criteria:**

* known fixture output checked
* shell radius mapping tested

### 35. Add compare-two-runs workflow

**Problem:** Need to compare model changes and solver changes.
**Goal:** Support delta analysis.
**Acceptance Criteria:**

* compare two runs
* show differences in plots and summary metrics

### 36. Add validation mode in GUI

**Problem:** Testing should be easy to run.
**Goal:** Built-in quick validation workflow.
**Acceptance Criteria:**

* benchmark scenes available from GUI
* one-click validation run

---

# MILESTONE 6 — NCTR / TIME-DOMAIN SIMULATION

## Goal

Extend from static RCS to coherent time-domain return simulation suitable for NCTR research.

## Issues

### 37. Add coherent time-domain return synthesis

**Problem:** NCTR needs time-varying signal, not only static angular maps.
**Goal:** Generate complex return signal over time.
**Acceptance Criteria:**

* return signal `E(t)` generated for selected radar/aspect
* coherent phase accumulation included

### 38. Add time-step scene update pipeline

**Problem:** Need moving geometry support over time.
**Goal:** Update scene and returns across timesteps.
**Acceptance Criteria:**

* target attitude and moving parts can update per timestep
* solver supports time-series generation

### 39. Add time-domain RCS trace output

**Problem:** Need direct signature-over-time view.
**Goal:** Plot `RCS(t)` or equivalent return-power trace.
**Acceptance Criteria:**

* time trace view added
* export supported

### 40. Add spectrogram generation

**Problem:** NCTR relies heavily on time-frequency structure.
**Goal:** Compute micro-Doppler spectrogram from time-domain return.
**Acceptance Criteria:**

* STFT/spectrogram view
* adjustable windowing parameters
* export supported

### 41. Add range-Doppler style experimental output

**Problem:** Useful for advanced NCTR workflows.
**Goal:** Support richer time-frequency analysis.
**Acceptance Criteria:**

* experimental range-Doppler or equivalent view
* clearly labeled if approximate

---

# MILESTONE 7 — MOVING COMPONENTS / MICRO-DOPPLER

## Goal

Simulate rotating and moving parts that dominate many NCTR signatures.

## Issues

### 42. Add structured propeller model

**Problem:** Propellers need true time-varying geometry/signature support.
**Goal:** Model propeller motion over time.
**Acceptance Criteria:**

* blade count
* radius
* RPM
* axis/origin
* time-dependent return modulation

### 43. Add structured rotor model

**Problem:** Helicopter-style rotor signatures are important for NCTR.
**Goal:** Model rotor disk and blade motion.
**Acceptance Criteria:**

* rotor motion simulated over time
* micro-Doppler features visible in spectrogram

### 44. Add turbine/fan disk simplified model

**Problem:** Turbine-like components can contribute useful signatures.
**Goal:** Add simplified rotating disk/blade model.
**Acceptance Criteria:**

* configurable rotating component
* coherent return support

### 45. Add moving-component visualization

**Problem:** Need to inspect motion setup.
**Goal:** Visual preview of moving parts and axes.
**Acceptance Criteria:**

* moving part paths visible
* axes/origins shown

### 46. Add micro-Doppler parameter presets

**Problem:** Common setups should be easy to reproduce.
**Goal:** Presets for propeller/rotor/turbine cases.
**Acceptance Criteria:**

* standard presets available
* values editable after load

---

# MILESTONE 8 — COMPARATIVE ANALYSIS & WORKFLOW POLISH

## Goal

Make the tool useful for real signature studies and research comparisons.

## Issues

### 47. Reorganize GUI into workflow tabs

**Problem:** Professional tools need a clean workflow.
**Goal:** Make the UI structured.
**Acceptance Criteria:**

* Geometry
* Materials
* Setup
* Results
* Compare
* NCTR / Time Analysis

### 48. Add quality presets

**Problem:** Users should not tune every internal parameter manually.
**Goal:** Offer preview/standard/high-quality modes.
**Acceptance Criteria:**

* quality presets available
* advanced panel for expert settings

### 49. Add run summary panel

**Problem:** Users need to know exactly what was simulated.
**Goal:** Show a simulation summary.
**Acceptance Criteria:**

* solver mode
* frequency/sweep
* material used
* assumptions
* warnings

### 50. Add multi-frequency comparison dashboard

**Problem:** Comparative studies need side-by-side views.
**Goal:** Compare bands/frequencies easily.
**Acceptance Criteria:**

* multiple frequencies shown together
* standardized layouts

### 51. Add multi-material comparison workflow

**Problem:** Signature studies often compare coatings/materials.
**Goal:** Compare materials on same geometry.
**Acceptance Criteria:**

* overlay or side-by-side material comparison
* result delta view

### 52. Add target-variant comparison workflow

**Problem:** Conceptual design needs variant comparison.
**Goal:** Compare multiple geometry variants.
**Acceptance Criteria:**

* compare runs from different models/configurations
* key delta summary

### 53. Add saved-case library/browser

**Problem:** Research workflows need case management.
**Goal:** Browse and reload previous runs.
**Acceptance Criteria:**

* save/load runs
* metadata searchable
* compare from saved library

### 54. Add template/signature comparison tools

**Problem:** NCTR workflows need signature matching/comparison.
**Goal:** Compare spectrograms or signatures against references.
**Acceptance Criteria:**

* signature template storage
* similarity scoring
* baseline/reference comparison

### 55. Add exportable report sheets

**Problem:** Results should be easy to hand off.
**Goal:** Generate analysis sheets/reports.
**Acceptance Criteria:**

* include geometry, settings, key plots, metadata
* export PDF/HTML or structured report package

---

# RECOMMENDED IMPLEMENTATION ORDER

## Phase Order

1. Core Stabilization
2. Solver Accuracy & Model Honesty
3. Professional Visualization
4. Validation & Trust
5. Contribution & Interpretability
6. NCTR / Time-Domain Simulation
7. Moving Components / Micro-Doppler
8. Comparative Analysis & Workflow Polish

## Reason

* first make the tool stable and trustworthy
* then make the visual outputs correct
* then validate it
* then add deeper interpretation
* then add time-domain NCTR capability
* then polish it into a strong research platform

---

# MINIMUM VIABLE “PROFESSIONAL CONCEPTUAL TOOL”

If you want the shortest path to something already impressive and useful, prioritize:

* official new stack only
* deterministic outputs
* corrected 3D shell
* contour map
* top/front/side/trimetric presets
* model overlay
* validation scene pack
* contribution heatmap
* coherent time-domain return
* spectrogram output
* propeller/rotor moving parts

That would already make it a serious tool.

---

# PROJECT POSITIONING STATEMENT

**RCS-CALCULATOR** is a high-frequency radar signature and NCTR simulation platform for conceptual analysis, comparative studies, and research workflows. It focuses on aspect-dependent RCS, coherent return synthesis, moving-part micro-Doppler, and professional engineering visualization while remaining explicit about solver approximations and limitations.

---

I
Below is a **Distribution & Deployment section** you can append to your existing roadmap.
It’s written in the same style as the earlier roadmap so you can **paste it directly into GitHub / README / roadmap.txt**.

---

# MILESTONE 9 — DISTRIBUTION & DEPLOYMENT

## Goal

Make the simulator easy to install, run, and integrate into research workflows across Windows and Linux.

Distribution quality is critical for adoption. A technically strong tool will still fail if users cannot install or run it easily.

The project should support:

* Windows GUI users
* Linux research environments
* automated batch workflows
* reproducible environments

---

# DISTRIBUTION STRATEGY

## Primary Targets

### Windows

Primary entry point for most users.

Provide:

```
standalone executable
or simple installer
```

Requirements:

* no Python installation required
* bundled dependencies
* double-click launch

---

### Linux

Primary environment for research and servers.

Provide:

```
pip installation
or source install
```

Requirements:

* tested on Ubuntu LTS
* documented dependencies
* reproducible install instructions

---

### Docker

Optional but highly useful for:

```
reproducible environments
CI testing
batch simulations
server deployments
```

Docker is especially useful for headless or scripted workflows.

---

# PACKAGING ARCHITECTURE

The project should eventually be split logically into:

```
rcs-core
    simulation engine
    solver implementations
    physics modules

rcs-gui
    desktop application
    visualization
    user interaction

examples
    scripts
    demo models
    tutorials

docker
    reproducible environments
```

This separation allows:

* scripting without GUI
* GUI without rewriting solver
* easier testing and CI

---

# ISSUES

## 56. Build Windows standalone executable

**Problem**

Users should not need to install Python manually.

**Goal**

Provide a Windows release that runs immediately.

**Acceptance Criteria**

* packaged application builds successfully
* executable launches GUI directly
* dependencies bundled
* distributed via GitHub Releases

---

## 57. Optional Windows MSI installer

**Problem**

Professional users prefer installers.

**Goal**

Provide standard Windows installer.

**Acceptance Criteria**

* MSI installer available
* adds start menu shortcut
* installs/uninstalls cleanly

---

## 58. Add Linux installation instructions

**Problem**

Linux users need clear setup instructions.

**Goal**

Support Linux researchers.

**Acceptance Criteria**

* tested on Ubuntu
* install steps documented
* dependencies listed
* GUI launches correctly

---

## 59. Provide pip-installable core library

**Problem**

Researchers want to script simulations.

**Goal**

Allow installation via pip.

**Acceptance Criteria**

```
pip install rcs-simulator
```

* installs core solver
* exposes Python API
* works without GUI

---

## 60. Create simple Python API

**Problem**

Researchers often prefer scripted workflows.

**Goal**

Allow simulations from Python scripts.

Example usage:

```python
from rcs import simulate

result = simulate(
    model="aircraft.stl",
    frequency_hz=10e9,
    method="sbr"
)
```

**Acceptance Criteria**

* stable API
* documented parameters
* example scripts provided

---

## 61. Add CLI interface

**Problem**

Batch simulations should run without GUI.

**Goal**

Provide command-line interface.

Example:

```
rcs-simulate aircraft.stl --freq 10e9 --method sbr
```

**Acceptance Criteria**

* command-line tool available
* supports configuration files
* produces output data

---

## 62. Provide Docker environment

**Problem**

Dependency issues discourage adoption.

**Goal**

Provide reproducible container environment.

**Acceptance Criteria**

* Dockerfile builds successfully
* simulation runs inside container
* usable for headless runs

---

## 63. Add CI build pipeline

**Problem**

Manual builds are error-prone.

**Goal**

Automate testing and packaging.

**Acceptance Criteria**

* CI runs tests
* builds release artifacts
* checks installability

---

## 64. Provide example models

**Problem**

Users need immediate demonstrations.

**Goal**

Include sample scenes.

Examples:

```
flat_plate
dihedral
trihedral
simple_aircraft
propeller_demo
```

**Acceptance Criteria**

* examples load correctly
* produce expected plots
* included in repository

---

## 65. Add tutorial examples

**Problem**

Users must quickly understand workflow.

**Goal**

Provide beginner-friendly examples.

Examples:

```
basic RCS simulation
aspect sweep
micro-Doppler example
propeller simulation
```

**Acceptance Criteria**

* step-by-step tutorial
* reproducible results
* minimal setup required

---

# OPTIONAL FEATURES (LATER)

Not required for V1 but beneficial later.

### Linux AppImage / Flatpak

Portable Linux distribution.

### Conda environment

For research environments.

### Jupyter tutorial notebooks

Interactive educational examples.

### Remote simulation mode

Run solver on server while GUI acts as frontend.

---

# MINIMUM DISTRIBUTION GOAL (V1)

To reach a usable first release:

Required:

```
Windows standalone build
Linux install instructions
example scenes
Python API
```

Optional but recommended:

```
CLI interface
Docker environment
```

---

# LONG-TERM DISTRIBUTION GOAL

A mature release should allow:

```
GUI exploration
scripted simulations
batch processing
reproducible research workflows
```

across both Windows and Linux environments.

---

# FINAL NOTE

Ease of installation and clear examples are often the deciding factor for adoption.

Many technically strong research tools fail because:

```
installation is difficult
documentation is unclear
examples are missing
```

