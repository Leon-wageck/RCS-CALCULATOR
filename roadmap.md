# RCS-CALCULATOR ROADMAP

## Target: Professional Conceptual RCS / Signature Analysis Tool with NCTR Capability

## Product Goal

Build a **professional conceptual RCS and radar-signature analysis tool** that is:

- accurate enough for **high-frequency RCS studies**
- suitable for **NCTR / micro-Doppler research**
- deterministic and reproducible
- visually aligned with engineering standards
- honest about model assumptions and limits
- strong for comparative analysis, research, and development

## Non-Goal

This tool is **not** a full-wave EM solver and does **not** aim to replace CST / FEKO / HFSS for all cases.

The tool should instead become a strong **high-frequency radar signature and NCTR simulation platform** based on:

- Facet Physical Optics
- heuristic diffraction
- SBR / ray-based methods
- coherent return synthesis
- moving-part / micro-Doppler modelling

## Development Philosophy

This project should evolve as a **research instrument** and **engineering analysis tool**, not as a rushed product.

Milestones represent **capability improvements**, not strict deadlines.

Priority should go to:

- correctness of interpretation
- solver honesty
- reproducibility
- validation
- clear visual outputs
- gradual NCTR capability

---

# HIGH-LEVEL DEVELOPMENT PHASES

1. Core Stabilization
2. Early Visual Impact Features
3. Solver Accuracy & Model Honesty
4. Professional Visualization
5. Validation & Trust
6. Contribution & Interpretability
7. NCTR / Time-Domain Simulation
8. Moving Components / Micro-Doppler
9. Comparative Analysis & Workflow Polish
10. Distribution & Deployment
11. Documentation

---

# MILESTONE 1 — CORE STABILIZATION

## Goal

Make the new stack the only trusted stack, clean up architecture, and ensure deterministic behavior.

## Issues

### 1. Define official application stack

**Problem:** Old and new stacks coexist.  
**Goal:** One official GUI path and one official simulation backend.  
**Acceptance Criteria:**

- official startup path documented
- legacy path marked deprecated or archived
- no ambiguity about which frontend/backend is current

### 2. Clean and normalize `main_window.py`

**Problem:** File structure is messy, duplicated, or hard to trust.  
**Goal:** Make GUI code readable and maintainable.  
**Acceptance Criteria:**

- duplicate methods removed
- broken or placeholder code removed
- GUI file split if needed

### 3. Separate GUI responsibilities

**Problem:** Main window likely owns too much.  
**Goal:** Split UI, plotting, worker logic, and data flow.  
**Acceptance Criteria:**

- plotting logic isolated
- worker or thread logic isolated
- UI state separated from simulation execution

### 4. Remove hidden randomness from simulation outputs

**Problem:** Results must be reproducible.  
**Goal:** Same input must produce same output.  
**Acceptance Criteria:**

- no random noise in solver output by default
- synthetic noise, if any, is explicit and optional

### 5. Add result completeness and cancellation state

**Problem:** Partial results can look valid.  
**Goal:** Make cancellation explicit.  
**Acceptance Criteria:**

- `SimulationResult` tracks completed, cancelled, or partial state
- GUI handles partial results safely

### 6. Improve progress reporting

**Problem:** Progress is coarse and frequency-only.  
**Goal:** Better simulation progress feedback.  
**Acceptance Criteria:**

- progress updates across frequency and elevation or time
- no 0→100 jump for single-frequency runs

### 7. Remove or quarantine legacy solver path

**Problem:** Old solver code causes confusion and future regressions.  
**Goal:** Keep only one supported stack.  
**Acceptance Criteria:**

- legacy solver moved to archive or deprecated module
- GUI does not call legacy path

### 8. Add metadata-rich result objects

**Problem:** Results are not self-describing enough.  
**Goal:** Make runs reproducible and exportable.  
**Acceptance Criteria:**

- result contains solver mode, mesh, material, frequency, timestamp, and version
- exports preserve metadata

---

# MILESTONE 2 — EARLY VISUAL IMPACT FEATURES

## Goal

Implement the highest visual impact features with the least work near the start so the project quickly looks mature and professional.

