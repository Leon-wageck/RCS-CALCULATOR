📡 Radar RCS Studio

3D Radar Cross Section Simulator (Open Source)
Physikalisch inspiriert · CAD-basiert · GPU-freundlich · RAM-sparend

🔧 Funktionen

Dieses Projekt simuliert den Radar Cross Section (RCS) von 3D-Objekten anhand echter STLs oder OBJ-Modelle.
Es ist speziell für Luftfahrzeuge ausgelegt, funktioniert aber für jedes triangulierte Modell.

✔ Enthaltene Features

3D Modellanzeige (STL/OBJ)

Monostatische RCS-Simulation
– Azimut / Elevation Scans
– Mehrere Frequenzen (Single + Sweep)
– Polare und 3D-Plots

Raytracing & Physical Optics
– Specular Reflection
– Diffraction (Kanten / Ecken)
– Shadowing

Materialmodell
– Permittivität
– Leitfähigkeit
– Polarisation (H/V/Co-/Cross-pol)

Powerplant Modeling
– Intakes
– Propeller-Disk Model

NCTR Template System
– Signatur speichern & vergleichen
– Template-Library im Benutzerordner

Speicheroptimierte Simulation
– Streaming-Modus: keine 4-GB Arrays mehr
– große Scans auch mit wenig RAM

🆕 Simulation Modes (2025+)

Du kannst nun zwischen drei Stufen wählen:

1) FAST APPROXIMATION (facet_po)

Schnell · Niedriger Speicherverbrauch · Gute Basisqualität

Nur Physical Optics

Keine RAM-Schichten

Kein Engine-Fan-Modell

Ideal für große Az/El-Raster

2) REALISTIC LO MODE (facet_po + diffraction + RAM + Fan)

Ausgewogen · Gute physikalische Annäherung

Physical Optics

Edge + Corner Diffraction

Absorber-Materialmodell (RAM)

Intake & Fan-Modell

Beste Wahl für realistische Flugzeug-Signaturen

3) EXPERIMENTAL SBR MODE (ray, multibounce)

Sehr teuer · experimentell · nicht für jeden Mesh geeignet

Raytracing mit Multibounce

Specular + Diffraction Mischung

Für hohe Details

RAM-optimierter Modus verhindert >4-GB Arrays

⚠ Hinweis: SBR Mode ist experimentell und kann „löchrige“ RCS-Bälle erzeugen, falls Mesh-Normals, Topologie oder Intersector Probleme machen.

📥 Installation
Anforderungen:

Python 3.10 – 3.12

pip

Installieren:
git clone https://github.com/Steiynbrodt/RCS-calculator-3d-
cd RCS-calculator-3d-
pip install -r requirements.txt


Optional (aber wichtig für Raytracing):

pip install rtree


Starten:

python RCS.py

🧭 Bedienung
1. STL/OBJ laden

Links oben auf Open STL klicken.

2. Radarprofil wählen

Beispielsweise:
J-20 Type 1475 AESA (X-Band)
(Ist nur für Meta-Infos, beeinflusst nicht die Simulation selbst.)

3. Frequenz einstellen

Single Frequency

Sweep Mode (Start – Stop – Steps)

4. Winkel einstellen

Azimut / Elevation
Feine Schritte ergeben glattere Polarplots (1° ok).

5. Simulation Mode

Wähle zwischen:

Fast Approximation

Realistic LO

Experimental SBR

6. Material auswählen

z. B.:

CFRP

Aluminium

RAM-beschichtet
(Alles im materials.py definiert.)

7. Engines / Propellers

Intakes modellieren:
Einfach XYZ und Radius setzen.

8. Simulation starten

Die Fortschrittsleiste unten zeigt den Fortschritt an.
Im 3D-Tab kannst du den RCS-Ball visualisieren.

📁 NCTR Templates

Templates speichern den gesamten RCS-Cube:

(frequencies × elevations × azimuths)

Template erstellen

Im Tab Templates / NCTR → Save template

Template Matching

RCS-Ergebnis auswählen → Match templates

Die Library speichert Templates in:

%USERPROFILE%/.rcs/templates/


Zum Teilen einfach die JSON-Dateien uploaden.

🧠 Genauigkeit & Physikmodell

⚠️ Das ist keine militärische Software.
Aber du bekommst ein technisch sinnvolles RCS-Verhalten basierend auf:

Physical Optics (PO)

Geometric Optics (GO)

Keller Diffraction

Shadowing

Simplified RAM absorption

Simplified inlet fan modulation

Das ergibt realistische Trends und semi-realistische absoluten Werte, ideal für:

Lehre

Forschung

Hobby-Radar / Signalverarbeitung

NCTR Methoden (template matching)

Nicht geeignet für:

Klassifizierte Stealth-Analysen

Hardware-Verifikation

Präzise militärische RCS-Prediction

🧩 Dateien & Struktur
rcs/
│ rcs_engine.py       – Kern der Simulation
│ facet_po.py         – Physical Optics
│ diffraction.py      – EDGE & CORNER diffraction
│ physics.py          – Material / dielectric / EM helpers
│ materials.py        – Materialdatenbank
│ templates.py        – NCTR Templates
│ gui/main_window.py  – PyQt UI
│ math_utils.py       – Hilfsfunktionen


🛰 Zukunftspläne

Geplant:

GPU-Beschleunigung (CUDA + numba/cupy)

SBR-Optimierungen (Missed Facets → patching)

bistatic RCS

multipath ground modeling

clutter & noise simulation

doppler-spectrum generator / waterfall

