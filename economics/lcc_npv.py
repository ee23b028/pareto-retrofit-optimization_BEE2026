"""
economics/lcc_npv.py

Lebenszykluskosten (LCC) als Nettobarwert (Net Present Value, NPV)
auf Basis konstanter jährlicher Kosten.

Normative Grundlage:
- ISO 15686-5:2017
  "Buildings and constructed assets – Service life planning – Part 5: Life-cycle costing"

Modellannahmen (bewusst vereinfacht, wissenschaftlich zulässig):
- konstante jährliche Betriebskosten (€/a)
- konstanter Diskontsatz r
- keine Preissteigerungen / Inflationsmodelle
- keine Restwerte am Ende des Betrachtungszeitraums

ABGRENZUNG:
- Keine Ermittlung jährlicher Kosten (-> economics/annual_costs.py)
- Keine Investitionskosten-Berechnung (-> economics/capex_blocks.py)
- Keine Förderlogik (CAPEX_eff wird als Eingangswert übergeben)
"""

from typing import Optional


# =====================================================================
# 1) NPV-Berechnung für konstante Jahreskosten
# =====================================================================

def lcc_from_annual_cost(
    capex_effective: float,
    annual_cost_eur: float,
    lifetime: int,
    discount_rate: float,
    annual_extra_cost_eur: float = 0.0,
    clamp_nonnegative: bool = True
) -> float:
    """
    Berechnet die Lebenszykluskosten (LCC) als Nettobarwert (NPV).

    Mathematische Definition (ISO 15686-5, sinngemäß):
    LCC = CAPEX_eff + Sum_{t=1..T} ( (C_ann + C_extra) / (1 + r)^t )

    Parameter:
    - capex_effective        : effektive Anfangsinvestition (nach Förderung) [€]
    - annual_cost_eur        : konstante jährliche Betriebskosten [€/a]
    - lifetime               : Betrachtungszeitraum T [a]
    - discount_rate          : Diskontsatz r [-]
    - annual_extra_cost_eur  : optionale zusätzliche jährliche Kosten [€/a]
    - clamp_nonnegative      : Schutz gegen negative LCC-Werte (numerisch)

    Rückgabe:
    - Lebenszykluskosten als Barwert [€]

    """

    # -------------------------------------------------------------
    # A) Robustheit / Eingangsprüfung
    # -------------------------------------------------------------
    if capex_effective < 0:
        raise ValueError("capex_effective darf nicht negativ sein.")
    if annual_cost_eur < 0:
        raise ValueError("annual_cost_eur darf nicht negativ sein.")
    if annual_extra_cost_eur < 0:
        raise ValueError("annual_extra_cost_eur darf nicht negativ sein.")

    # Betrachtungszeitraum als ganze Zahl (NPV-Summe über Jahre)
    T = int(max(0, lifetime))

    # Diskontsatz r muss > -1 sein, sonst ist (1+r)^t nicht definiert
    r = float(discount_rate)
    if r <= -0.999999:
        raise ValueError("discount_rate muss größer als -1 sein.")

    # -------------------------------------------------------------
    # B) Jährliche Gesamtkosten (OPEX)
    # -------------------------------------------------------------

    annual_total_cost = float(annual_cost_eur) + float(annual_extra_cost_eur)

    # -------------------------------------------------------------
    # C) Diskontierte Summe der jährlichen Kosten (NPV)
    # -------------------------------------------------------------
    npv_opex = 0.0

    for t in range(1, T + 1):

        # Diskontfaktor nach klassischer NPV-Formel
        discount_factor = (1.0 + r) ** t

        # Diskontierter Kostenanteil für Jahr t
        npv_opex += annual_total_cost / discount_factor

    # -------------------------------------------------------------
    # D) Lebenszykluskosten (LCC)
    # -------------------------------------------------------------

    # CAPEX_eff + diskontierte Betriebskosten
    lcc = float(capex_effective) + npv_opex

    # Optionaler Schutz gegen numerisch negative Ergebnisse
    if clamp_nonnegative:
        lcc = max(0.0, lcc)

    return float(lcc)


# =====================================================================
# 2) Optionaler Selbsttest (nur bei direktem Aufruf)
# =====================================================================

if __name__ == "__main__":
    print("=== Test: economics/lcc_npv.py ===")

    # Beispielwerte (nur Plausibilitätscheck, keine Projektwerte)
    lcc = lcc_from_annual_cost(
        capex_effective=100000.0,
        annual_cost_eur=3000.0,
        lifetime=30,
        discount_rate=0.03
    )

    print(f"LCC (NPV): {lcc:,.2f} €")