## Issues

### 9. Replace normalized 3D shell default with true absolute RCS shell

**Problem:** Current 3D surface is stylized and can mislead.  
**Goal:** Use standard absolute shell by default.  
**Acceptance Criteria:**

- default radius derived from linear RCS
- recommended standard mapping uses `sqrt(RCS_linear)`
- color from dBsm
- absolute view clearly separated from normalized modes

### 10. Add standard azimuth/elevation contour view

**Problem:** Angular heatmap is essential for professional use.  
**Goal:** Plot `RCS(el, az)` clearly.  
**Acceptance Criteria:**

- contour or heatmap view added
- axes labeled
- colorbar in dBsm

### 11. Add semi-transparent model overlay in 3D RCS shell

**Problem:** Shell lacks geometric context.  
**Goal:** Show target and shell together.  
**Acceptance Criteria:**

- mesh overlay toggle
- shell centered on model
- orientation visually obvious

---

# MILESTONE 3 — SOLVER ACCURACY & MODEL HONESTY

## Goal

Make the solver clearer, more consistent, and more technically honest.

## Issues

### 12. Document solver mode meanings

**Problem:** Fast, Realistic, and SBR are unclear.  
**Goal:** Explain intended use and limitations.  
**Acceptance Criteria:**

- each mode has UI description
- each mode has documented assumptions

### 13. Audit material model vs actual solver use

**Problem:** Material data model implies more physics than used.  
**Goal:** Align UI and data with implementation.  
**Acceptance Criteria:**

- every material field is either used or documented
- no misleading unused parameters in main workflow

### 14. Fix or relabel polarization handling

**Problem:** Polarization currently collapses to scalar reflectivity.  
**Goal:** Be honest and consistent.  
**Acceptance Criteria:**

- either proper polarization handling added
- or relabeled as effective reflectivity weighting

### 15. Improve SBR monostatic return logic

**Problem:** Current return detection is heuristic.  
**Goal:** Make ray return evaluation more consistent.  
**Acceptance Criteria:**

- explicit return alignment model
- receiver acceptance cone or equivalent logic
- documented behavior

### 16. Expose ray bundle density as a setting or preset

**Problem:** SBR quality is fixed and hidden.  
**Goal:** Make quality/performance tunable.  
**Acceptance Criteria:**

- preview, standard, and high-quality ray bundle settings
- configurable through settings or quality presets

### 17. Optimize diffraction candidate handling

**Problem:** Corner diffraction likely scales poorly.  
**Goal:** Reduce combinatorial cost.  
**Acceptance Criteria:**

- corner candidate generation optimized
- performance improved on dense meshes

### 18. Review engine or propeller signature model

**Problem:** Current model is heuristic.  
**Goal:** Keep it useful but clearly defined.  
**Acceptance Criteria:**

- model documented as empirical
- parameters exposed cleanly
- no misleading physical-precision claims

### 19. Improve Doppler model semantics

**Problem:** Current Doppler is oversimplified.  
**Goal:** Make output better or label it honestly.  
**Acceptance Criteria:**

- nominal Doppler clearly identified
- aspect or radial interpretation documented
- groundwork laid for time-domain Doppler pipeline

### 20. Remove or simplify unused EM parameters

**Problem:** `epsilon` and `conductivity` are not really active in the current solver.  
**Goal:** Reduce confusion.  
**Acceptance Criteria:**

- unused fields removed from primary UI
- or angle/frequency dependent reflectivity implemented later

## High-value low-effort solver accuracy upgrades

### 21. Use continuous SBR return weighting instead of hard alignment threshold

**Problem:** Binary return gating causes unstable glints and unrealistic on/off behavior.  
**Goal:** Weight return strength continuously by alignment.  
**Acceptance Criteria:**

- threshold-based monostatic gate replaced or augmented with continuous return weighting
- aspect behavior becomes smoother
- documented exponent or tuning parameter included

### 22. Add facet shadowing or visibility filtering

**Problem:** Front-facing facets can contribute even when geometrically shadowed.  
**Goal:** Suppress hidden facet contributions.  
**Acceptance Criteria:**

