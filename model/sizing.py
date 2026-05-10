"""
model/sizing.py

Vereinfachte Vorbemessung / Dimensionierung auf Systemebene.

Abgebildet wird:
- Heizlastabschätzung aus Jahres-Heizwärmebedarf (Nutzenergie) über Vollaststunden.

ABGRENZUNG (sehr wichtig):
- KEINE normgerechte Heizlastberechnung nach EN 12831.
- Dient ausschließlich zur vergleichenden Dimensionierung von Anlagen
  (z.B. €/kW-Ansätze für CAPEX) im Optimierungsmodell.
- Keine Gebäudephysik (U, HGT, Lüftung) und keine Systemwirkungsgrade.

Methodische Einordnung:
- Vereinfachte Heizlastabschätzung über Jahresenergie / Vollaststunden.
"""

from typing import Dict


# =====================================================================
# 1) Heizlast aus Jahres-Heizwärmebedarf und Vollaststunden
# =====================================================================

def calc_heating_load_approx(
    Q_heat_demand: float,
    full_load_hours: float,
    min_heating_load_kw: float = 0.0,
    max_heating_load_kw: float = 1e9
) -> float:
    """
    Schätzt die Heizlast aus dem Jahres-Heizwärmebedarf ab.

    Formel:
    Φ_HL,appr. [kW] ≈ Q_heat_demand [kWh/a] / t_VL [h/a]

    Parameter:
    - Q_heat_demand       : Jahres-Heizwärmebedarf (Nutzenergie) [kWh/a]
    - full_load_hours     : angenommene Jahresvollaststunden [h/a]
    - min_heating_load_kw : Untergrenze zur Stabilisierung (z.B. CAPEX nicht 0) [kW]
    - max_heating_load_kw : optionale Obergrenze (Schutz gegen Ausreißer) [kW]

    Rückgabe:
    - Heizlastabschätzung [kW]
    """

    # -------------------------------------------------------------
    # A) Robustheit / Eingangsprüfung
    # -------------------------------------------------------------
    if full_load_hours <= 0:
        raise ValueError("full_load_hours muss > 0 sein.")

    # Negative Jahresbedarfe sind physikalisch nicht sinnvoll -> auf 0 begrenzen
    Q = max(0.0, float(Q_heat_demand))

    # -------------------------------------------------------------
    # B) Lineare Abschätzung
    # -------------------------------------------------------------
    # Kernannahme (Jahresenergie -> Leistung über Vollaststunden)
    heating_load_kw = Q / float(full_load_hours)

    # -------------------------------------------------------------
    # C) Begrenzung (Unter-/Obergrenze)
    # -------------------------------------------------------------
    # Untergrenze verhindert unrealistisch kleine Anlagen in €/kW-Modellen
    if min_heating_load_kw > 0:
        heating_load_kw = max(float(min_heating_load_kw), heating_load_kw)

    # Obergrenze als numerischer Schutz (optional)
    heating_load_kw = min(float(max_heating_load_kw), heating_load_kw)

    return float(heating_load_kw)


# =====================================================================
# 2) Convenience: Vorbemessung als Debug-Block (transparentes Output-Set)
# =====================================================================

def sizing_summary(
    Q_heat_demand: float,
    full_load_hours: float,
    min_heating_load_kw: float = 0.0
) -> Dict[str, float]:
    """
    Liefert eine kleine Zusammenfassung zur Nachvollziehbarkeit.

    Rückgabe:
    - Q_heat_demand      : [kWh/a]
    - full_load_hours    : [h/a]
    - heating_load_kw    : [kW]
    """

    hl = calc_heating_load_approx(
        Q_heat_demand=Q_heat_demand,
        full_load_hours=full_load_hours,
        min_heating_load_kw=min_heating_load_kw
    )

    return {
        "Q_heat_demand": float(max(0.0, Q_heat_demand)),
        "full_load_hours": float(full_load_hours),
        "heating_load_kw": float(hl),
    }


# =====================================================================
# 3) Optionaler Selbsttest (nur bei direktem Aufruf)
# =====================================================================

if __name__ == "__main__":
    print("=== Test: model/sizing.py ===")

    # Beispielwerte nur zur Plausibilitätsprüfung (keine Projektwerte)
    out = sizing_summary(Q_heat_demand=20000.0, full_load_hours=2000.0, min_heating_load_kw=1.0)
    print(out)