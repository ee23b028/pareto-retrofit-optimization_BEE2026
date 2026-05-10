"""
ecology/operational.py

Betriebliche CO₂-Emissionen (Operational Carbon) des Gebäudes.

Abgebildet werden:
- CO₂-Emissionen aus Endenergieverbräuchen im Betrieb
  (z. B. Raumheizung, Hilfsenergie Strom)
- lineare Aufsummierung über den Betrachtungszeitraum

WICHTIGE ABGRENZUNG:
- Keine grauen Emissionen (-> ecology/embodied.py)
- Keine Kosten (-> economics/*)
- Keine System- oder Gebäudephysik
- Keine zeitliche Dekarbonisierung (konstante Emissionsfaktoren)
"""

from typing import Dict


# =====================================================================
# 1) CO₂-Emissionen aus Endenergie (jährlich)
# =====================================================================

def calc_co2_operational_annual(
    Q_end_energy: float,
    emission_factor: float
) -> float:
    """
    Berechnet die jährlichen betrieblichen CO₂-Emissionen.

    Formel:
    CO₂_annual = Q_end * EF

    Parameter:
    - Q_end_energy    : Endenergieverbrauch [kWh/a]
                         (z. B. Heizung, Strom)
    - emission_factor : Emissionsfaktor [kgCO₂/kWh]

    Rückgabe:
    - jährliche CO₂-Emissionen [kgCO₂/a]

    Wissenschaftliche Grundlage:
    - EN 15804 (Modul B6)
    - ISO 14067
    """

    if Q_end_energy < 0:
        raise ValueError("Q_end_energy darf nicht negativ sein.")
    if emission_factor < 0:
        raise ValueError("emission_factor darf nicht negativ sein.")

    # Kritische Zeile:
    # Lineare Verknüpfung von Energie und Emissionsfaktor
    co2_annual = Q_end_energy * emission_factor

    return float(co2_annual)


# =====================================================================
# 2) CO₂-Emissionen über den Betrachtungszeitraum
# =====================================================================

def calc_co2_operational_total(
    Q_end_energy: float,
    emission_factor: float,
    lifetime: int
) -> float:
    """
    Berechnet die gesamten betrieblichen CO₂-Emissionen
    über den Betrachtungszeitraum.

    Formel:
    CO₂_total = CO₂_annual * T

    Parameter:
    - Q_end_energy    : Endenergieverbrauch [kWh/a]
    - emission_factor : Emissionsfaktor [kgCO₂/kWh]
    - lifetime        : Betrachtungszeitraum [a]

    Rückgabe:
    - gesamte betriebliche CO₂-Emissionen [kgCO₂]

    Methodische Annahmen:
    - konstante Endenergie pro Jahr
    - konstante Emissionsfaktoren
    - keine zeitliche Dekarbonisierung

    Wissenschaftliche Einordnung:
    - zulässig für Variantenvergleiche
      (Asadi et al., 2012; Evins, 2013)
    """

    if lifetime < 0:
        raise ValueError("lifetime darf nicht negativ sein.")

    # Jährliche Emissionen
    co2_annual = calc_co2_operational_annual(
        Q_end_energy=Q_end_energy,
        emission_factor=emission_factor
    )

    co2_total = co2_annual * float(lifetime)

    return float(co2_total)


# =====================================================================
# 3) Convenience: mehrere Energieträger aggregieren
# =====================================================================

def calc_co2_operational_multi(
    energy_flows: Dict[str, Dict[str, float]],
    lifetime: int
) -> Dict[str, float]:
    """
    Aggregiert betriebliche CO₂-Emissionen mehrerer Energieträger.

    Parameter:
    - energy_flows : Dictionary mit Energiemengen und Emissionsfaktoren
    - lifetime     : Betrachtungszeitraum [a]

    Rückgabe:
    - Dictionary mit:
        * CO2_<name>_annual
        * CO2_<name>_total
        * CO2_operational_total
    """

    results: Dict[str, float] = {}
    co2_sum = 0.0

    for name, data in energy_flows.items():
        Q = float(data["Q"])
        EF = float(data["EF"])

        co2_annual = calc_co2_operational_annual(Q, EF)
        co2_total = co2_annual * float(lifetime)

        results[f"CO2_{name}_annual"] = float(co2_annual)
        results[f"CO2_{name}_total"] = float(co2_total)

        co2_sum += co2_total

    # Kritische Zeile:
    # Gesamte betriebliche Emissionen (alle Energieträger)
    results["CO2_operational_total"] = float(co2_sum)

    return results


# =====================================================================
# 4) Optionaler Selbsttest (nur bei direktem Aufruf)
# =====================================================================

if __name__ == "__main__":
    print("=== Test: ecology/operational.py ===")

    flows = {
        "heating": {"Q": 20000.0, "EF": 0.25},
        "electricity": {"Q": 1200.0, "EF": 0.23},
    }

    out = calc_co2_operational_multi(flows, lifetime=30)
    print(out)