- optional shadow or visibility filtering for facet contributions
- uses existing ray-intersection infrastructure where possible
- improved realism on concave or occluded geometry

### 23. Add angle-dependent reflectivity

**Problem:** Single scalar reflectivity is too crude across incidence angles.  
**Goal:** Make reflectivity depend on angle of incidence.  
**Acceptance Criteria:**

- effective reflectivity varies with incidence angle
- simple empirical or simplified Fresnel-style model supported
- broadside vs grazing behavior improved

### 24. Improve diffraction directional filtering

**Problem:** Heuristic diffraction can be too strong or too noisy.  
**Goal:** Only allow plausible edge or corner contributions.  
**Acceptance Criteria:**

- stronger illumination, visibility, and direction checks
- reduced off-specular clutter
- cleaner contour plots and better runtime

### 25. Keep normalized or compressed shell modes as optional display modes

**Problem:** Stylized visualization is still useful but should not be mistaken for standard output.  
**Goal:** Preserve it, but not as the default.  
**Acceptance Criteria:**

- display modes explicitly named
- transforms explained in UI

---

# MILESTONE 4 — PROFESSIONAL VISUALIZATION

## Goal

Bring the outputs in line with standard engineering RCS representations.

## Issues

### 26. Add top, front, side, and trimetric camera presets

**Problem:** Professional report views need standard perspectives.  
**Goal:** One-click standard views.  
**Acceptance Criteria:**

- top, front, side, and trimetric views available
- export uses same presets

### 27. Fix 3D colorbar normalization

**Problem:** Display colors and colorbar normalization may drift.  
**Goal:** Ensure visual correctness.  
**Acceptance Criteria:**

- explicit shared normalization object used

### 28. Add axis labels and orientation gizmo

**Problem:** Spatial interpretation is weak.  
**Goal:** Make 3D plots readable immediately.  
**Acceptance Criteria:**

- X, Y, and Z labels
- forward or up direction visible
- orientation note in plot or legend

### 29. Add publication or report export presets

**Problem:** Results should export cleanly.  
**Goal:** Generate professional-looking figures.  
**Acceptance Criteria:**

- PNG, PDF, and SVG export
- consistent titles, labels, and colorbars
- report-friendly layout

---

# MILESTONE 5 — VALIDATION & TRUST

## Goal

Make the tool testable, benchmarked, and credible.

## Issues

### 30. Build canonical validation scene pack

**Problem:** Solver changes need stable reference scenes.  
**Goal:** Add standard test targets.  
**Acceptance Criteria:**

- flat plate
- cube
- dihedral
- trihedral
- simple aircraft-like body
- rotor or prop test scene

### 31. Add static regression tests

**Problem:** Solver can drift silently.  
**Goal:** Lock in basic behavior.  
**Acceptance Criteria:**

- symmetry tests
- no NaN or inf
- expected peaks or nulls
- shape and dimension checks

### 32. Add visual regression tests for plot transforms

**Problem:** Plot correctness is also part of trust.  
**Goal:** Verify contour and 3D shell transforms.  
**Acceptance Criteria:**

- known fixture output checked
- shell radius mapping tested

### 33. Add compare-two-runs workflow

**Problem:** Need to compare model changes and solver changes.  
**Goal:** Support delta analysis.  
**Acceptance Criteria:**

- compare two runs
- show differences in plots and summary metrics

### 34. Add validation mode in GUI

**Problem:** Testing should be easy to run.  
**Goal:** Built-in quick validation workflow.  
**Acceptance Criteria:**

- benchmark scenes available from GUI
- one-click validation run

---

# MILESTONE 6 — CONTRIBUTION & INTERPRETABILITY

## Goal

Show where the return likely comes from on the actual model.

## Issues

### 35. Add per-face illumination heatmap

**Problem:** Users need to see illuminated regions.  
**Goal:** Color faces by incident illumination.  
**Acceptance Criteria:**

- selectable for chosen look direction
- works on current mesh

### 36. Add per-face local scattering proxy heatmap

**Problem:** Need a surface-based contribution view.  
**Goal:** Show local facet scattering proxy.  
**Acceptance Criteria:**

