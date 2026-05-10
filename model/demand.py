"""
model/demand.py

Bedarfsmodell (Gebäudeebene) für den jährlichen Heizwärmebedarf als Nutzenergie.

Dieses Modul kapselt ausschließlich:
- die Zusammenführung der Wärmeverlustanteile (Transmission + Lüftung)
- einen kalibrierten Restanteil Q_other (Konstante)
- die optionale Nachtabsenkung als pauschale Reduktion

ABGRENZUNG:
- Keine Endenergie (keine Systemwirkungsgrade).
- Keine Heizlast nach EN 12831 (nur Bedarf auf Jahresbasis).
- Keine Bauteilphysik (U-Werte, HGT-Formeln) -> gehört in eigene Module.

Bezug zur Arbeit:
- Q_new_total = Q_tr_sum + Q_vent + Q_other
- Nachtabsenkung als prozentuale Reduktion (bewusste Vereinfachung)
"""

from typing import Dict


# =====================================================================
# 1) Kalibrierung Restanteil Q_other (Konstante)
# =====================================================================

def calibrate_q_other(
    Q_old_total: float,
    Q_tr_sum_old: float,
    Q_vent_old: float,
    clamp_nonnegative: bool = True
) -> float:
    """
    Kalibriert einen konstanten Restanteil Q_other aus dem Ausgangszustand.

    Idee:
    - Das vereinfachte Jahresmodell bildet nicht alle Effekte explizit ab.
    - Q_other kompensiert diese Abweichung so, dass der Ausgangszustand
      reproduziert wird.

    Formel:
    Q_other = Q_old_total - (Q_tr_sum_old + Q_vent_old)

    Parameter:
    - Q_old_total  : Jahres-Heizwärmebedarf im Ausgangszustand [kWh/a]
    - Q_tr_sum_old : Summe Transmissionsverluste Ausgangszustand [kWh/a]
    - Q_vent_old   : Lüftungswärmeverlust Ausgangszustand [kWh/a]
    - clamp_nonnegative: Schutz, damit Q_other nicht negativ wird

    Rückgabe:
    - Q_other [kWh/a]
    """

    # Differenzbildung zur Kalibrierung
    Q_other = Q_old_total - (Q_tr_sum_old + Q_vent_old)

    # Optionaler Schutz:
    # Ein negativer Restterm würde bedeuten, dass das vereinfachte Modell
    # den Ausgangszustand "übererklärt". In diesem Fall wird auf 0 begrenzt.
    if clamp_nonnegative:
        Q_other = max(0.0, Q_other)

    return float(Q_other)


# =====================================================================
# 2) Nachtabsenkung als pauschale Reduktion
# =====================================================================

def apply_night_reduction(
    Q_total: float,
    night_active: bool,
    night_reduction_factor: float
) -> float:
    """
    Wendet eine pauschale Nachtabsenkung auf den Jahresbedarf an.

    Annahme:
    - Nachtabsenkung wird als prozentuale Reduktion des Jahresbedarfs modelliert.
    - Keine zeitaufgelöste Simulation (bewusste Vereinfachung).

    Parameter:
    - Q_total               : Jahresbedarf vor Nachtabsenkung [kWh/a]
    - night_active          : True/False
    - night_reduction_factor: Reduktionsfaktor r_night [-],

    Rückgabe:
    - Jahresbedarf nach Nachtabsenkung [kWh/a]
    """

    if not night_active:
        return float(Q_total)

    # Kritische Zeile: Multiplikative Reduktion
    return float(Q_total * (1.0 - night_reduction_factor))


# =====================================================================
# 3) Gesamtbedarf Q_new_total (Gebäudeebene, Nutzenergie)
# =====================================================================

def calc_q_new_total(
    Q_tr_sum: float,
    Q_vent: float,
    Q_other: float,
    night_active: bool = False,
    night_reduction_factor: float = 0.0
) -> Dict[str, float]:
    """
    Berechnet den jährlichen Heizwärmebedarf (Nutzenergie) auf Gebäudeebene.

    Zusammensetzung:
    Q_new_total = Q_tr_sum + Q_vent + Q_other
    optional: Nachtabsenkung -> pauschale Reduktion

    Parameter:
    - Q_tr_sum : Summe Transmissionsverluste [kWh/a]
    - Q_vent   : Lüftungswärmeverlust [kWh/a]
    - Q_other  : kalibrierter Restanteil [kWh/a]
    - night_active / night_reduction_factor : Nachtabsenkung

    Rückgabe (Dictionary):
    - Q_new_total : Gesamtbedarf [kWh/a]
    - Q_tr_sum    : Transmissionsanteil [kWh/a]
    - Q_vent      : Lüftungsanteil [kWh/a]
    - Q_other     : Restanteil [kWh/a]
    """

    # Basisbedarf ohne Nachtabsenkung
    Q_base = float(Q_tr_sum + Q_vent + Q_other)

    # Nachtabsenkung optional anwenden
    Q_final = apply_night_reduction(
        Q_total=Q_base,
        night_active=night_active,
        night_reduction_factor=night_reduction_factor
    )

    return {
        "Q_new_total": float(Q_final),
        "Q_tr_sum": float(Q_tr_sum),
        "Q_vent": float(Q_vent),
        "Q_other": float(Q_other),
    }


# =====================================================================
# 4) Hilfsfunktion: spezifischer Wert (z.B. HWB in kWh/(m²*a))
# =====================================================================

def specific_value(
    Q_annual: float,
    A_ref: float
) -> float:
    """
    Rechnet einen Jahreswert [kWh/a] in einen spezifischen Wert [kWh/(m²*a)] um.

    Parameter:
    - Q_annual: Jahresenergie [kWh/a]
    - A_ref   : Bezugsfläche [m²]

    Rückgabe:
    - spezifischer Wert [kWh/(m²*a)]
    """

    if A_ref <= 0:
        return 0.0

    # Kritische Zeile: Normierte Umrechnung
    return float(Q_annual / A_ref)


# =====================================================================
# 5) Optionaler Selbsttest (nur bei direktem Aufruf)
# =====================================================================

if __name__ == "__main__":
    print("=== Test: model/demand.py ===")

    # Beispielwerte (nur Plausibilitätstest, keine Projektwerte)
    Q_other = calibrate_q_other(Q_old_total=100000.0, Q_tr_sum_old=80000.0, Q_vent_old=15000.0)
    out = calc_q_new_total(Q_tr_sum=60000.0, Q_vent=12000.0, Q_other=Q_other,
                           night_active=True, night_reduction_factor=0.05)
    print(out)