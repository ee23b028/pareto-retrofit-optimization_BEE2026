"""
ecology/embodied.py

Graue CO₂-Emissionen (Embodied Carbon) von Dämmmaßnahmen.

Abgebildet werden:
- Graue Emissionen der Dämmstoffe über einen Volumenansatz
- Emissionsfaktoren gemäß Umweltproduktdeklarationen (EPD)

WICHTIGE ABGRENZUNG:
- Es werden ausschließlich Dämmstoffe berücksichtigt.
"""

from typing import Dict


# =====================================================================
# 1) Graue Emissionen eines Dämmbauteils (Volumenansatz)
# =====================================================================

def calc_co2_embodied_insulation(
    area_m2: float,
    thickness_m: float,
    emission_factor_kg_per_m3: float
) -> float:
    """
    Berechnet die grauen CO₂-Emissionen einer Dämmmaßnahme.

    Methodik:
    - Volumenansatz gemäß EN 15804 (A1–A3)
    - V = A * d
    - CO₂_emb = V * EF

    Parameter:
    - area_m2                   : gedämmte Fläche [m²]
    - thickness_m               : Dämmstärke [m]
    - emission_factor_kg_per_m3 : materialabhängiger EPD-Faktor [kgCO₂/m³]

    Rückgabe:
    - Graue CO₂-Emissionen [kgCO₂]

    Wissenschaftliche Grundlage:
    - EN 15804:2022 (Module A1-A3)
    - EN 15978:2011
    """

    # -------------------------------------------------------------
    # A) Robustheit / Eingangsprüfung
    # -------------------------------------------------------------
    if area_m2 < 0:
        raise ValueError("area_m2 darf nicht negativ sein.")
    if thickness_m < 0:
        raise ValueError("thickness_m darf nicht negativ sein.")
    

    # -------------------------------------------------------------
    # B) Dämmvolumen
    # -------------------------------------------------------------

    volume_m3 = area_m2 * thickness_m

    # -------------------------------------------------------------
    # C) Graue Emissionen
    # -------------------------------------------------------------
    co2_embodied = volume_m3 * emission_factor_kg_per_m3

    return float(co2_embodied)


# =====================================================================
# 2) Aggregation: mehrere Dämmbauteile
# =====================================================================

def calc_co2_embodied_total(
    insulation_elements: Dict[str, Dict[str, float]]
) -> Dict[str, float]:
    """
    Aggregiert graue CO₂-Emissionen mehrerer Dämmbauteile.
    Parameter:
    - insulation_elements : Dictionary mit Geometrie- und Materialdaten

    Rückgabe:
    - Dictionary mit:
        * CO2_<name>_embodied
        * CO2_embodied_total
    """

    results: Dict[str, float] = {}
    co2_sum = 0.0

    for name, data in insulation_elements.items():
        A = float(data["A"])
        d = float(data["d"])
        EF = float(data["EF"])

        co2_elem = calc_co2_embodied_insulation(
            area_m2=A,
            thickness_m=d,
            emission_factor_kg_per_m3=EF
        )

        results[f"CO2_{name}_embodied"] = float(co2_elem)
        co2_sum += co2_elem
    
    # >>> ZENTRALER SCHUTZ: keine negativen Gesamtemissionen <<<
    co2_sum = max(0.0, co2_sum)

    results["CO2_embodied_total"] = float(co2_sum)

    return results


# =====================================================================
# 3) Optionaler Selbsttest (nur bei direktem Aufruf)
# =====================================================================

if __name__ == "__main__":
    print("=== Test: ecology/embodied.py ===")

    elems = {
        "wall":  {"A": 300.0, "d": 0.20, "EF": 8.0},
        "roof":  {"A": 90.0,  "d": 0.25, "EF": 7.5},
        "floor": {"A": 160.0, "d": 0.15, "EF": 9.0},
    }

    out = calc_co2_embodied_total(elems)
    print(out)