- face colors represent local contribution estimate
- labeled clearly as proxy

### 37. Add per-face monostatic return contribution proxy

**Problem:** Need to see which faces likely return energy to radar.  
**Goal:** Map return-like contributions to the model.  
**Acceptance Criteria:**

- uses reflected-direction alignment back to radar
- face heatmap updates for selected angle

### 38. Add reflected-direction arrow overlay

**Problem:** Need local directional insight.  
**Goal:** Draw strongest specular reflection vectors.  
**Acceptance Criteria:**

- arrows originate from face centers
- threshold or top-percent filtering
- vector direction equals reflected direction
- vector magnitude equals contribution proxy

### 39. Link angular plots to model contribution views

**Problem:** Hard to connect lobes to geometry.  
**Goal:** Click angle, inspect model contributors.  
**Acceptance Criteria:**

- selecting point on polar or contour view updates model view
- linked aspect displayed numerically

### 40. Add synchronized aspect inspector

**Problem:** Need clear angle selection workflow.  
**Goal:** One selected aspect shared by plots and model.  
**Acceptance Criteria:**

- azimuth and elevation shown
- polar cut, contour, and model contribution views stay in sync

---

# MILESTONE 7 — NCTR / TIME-DOMAIN SIMULATION

## Goal

Extend from static RCS to coherent time-domain return simulation suitable for NCTR research.

## Issues

### 41. Add coherent time-domain return synthesis

**Problem:** NCTR needs time-varying signal, not only static angular maps.  
**Goal:** Generate complex return signal over time.  
**Acceptance Criteria:**

- return signal `E(t)` generated for selected radar or aspect
- coherent phase accumulation included

### 42. Add time-step scene update pipeline

**Problem:** Need moving geometry support over time.  
**Goal:** Update scene and returns across timesteps.  
**Acceptance Criteria:**

- target attitude and moving parts can update per timestep
- solver supports time-series generation

### 43. Add time-domain RCS trace output

**Problem:** Need direct signature-over-time view.  
**Goal:** Plot `RCS(t)` or equivalent return-power trace.  
**Acceptance Criteria:**

- time trace view added
- export supported

### 44. Add spectrogram generation

**Problem:** NCTR relies heavily on time-frequency structure.  
**Goal:** Compute micro-Doppler spectrogram from time-domain return.  
**Acceptance Criteria:**

- STFT or spectrogram view
- adjustable windowing parameters
- export supported

### 45. Add range-Doppler style experimental output

**Problem:** Useful for advanced NCTR workflows.  
**Goal:** Support richer time-frequency analysis.  
**Acceptance Criteria:**

- experimental range-Doppler or equivalent view
- clearly labeled if approximate

---

# MILESTONE 8 — MOVING COMPONENTS / MICRO-DOPPLER

## Goal

Simulate rotating and moving parts that dominate many NCTR signatures.

## Issues

### 46. Add structured propeller model

**Problem:** Propellers need true time-varying geometry or signature support.  
**Goal:** Model propeller motion over time.  
**Acceptance Criteria:**

- blade count
- radius
- RPM
- axis or origin
- time-dependent return modulation

### 47. Add structured rotor model

**Problem:** Helicopter-style rotor signatures are important for NCTR.  
**Goal:** Model rotor disk and blade motion.  
**Acceptance Criteria:**

- rotor motion simulated over time
- micro-Doppler features visible in spectrogram

### 48. Add turbine or fan disk simplified model

**Problem:** Turbine-like components can contribute useful signatures.  
**Goal:** Add simplified rotating disk or blade model.  
**Acceptance Criteria:**

- configurable rotating component
- coherent return support

### 49. Add moving-component visualization

**Problem:** Need to inspect motion setup.  
**Goal:** Visual preview of moving parts and axes.  
**Acceptance Criteria:**

- moving part paths visible
- axes or origins shown

### 50. Add micro-Doppler parameter presets

**Problem:** Common setups should be easy to reproduce.  
**Goal:** Presets for propeller, rotor, or turbine cases.  
**Acceptance Criteria:**

