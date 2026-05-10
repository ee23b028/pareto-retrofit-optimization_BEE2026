"""
model/system_energy.py

Systemebene des Energiemodells.

Abgebildet werden:
- Umrechnung von Heizwärmebedarf (Nutzenergie) zu Endenergie
- Vereinfachte Heizlastabschätzung zur Systemdimensionierung
- Elektrische Hilfsenergie (z. B. Lüftungsstrom)

ABGRENZUNG (sehr wichtig):
- Keine Gebäudephysik (keine U-Werte, keine HGT-Bilanz).
- Keine normgerechte Heizlast nach EN 12831.
- Keine Kosten und keine Emissionsfaktoren.
- Keine zeitliche Auflösung (Jahreswerte).

"""

from typing import Dict


# =====================================================================
# 1) Umrechnung Nutzenergie -> Endenergie (Heizung)
# =====================================================================

def calc_end_energy_heating(
    Q_heat_demand: float,
    system_efficiency: float
) -> float:
    """
    Rechnet den Heizwärmebedarf (Nutzenergie) in Endenergie um.

    Formel:
    Q_end = Q_nutz / η_sys

    Parameter:
    - Q_heat_demand : Heizwärmebedarf (Nutzenergie) [kWh/a]
    - system_efficiency (η_sys):
        - Kesselwirkungsgrad (Gas)
        - Jahresnutzungsgrad (Fernwärme)
        - Jahresarbeitszahl (Wärmepumpe)

    Rückgabe:
    - Endenergie Heizung [kWh/a]

    """

    # Schutz gegen Division durch 0 oder negative Wirkungsgrade
    if system_efficiency <= 0:
        raise ValueError("system_efficiency muss > 0 sein.")

    # einfache, transparente Umrechnung
    Q_end = Q_heat_demand / system_efficiency

    return float(Q_end)


# =====================================================================
# 2) Vereinfachte Heizlastabschätzung (Vorbemessung)
# =====================================================================

def calc_heating_load_approx(
    Q_heat_demand: float,
    full_load_hours: float,
    min_heating_load_kw: float = 0.0
) -> float:
    """
    Schätzt die Heizlast aus dem Jahres-Heizwärmebedarf ab.

    Formel:
    Φ_HL ≈ Q_nutz / t_VL

    Parameter:
    - Q_heat_demand    : Jahres-Heizwärmebedarf (Nutzenergie) [kWh/a]
    - full_load_hours  : angenommene Jahresvollaststunden [h/a]
    - min_heating_load_kw : optionale Untergrenze [kW]

    Rückgabe:
    - Heizlast (Vorbemessung) [kW]

    """

    if full_load_hours <= 0:
        raise ValueError("full_load_hours muss > 0 sein.")

    # lineare Abschätzung aus Jahresenergie
    heating_load_kw = Q_heat_demand / full_load_hours

    # Optionale Untergrenze, um unrealistisch kleine Anlagen zu vermeiden
    if min_heating_load_kw > 0:
        heating_load_kw = max(min_heating_load_kw, heating_load_kw)

    return float(heating_load_kw)


# =====================================================================
# 3) Elektrische Hilfsenergie (z. B. Lüftung)
# =====================================================================

def calc_auxiliary_electric_energy(
    specific_el_energy: float,
    reference_area: float
) -> float:
    """
    Berechnet die jährliche elektrische Hilfsenergie.

    Typische Anwendung:
    - Ventilatorstrom von Abluft- oder KWL-Anlagen

    Formel:
    Q_el = e_spec * A_ref

    Parameter:
    - specific_el_energy : spezifischer Strombedarf [kWh/(m²*a)]
    - reference_area    : Bezugsfläche (z. B. WNF) [m²]

    Rückgabe:
    - Elektrische Hilfsenergie [kWh/a]

    """

    if reference_area < 0:
        raise ValueError("reference_area darf nicht negativ sein.")

    # Kritische Zeile: lineare Skalierung mit Fläche
    Q_el = specific_el_energy * reference_area

    return float(Q_el)


# =====================================================================
# 4) Convenience-Funktion: komplette Systemebene in einem Schritt
# =====================================================================

def calc_system_energy(
    Q_heat_demand: float,
    system_efficiency: float,
    full_load_hours: float,
    specific_aux_el: float,
    reference_area: float,
    min_heating_load_kw: float = 0.0
) -> Dict[str, float]:
    """
    Bündelt die Berechnung der Systemebene:

    - Heizlast (Vorbemessung)
    - Endenergie Heizung
    - Elektrische Hilfsenergie

    Rückgabe (Dictionary):
    - heating_load_kw : Heizlast (Vorbemessung) [kW]
    - Q_end_heating   : Endenergie Heizung [kWh/a]
    - Q_el_aux        : Elektrische Hilfsenergie [kWh/a]
    """

    heating_load_kw = calc_heating_load_approx(
        Q_heat_demand=Q_heat_demand,
        full_load_hours=full_load_hours,
        min_heating_load_kw=min_heating_load_kw
    )

    Q_end_heating = calc_end_energy_heating(
        Q_heat_demand=Q_heat_demand,
        system_efficiency=system_efficiency
    )

    Q_el_aux = calc_auxiliary_electric_energy(
        specific_el_energy=specific_aux_el,
        reference_area=reference_area
    )

    return {
        "heating_load_kw": float(heating_load_kw),
        "Q_end_heating": float(Q_end_heating),
        "Q_el_aux": float(Q_el_aux),
    }


# =====================================================================
# 5) Optionaler Selbsttest (nur bei direktem Aufruf)
# =====================================================================

if __name__ == "__main__":
    print("=== Test: model/system_energy.py ===")

    out = calc_system_energy(
        Q_heat_demand=20000.0,     # kWh/a
        system_efficiency=3.5,     # JAZ WP
        full_load_hours=2000.0,    # h/a
        specific_aux_el=3.0,       # kWh/(m²*a)
        reference_area=400.0,      # m²
        min_heating_load_kw=1.0    # kW
    )

    print(out)