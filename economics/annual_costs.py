"""
economics/annual_costs.py

Jährliche Betriebskosten (OPEX) als Jahreswerte [€/a].

Abgebildet werden:
- Heizkosten aus Endenergie Heizung (Q_end_heating) und Systempreis (€/kWh)
- Stromkosten aus Hilfsenergie (z.B. Lüftungsstrom, WP-Strom sofern separat geführt)
  und Strompreis (€/kWh)
- Aggregation zu gesamten jährlichen Energiekosten

ABGRENZUNG:
- Keine Diskontierung / NPV (-> economics/lcc_npv.py).
- Keine Investitionskosten (-> economics/capex_blocks.py).
- Keine Emissionsrechnung (-> ecology/*).
- Keine Umrechnung Nutzenergie -> Endenergie (-> model/system_energy.py).

Hinweis:
- Dieses Modul rechnet ausschließlich Kosten.
- Die Definition, welche Energiemengen in welchen Kostentopf fallen,
  erfolgt in der Orchestrierung (Evaluator), damit die Modelllogik transparent bleibt.
"""


from typing import Dict, Optional


# =====================================================================
# 1) Kostenblock: Heizenergie (Endenergie) zu Systempreis
# =====================================================================

def annual_cost_heating(
    Q_end_heating: float,
    price_heat_per_kwh: float
) -> float:
    """
    Berechnet die jährlichen Heizkosten [€/a] aus Endenergie Heizung.

    Parameter:
    - Q_end_heating      : Endenergie für Raumheizung [kWh/a]
    - price_heat_per_kwh : Preis des Energieträgers (Gas/FW/Strom) [€/kWh]

    Rückgabe:
    - jährliche Heizkosten [€/a]
    """

    if Q_end_heating < 0:
        raise ValueError("Q_end_heating darf nicht negativ sein.")
    if price_heat_per_kwh < 0:
        raise ValueError("price_heat_per_kwh darf nicht negativ sein.")

    # Kritische Zeile: lineare Kostenbildung (Jahresenergie * Preis)
    cost = Q_end_heating * price_heat_per_kwh
    return float(cost)


# =====================================================================
# 2) Kostenblock: Strom (Hilfsenergie) zu Strompreis
# =====================================================================

def annual_cost_electricity(
    Q_el: float,
    price_el_per_kwh: float
) -> float:
    """
    Berechnet die jährlichen Stromkosten [€/a].

    Typische Anwendung:
    - Lüftungsstrom (Ventilatoren)
    - weitere Hilfsenergien, die elektrisch abgebildet werden

    Parameter:
    - Q_el            : elektrische Energie [kWh/a]
    - price_el_per_kwh: Strompreis [€/kWh]

    Rückgabe:
    - jährliche Stromkosten [€/a]
    """

    if Q_el < 0:
        raise ValueError("Q_el darf nicht negativ sein.")
    if price_el_per_kwh < 0:
        raise ValueError("price_el_per_kwh darf nicht negativ sein.")

    # Kritische Zeile: lineare Kostenbildung (Jahresenergie * Preis)
    cost = Q_el * price_el_per_kwh
    return float(cost)


# =====================================================================
# 3) Aggregation: gesamte jährliche Energiekosten (Heizen + Strom)
# =====================================================================

def annual_energy_cost_total(
    Q_end_heating: float,
    price_heat_per_kwh: float,
    Q_el_aux: float,
    price_el_per_kwh: float
) -> Dict[str, float]:
    """
    Aggregiert Heizkosten und Stromkosten zu jährlichen Energiekosten.

    Parameter:
    - Q_end_heating      : Endenergie Heizung [kWh/a]
    - price_heat_per_kwh : Preis Wärmeträger [€/kWh]
    - Q_el_aux           : elektrische Hilfsenergie [kWh/a]
    - price_el_per_kwh   : Strompreis [€/kWh]

    Rückgabe (Dictionary):
    - cost_heat_eur_a : Heizkosten [€/a]
    - cost_el_eur_a   : Stromkosten [€/a]
    - cost_total_eur_a: Summe [€/a]
    """

    cost_heat = annual_cost_heating(Q_end_heating, price_heat_per_kwh)
    cost_el = annual_cost_electricity(Q_el_aux, price_el_per_kwh)

    # Kritische Zeile: Summierung der jährlichen Energiekosten
    total = cost_heat + cost_el

    return {
        "cost_heat_eur_a": float(cost_heat),
        "cost_el_eur_a": float(cost_el),
        "cost_total_eur_a": float(total),
    }


# =====================================================================
# 4) Optional: allgemeine Aggregation weiterer jährlicher Kosten
# =====================================================================

def annual_total_cost_with_extras(
    annual_energy_cost_eur_a: float,
    annual_extra_cost_eur_a: float = 0.0,
    clamp_nonnegative: bool = True
) -> float:
    """
    Addiert optionale weitere jährliche Kosten (Pauschalen) zu den Energiekosten.

    Parameter:
    - annual_energy_cost_eur_a : jährliche Energiekosten [€/a]
    - annual_extra_cost_eur_a  : weitere jährliche Kosten [€/a]
    - clamp_nonnegative        : verhindert negative Gesamtkosten (numerischer Schutz)

    Rückgabe:
    - gesamte jährliche Betriebskosten [€/a]
    """

    if annual_energy_cost_eur_a < 0:
        raise ValueError("annual_energy_cost_eur_a darf nicht negativ sein.")
    if annual_extra_cost_eur_a < 0:
        raise ValueError("annual_extra_cost_eur_a darf nicht negativ sein.")

    total = float(annual_energy_cost_eur_a) + float(annual_extra_cost_eur_a)

    # Optionaler Schutz gegen negative Gesamtkosten, z.B. durch unerwartete Eingaben
    if clamp_nonnegative:
        total = max(0.0, total)

    return float(total)


# =====================================================================
# 5) Optionaler Selbsttest (nur bei direktem Aufruf)
# =====================================================================

if __name__ == "__main__":
    print("=== Test: economics/annual_costs.py ===")

    out = annual_energy_cost_total(
        Q_end_heating=20000.0,
        price_heat_per_kwh=0.10,
        Q_el_aux=1200.0,
        price_el_per_kwh=0.20
    )
    print(out)

    total = annual_total_cost_with_extras(out["cost_total_eur_a"], annual_extra_cost_eur_a=0.0)
    print(f"Total annual cost: {total:.2f} €/a")