- standard presets available
- values editable after load

---

# MILESTONE 9 — COMPARATIVE ANALYSIS & WORKFLOW POLISH

## Goal

Make the tool useful for real signature studies and research comparisons.

## Issues

### 51. Reorganize GUI into workflow tabs

**Problem:** Professional tools need a clean workflow.  
**Goal:** Make the UI structured.  
**Acceptance Criteria:**

- Geometry
- Materials
- Setup
- Results
- Compare
- NCTR or Time Analysis

### 52. Add quality presets

**Problem:** Users should not tune every internal parameter manually.  
**Goal:** Offer preview, standard, and high-quality modes.  
**Acceptance Criteria:**

- quality presets available
- advanced panel for expert settings

### 53. Add run summary panel

**Problem:** Users need to know exactly what was simulated.  
**Goal:** Show a simulation summary.  
**Acceptance Criteria:**

- solver mode
- frequency or sweep
- material used
- assumptions
- warnings

### 54. Add multi-frequency comparison dashboard

**Problem:** Comparative studies need side-by-side views.  
**Goal:** Compare bands or frequencies easily.  
**Acceptance Criteria:**

- multiple frequencies shown together
- standardized layouts

### 55. Add multi-material comparison workflow

**Problem:** Signature studies often compare coatings or materials.  
**Goal:** Compare materials on same geometry.  
**Acceptance Criteria:**

- overlay or side-by-side material comparison
- result delta view

### 56. Add target-variant comparison workflow

**Problem:** Conceptual design needs variant comparison.  
**Goal:** Compare multiple geometry variants.  
**Acceptance Criteria:**

- compare runs from different models or configurations
- key delta summary

### 57. Add saved-case library or browser

**Problem:** Research workflows need case management.  
**Goal:** Browse and reload previous runs.  
**Acceptance Criteria:**

- save or load runs
- metadata searchable
- compare from saved library

### 58. Add template or signature comparison tools

**Problem:** NCTR workflows need signature matching or comparison.  
**Goal:** Compare spectrograms or signatures against references.  
**Acceptance Criteria:**

- signature template storage
- similarity scoring
- baseline or reference comparison

### 59. Add exportable report sheets

**Problem:** Results should be easy to hand off.  
**Goal:** Generate analysis sheets or reports.  
**Acceptance Criteria:**

- include geometry, settings, key plots, and metadata
- export PDF, HTML, or structured report package

---

# MILESTONE 10 — DISTRIBUTION & DEPLOYMENT

## Goal

Make the simulator easy to install, run, and integrate into research workflows across Windows and Linux.

Distribution quality is critical for adoption. A technically strong tool will still fail if users cannot install or run it easily.

The project should support:

- Windows GUI users
- Linux research environments
- automated batch workflows
- reproducible environments

## Distribution Strategy

### Windows

Primary entry point for most users.

Provide:

- standalone executable
- or simple installer

Requirements:

- no Python installation required
- bundled dependencies
- double-click launch

### Linux

Primary environment for research and servers.

Provide:

- pip installation
- or source install

Requirements:

- tested on Ubuntu LTS
- documented dependencies
- reproducible install instructions

### Docker

Optional but highly useful for:

- reproducible environments
- CI testing
- batch simulations
- server deployments

Docker is especially useful for headless or scripted workflows.

## Packaging Architecture

The project should eventually be split logically into:

- `rcs-core`
  - simulation engine
  - solver implementations
  - physics modules

- `rcs-gui`
  - desktop application
  - visualization
  - user interaction

- `examples`
  - scripts
  - demo models
  - tutorials

- `docker`
  - reproducible environments

This separation allows:

- scripting without GUI
- GUI without rewriting solver
- easier testing and CI

## Issues

### 60. Build Windows standalone executable

**Problem:** Users should not need to install Python manually.  
**Goal:** Provide a Windows release that runs immediately.  
**Acceptance Criteria:**

- packaged application builds successfully
- executable launches GUI directly
- dependencies bundled
- distributed via GitHub Releases

### 61. Optional Windows MSI installer

**Problem:** Professional users prefer installers.  
**Goal:** Provide standard Windows installer.  
**Acceptance Criteria:**

