"""Reference radar presets for quick configuration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class RadarProfile:
    """Minimal radar description used to pre-fill simulation settings."""

    name: str
    band: str
    frequency_ghz: Optional[float] = None
    polarization: str = "H"
    sweep_start_ghz: Optional[float] = None
    sweep_stop_ghz: Optional[float] = None
    sweep_steps: Optional[int] = None
    max_reflections: Optional[int] = None
    default_speed_mps: Optional[float] = None
    note: Optional[str] = None


RADAR_PROFILES: Dict[str, RadarProfile] = {
    # ------------------------------------------------------------------
    # Generic/manual
    # ------------------------------------------------------------------
    "Custom (manual)": RadarProfile(
        name="Custom (manual)",
        band="S",
        frequency_ghz=None,
    ),

    # ------------------------------------------------------------------
    # Legacy / existing profiles
    # ------------------------------------------------------------------
    "S-300 30N6 Flap Lid (X-band 9.2 GHz)": RadarProfile(
        name="S-300 30N6 Flap Lid (X-band 9.2 GHz)",
        band="X",
        frequency_ghz=9.2,
        polarization="H/V",
        max_reflections=4,
    ),
    "S-400 92N6E Grave Stone (X-band 10 GHz)": RadarProfile(
        name="S-400 92N6E Grave Stone (X-band 10 GHz)",
        band="X",
        frequency_ghz=10.0,
        polarization="H/V",
        max_reflections=5,
    ),
    "S-400 91N6E Big Bird (S-band 3.2 GHz)": RadarProfile(
        name="S-400 91N6E Big Bird (S-band 3.2 GHz)",
        band="S",
        frequency_ghz=3.2,
        polarization="H/V",
    ),
    "Buk-M2 9S36 Fire Dome (X-band 9.5 GHz)": RadarProfile(
        name="Buk-M2 9S36 Fire Dome (X-band 9.5 GHz)",
        band="X",
        frequency_ghz=9.5,
        polarization="H",
    ),
    "Patriot AN/MPQ-65 (C-band 4.0 GHz)": RadarProfile(
        name="Patriot AN/MPQ-65 (C-band 4.0 GHz)",
        band="C",
        frequency_ghz=4.0,
        polarization="H",
        max_reflections=4,
    ),
    "NASAMS AN/MPQ-64 Sentinel (X-band 9.5 GHz)": RadarProfile(
        name="NASAMS AN/MPQ-64 Sentinel (X-band 9.5 GHz)",
        band="X",
        frequency_ghz=9.5,
        polarization="H",
    ),
    "MEADS MFCR (X-band 10 GHz sweep)": RadarProfile(
        name="MEADS MFCR (X-band 10 GHz sweep)",
        band="X",
        frequency_ghz=None,
        polarization="H",
        sweep_start_ghz=8.5,
        sweep_stop_ghz=11.5,
        sweep_steps=6,
        max_reflections=4,
    ),
    "IRIS-T SLM TRML-4D (S-band 3.5 GHz)": RadarProfile(
        name="IRIS-T SLM TRML-4D (S-band 3.5 GHz)",
        band="S",
        frequency_ghz=3.5,
        polarization="H",
    ),

    # ------------------------------------------------------------------
    # Civil / ATC / weather radars (generic presets)
    # ------------------------------------------------------------------
    "ATC Terminal Approach (S-band 2.8 GHz)": RadarProfile(
        name="ATC Terminal Approach (S-band 2.8 GHz)",
        band="S",
        frequency_ghz=2.8,
        polarization="H/V",
        max_reflections=2,
        note="Generic terminal area surveillance radar preset",
    ),
    "ATC En-Route (L-band 1.3 GHz)": RadarProfile(
        name="ATC En-Route (L-band 1.3 GHz)",
        band="L",
        frequency_ghz=1.3,
        polarization="H",
        max_reflections=2,
        note="Generic long-range en-route surveillance radar",
    ),
    "Airport Surface Movement Radar (X-band 9.4 GHz)": RadarProfile(
        name="Airport Surface Movement Radar (X-band 9.4 GHz)",
        band="X",
        frequency_ghz=9.4,
        polarization="H",
        max_reflections=3,
        note="Generic surface movement / ground radar",
    ),
    "Civil Weather Radar (C-band 5.6 GHz)": RadarProfile(
        name="Civil Weather Radar (C-band 5.6 GHz)",
        band="C",
        frequency_ghz=5.6,
        polarization="H/V",
        max_reflections=1,
        note="Generic C-band weather radar",
    ),

    # ------------------------------------------------------------------
    # NATO / Western military surveillance radars
    # ------------------------------------------------------------------
    "NATO – X-Band (10 GHz)": RadarProfile(
        name="NATO – X-Band (10 GHz)",
        band="X",
        frequency_ghz=10.0,
        polarization="H",
        max_reflections=3,
        note="Generic NATO X-band fire-control / tracking radar",
    ),
    "NATO AN/TPS-77 (L-band 1.3 GHz)": RadarProfile(
        name="NATO AN/TPS-77 (L-band 1.3 GHz)",
        band="L",
        frequency_ghz=1.3,
        polarization="H",
        max_reflections=3,
        note="Mobile long-range air surveillance radar",
    ),
    "NATO AN/TPS-59 (L-band 1.25 GHz)": RadarProfile(
        name="NATO AN/TPS-59 (L-band 1.25 GHz)",
        band="L",
        frequency_ghz=1.25,
        polarization="H",
        max_reflections=3,
        note="Long-range 3D air surveillance radar",
    ),
    "Giraffe AMB (C-band 5.4 GHz)": RadarProfile(
        name="Giraffe AMB (C-band 5.4 GHz)",
        band="C",
        frequency_ghz=5.4,
        polarization="H",
        max_reflections=3,
        note="Short- to medium-range air surveillance radar",
    ),
    "ELM-2084 MMR (S-band 3.0 GHz)": RadarProfile(
        name="ELM-2084 MMR (S-band 3.0 GHz)",
        band="S",
        frequency_ghz=3.0,
        polarization="H",
        max_reflections=4,
        note="Multi-mission radar used in various NATO systems",
    ),
    "SMART-L Long-Range Radar (L-band 1.4 GHz)": RadarProfile(
        name="SMART-L Long-Range Radar (L-band 1.4 GHz)",
        band="L",
        frequency_ghz=1.4,
        polarization="H",
        max_reflections=3,
        note="Naval long-range air surveillance radar",
    ),

    # ------------------------------------------------------------------
    # Russian / CIS radars
    # ------------------------------------------------------------------
    "S-300 64N6 Big Bird (S-band 3.0 GHz)": RadarProfile(
        name="S-300 64N6 Big Bird (S-band 3.0 GHz)",
        band="S",
        frequency_ghz=3.0,
        polarization="H/V",
        max_reflections=4,
        note="Long-range early warning / acquisition radar",
    ),
    "S-400 96L6 Cheese Board (S-band 3.0 GHz)": RadarProfile(
        name="S-400 96L6 Cheese Board (S-band 3.0 GHz)",
        band="S",
        frequency_ghz=3.0,
        polarization="H",
        max_reflections=4,
        note="All-altitude surveillance radar",
    ),
    "Nebo-M RLM-M (VHF-band 0.3 GHz)": RadarProfile(
        name="Nebo-M RLM-M (VHF-band 0.3 GHz)",
        band="VHF",
        frequency_ghz=0.3,
        polarization="H",
        max_reflections=2,
        note="VHF AESA radar for long-range early warning",
    ),
    "P-18 Spoon Rest (VHF-band 0.15 GHz)": RadarProfile(
        name="P-18 Spoon Rest (VHF-band 0.15 GHz)",
        band="VHF",
        frequency_ghz=0.15,
        polarization="H",
        max_reflections=2,
        note="Legacy 2D VHF early warning radar",
    ),
    "36D6 Tin Shield (S-band 3.0 GHz)": RadarProfile(
        name="36D6 Tin Shield (S-band 3.0 GHz)",
        band="S",
        frequency_ghz=3.0,
        polarization="H",
        max_reflections=3,
        note="3D air surveillance radar often paired with S-300",
    ),

    # ------------------------------------------------------------------
    # AESA / advanced phased-array radars
    # ------------------------------------------------------------------
    "AN/APG-77 (F-22 AESA, X-band 10 GHz)": RadarProfile(
        name="AN/APG-77 (F-22 AESA, X-band 10 GHz)",
        band="X",
        frequency_ghz=10.0,
        polarization="H/V",
        max_reflections=3,
        note="US stealth fighter AESA radar",
    ),
    "AN/APG-81 (F-35 AESA, X-band 10 GHz)": RadarProfile(
        name="AN/APG-81 (F-35 AESA, X-band 10 GHz)",
        band="X",
        frequency_ghz=10.0,
        polarization="H/V",
        max_reflections=3,
        note="Advanced AESA with SAR/GMTI",
    ),
    "AN/SPY-1D(V) AEGIS (S-band 3.1 GHz)": RadarProfile(
        name="AN/SPY-1D(V) AEGIS (S-band 3.1 GHz)",
        band="S",
        frequency_ghz=3.1,
        polarization="H",
        max_reflections=4,
        note="PESA/AESA-like shipborne air & missile defense radar",
    ),
    "AN/SPY-6(V)1 AMDR (S-band 3.3 GHz)": RadarProfile(
        name="AN/SPY-6(V)1 AMDR (S-band 3.3 GHz)",
        band="S",
        frequency_ghz=3.3,
        polarization="H",
        max_reflections=4,
        note="GaN AESA naval radar",
    ),
    "EL/M-2084 MMR AESA (S-band 3.0 GHz)": RadarProfile(
        name="EL/M-2084 MMR AESA (S-band 3.0 GHz)",
        band="S",
        frequency_ghz=3.0,
        polarization="H",
        max_reflections=4,
        note="Iron Dome / NATO users; multi-mission AESA",
    ),
    "RBE2-AA (Rafale AESA, X-band 10 GHz)": RadarProfile(
        name="RBE2-AA (Rafale AESA, X-band 10 GHz)",
        band="X",
        frequency_ghz=10.0,
        polarization="H/V",
        max_reflections=3,
        note="French AESA fighter radar",
    ),
    "Captor-E (Eurofighter AESA, X-band 10 GHz)": RadarProfile(
        name="Captor-E (Eurofighter AESA, X-band 10 GHz)",
        band="X",
        frequency_ghz=10.0,
        polarization="H/V",
        max_reflections=3,
        note="Swashplate AESA with wide field of regard",
    ),
    "Zaslon-M (MiG-31 AESA/PESA hybrid, X-band 9.5 GHz)": RadarProfile(
        name="Zaslon-M (MiG-31 AESA/PESA hybrid, X-band 9.5 GHz)",
        band="X",
        frequency_ghz=9.5,
        polarization="H",
        max_reflections=3,
        note="Large phased array, PESA heritage",
    ),
    "N036 Byelka (Su-57 AESA, X-band 9.4 GHz)": RadarProfile(
        name="N036 Byelka (Su-57 AESA, X-band 9.4 GHz)",
        band="X",
        frequency_ghz=9.4,
        polarization="H/V",
        max_reflections=3,
        note="Russian multi-array AESA with L-band wing arrays",
    ),
    "J-20 Type 1475 AESA (X-band 10 GHz)": RadarProfile(
        name="J-20 Type 1475 AESA (X-band 10 GHz)",
        band="X",
        frequency_ghz=10.0,
        polarization="H/V",
        max_reflections=3,
        note="Chinese high-power AESA for long-range detection",
    ),
    "Ground-Based 55Zh6M Nebo-M AESA (L-band 1.3 GHz)": RadarProfile(
        name="Ground-Based 55Zh6M Nebo-M AESA (L-band 1.3 GHz)",
        band="L",
        frequency_ghz=1.3,
        polarization="H",
        max_reflections=3,
        note="Long-range AESA L-band component for stealth detection",
    ),
    "YLC-8B AESA (S-band 3.2 GHz)": RadarProfile(
        name="YLC-8B AESA (S-band 3.2 GHz)",
        band="S",
        frequency_ghz=3.2,
        polarization="H",
        max_reflections=4,
        note="Chinese AESA with strong anti-stealth capability",
    ),
}


# ----------------------------------------------------------------------
# Legacy compatibility: simple frequency presets for the Tkinter GUI
# ----------------------------------------------------------------------
# The Tk GUI uses a dict[name] -> frequency_in_MHz for the slider.
# We derive that automatically from RADAR_PROFILES so both frontends
# stay in sync.
RADAR_PRESETS: Dict[str, float] = {}

for name, profile in RADAR_PROFILES.items():
    if profile.frequency_ghz is not None:
        freq_mhz = profile.frequency_ghz * 1000.0
    elif profile.sweep_start_ghz is not None and profile.sweep_stop_ghz is not None:
        # Use the mid-sweep frequency as a reasonable default
        freq_mhz = 0.5 * (profile.sweep_start_ghz + profile.sweep_stop_ghz) * 1000.0
    else:
        # Fallback generic 3 GHz if nothing specified
        freq_mhz = 3000.0
    RADAR_PRESETS[name] = freq_mhz


__all__ = ["RadarProfile", "RADAR_PROFILES", "RADAR_PRESETS"]
