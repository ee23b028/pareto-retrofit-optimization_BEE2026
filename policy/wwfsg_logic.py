"""
policy/wwfsg_logic.py

Logische Bestimmung der Förderstufe (0-5) gemäß
Sanierungs- und Dekarbonisierungsverordnung der Stadt Wien (WWFSG).

Dieses Modul enthält AUSSCHLIESSLICH Logik:
- keine Beträge
- keine Flächen
- keine CAPEX-Bezüge
"""

from dataclasses import dataclass
from typing import Optional, List


# =====================================================================
# 1) Datenstruktur Förderstufe
# =====================================================================

@dataclass(frozen=True)
class Foerderstufe:
    name: str
    min_savings: float              # kWh/(m²·a)
    max_hwb_factor: Optional[float] # Faktor * HWB_nstEG (None = nicht relevant)

# =====================================================================
# 2) Förderstufen gemäß SanDekVO (rein logisch)
# =====================================================================

STUFE_0 = Foerderstufe("Stufe 0", min_savings=40.0,  max_hwb_factor=None)
STUFE_1 = Foerderstufe("Stufe 1", min_savings=70.0,  max_hwb_factor=1.45)
STUFE_2 = Foerderstufe("Stufe 2", min_savings=100.0, max_hwb_factor=1.30)
STUFE_3 = Foerderstufe("Stufe 3", min_savings=130.0, max_hwb_factor=1.15)
STUFE_4 = Foerderstufe("Stufe 4", min_savings=0.0,   max_hwb_factor=1.00)
STUFE_5 = Foerderstufe("Stufe 5", min_savings=0.0,   max_hwb_factor=1.00)

ORDER = [STUFE_0, STUFE_1, STUFE_2, STUFE_3, STUFE_4, STUFE_5]


# =====================================================================
# 3) Einsparpfad (NUR Stufe 0–3)
# =====================================================================

def _stage_by_savings(hwb_old: float, hwb_new: float) -> Optional[Foerderstufe]:
    savings = hwb_old - hwb_new

    if savings >= STUFE_3.min_savings:
        return STUFE_3
    if savings >= STUFE_2.min_savings:
        return STUFE_2
    if savings >= STUFE_1.min_savings:
        return STUFE_1
    if savings >= STUFE_0.min_savings:
        return STUFE_0

    return None


# =====================================================================
# 4) Zielwertpfad (HWB-nstEG-basiert)
# =====================================================================

def _stage_by_target(hwb_new: float, hwb_nsteg: float) -> Optional[Foerderstufe]:
    # Stufe 4: absoluter Grenzwert
    if hwb_new <= hwb_nsteg:
        return STUFE_4

    # Stufe 3–1: relative Faktoren
    if hwb_new <= STUFE_3.max_hwb_factor * hwb_nsteg:
        return STUFE_3
    if hwb_new <= STUFE_2.max_hwb_factor * hwb_nsteg:
        return STUFE_2
    if hwb_new <= STUFE_1.max_hwb_factor * hwb_nsteg:
        return STUFE_1

    return None


# =====================================================================
# 5) Zentrale Förderlogik
# =====================================================================

def determine_foerderstufe(
    hwb_old: float,
    hwb_new: float,
    hwb_nsteg: float,
    extra_measures: bool = False
) -> Optional[Foerderstufe]:
    """
    Bestimmt die höchste zulässige Förderstufe gemäß WWFSG.
    """

    stage_s = _stage_by_savings(hwb_old, hwb_new)
    stage_t = _stage_by_target(hwb_new, hwb_nsteg)

    candidates = [s for s in (stage_s, stage_t) if s is not None]
    if not candidates:
        return None

    best = max(candidates, key=lambda s: ORDER.index(s))

    # Stufe 5 nur als Bonus auf Stufe 4
    if best == STUFE_4 and extra_measures:
        return STUFE_5

    return best

# =====================================================================
# 5) Optionaler Selbsttest
# =====================================================================

if __name__ == "__main__":
    print("=== Test: policy/wwfsg_logic.py ===")

    stage = determine_foerderstufe(
        hwb_old=180.0,
        hwb_new=90.0,
        hwb_nsteg=27.24,
        extra_measures=True
    )

    print(stage)