- MSI installer available
- adds start menu shortcut
- installs or uninstalls cleanly

### 62. Add Linux installation instructions

**Problem:** Linux users need clear setup instructions.  
**Goal:** Support Linux researchers.  
**Acceptance Criteria:**

- tested on Ubuntu
- install steps documented
- dependencies listed
- GUI launches correctly

### 63. Provide pip-installable core library

**Problem:** Researchers want to script simulations.  
**Goal:** Allow installation via pip.  
**Acceptance Criteria:**

- `pip install rcs-simulator`
- installs core solver
- exposes Python API
- works without GUI

### 64. Create simple Python API

**Problem:** Researchers often prefer scripted workflows.  
**Goal:** Allow simulations from Python scripts.  
**Acceptance Criteria:**

- stable API
- documented parameters
- example scripts provided

### 65. Add CLI interface

**Problem:** Batch simulations should run without GUI.  
**Goal:** Provide command-line interface.  
**Acceptance Criteria:**

- command-line tool available
- supports configuration files
- produces output data

### 66. Provide Docker environment

**Problem:** Dependency issues discourage adoption.  
**Goal:** Provide reproducible container environment.  
**Acceptance Criteria:**

- Dockerfile builds successfully
- simulation runs inside container
- usable for headless runs

### 67. Add CI build pipeline

**Problem:** Manual builds are error-prone.  
**Goal:** Automate testing and packaging.  
**Acceptance Criteria:**

- CI runs tests
- builds release artifacts
- checks installability

### 68. Provide example models

**Problem:** Users need immediate demonstrations.  
**Goal:** Include sample scenes.  
**Acceptance Criteria:**

- flat_plate
- dihedral
- trihedral
- simple_aircraft
- propeller_demo
- examples load correctly
- produce expected plots
- included in repository

### 69. Add tutorial examples

**Problem:** Users must quickly understand workflow.  
**Goal:** Provide beginner-friendly examples.  
**Acceptance Criteria:**

- step-by-step tutorial
- reproducible results
- minimal setup required

## Optional later

- Linux AppImage or Flatpak
- Conda environment
- Jupyter tutorial notebooks
- remote simulation mode

---

# MILESTONE 11 — DOCUMENTATION

## Goal

Make the project understandable and adoptable for researchers and advanced users.

## Issues

### 70. Write architecture overview

### 71. Document solver physics assumptions

### 72. Add first-simulation tutorial

### 73. Add NCTR workflow tutorial

### 74. Add validation or benchmark documentation

---

# RECOMMENDED IMPLEMENTATION ORDER

## Phase Order

1. Core Stabilization
2. Early Visual Impact Features
3. Solver Accuracy & Model Honesty
4. Professional Visualization
5. Validation & Trust
6. Contribution & Interpretability
7. NCTR / Time-Domain Simulation
8. Moving Components / Micro-Doppler
9. Comparative Analysis & Workflow Polish
10. Distribution & Deployment
11. Documentation

## Reason

- first make the tool stable and trustworthy
- then make it look immediately more professional
- then improve solver honesty and low-effort accuracy
- then standardize visuals
- then validate it
- then add deeper interpretation
- then add time-domain NCTR capability
- then polish and distribute it

---

# MINIMUM VIABLE PROFESSIONAL VERSION (V1)

If you want the shortest path to something already impressive and useful, prioritize:

- official new stack only
- deterministic outputs
- absolute 3D shell
- contour map
- top, front, side, and trimetric presets
- model overlay
- validation scene pack
- contribution heatmap
- continuous SBR return weighting
- facet shadowing or visibility filtering
- coherent time-domain return
- spectrogram output
- propeller or rotor moving parts

That would already make it a serious tool.

---

# PROJECT POSITIONING STATEMENT

**RCS-CALCULATOR** is a high-frequency radar signature and NCTR simulation platform for conceptual analysis, comparative studies, and research workflows. It focuses on aspect-dependent RCS, coherent return synthesis, moving-part micro-Doppler, and professional engineering visualization while remaining explicit about solver approximations and limitations.
