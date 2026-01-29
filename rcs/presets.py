"""Radar frequency presets."""

from __future__ import annotations

RADAR_PRESETS = {
    "NATO – L-Band (1.3 GHz)": 1300,
    "NATO – X-Band (10 GHz)": 10000,
    "Russland – S-Band (3.5 GHz)": 3500,
    "Russland – L-Band (1.4 GHz)": 1400,
    "F-14 AWG-9 Radar (5 GHz)": 5000,
    "F-15 AN/APG-63 (10.2 GHz)": 10200,
    "F-16 AN/APG-68 (10.5 GHz)": 10500,
    "F-22 AN/APG-77 (12 GHz)": 12000,
    "Su-35 Irbis-E (10 GHz)": 10000,
    "S-400 91N6E Big Bird (6 GHz)": 6000,
    "Su-57 N036 Belka (9 GHz)": 9000,
    "MiG-31 Zaslon (10.2 GHz)": 10200,
    "S-300 Flap Lid (9.2 GHz)": 9200,
    "S-400 Grave Stone (10 GHz)": 10000,
    "S-400 Big Bird (6 GHz)": 6000,
    "Konteyner OTH Radar (0.02 GHz)": 20,
    "Nebo SV (0.15 GHz)": 150,
    "Nebo-M Multiband (1.5 GHz)": 1500,
    "96L6E Cheese Board (3 GHz)": 3000,
    "Kasta 2E1 (1.2 GHz)": 1200,
}

__all__ = ["RADAR_PRESETS"]
