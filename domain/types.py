"""
domain/types.py

Zentrale Definition von Datentypen (Dataclasses) für das Optimierungsmodell.

Dieses Modul enthält:
- strukturierte Rückgabeformate (z. B. Evaluator-Ergebnisse)
- keine Modelllogik
- keine Berechnungen
- keine normativen Annahmen

Zweck:
- klare, explizite Schnittstellen zwischen Modulen
- verbesserte Lesbarkeit und Wartbarkeit
- saubere Trennung von Datenstruktur und Rechenlogik
"""

from dataclasses import dataclass
from typing import Dict, Any


# =====================================================================
# 1) Ergebniscontainer der Modellbewertung
# =====================================================================

@dataclass(frozen=True)
class EvalResult:
    """
    Container für die Bewertung einer einzelnen Lösung x.

    Enthält:
    - die Zielfunktionswerte (alle zu minimieren)
    - optionale Debug-Informationen für Validierung und Analyse

    WICHTIG:
    - Diese Dataclass enthält KEINE Logik.
    - Sie dient ausschließlich dem strukturierten Datentransfer.
    """

    # -------------------------------------------------------------
    # Zielfunktionen (Minimierung)
    # -------------------------------------------------------------
    capex_brutto: float  # Brutto-Investitionskosten [€]
    capex_eff: float     # effektive Investitionskosten [€]
    subsidy_stage: int  # Förderstufe (0, 1, 2, 3, 4, 5)
    q_new_total: float   # Heizwärmebedarf (Nutzenergie) [kWh/a]
    lcc: float           # Lebenszykluskosten (NPV) [€]
    co2_total: float    # gesamte CO₂-Emissionen [kg]

    # -------------------------------------------------------------
    # Optionale Zusatzinformationen (nicht Teil der Optimierung)
    # -------------------------------------------------------------
    debug: Dict[str, Any]
    """
    Debug-Container für Zwischenergebnisse, z.B.:
    - Q_tr_sum
    - Q_vent
    - Q_other
    - heating_load_kw
    - capex_brutto
    - subsidy_eur

    Nutzung:
    - Validierung
    - Plausibilitätschecks
    - Export zusätzlicher Informationen für Analyse und Visualisierung

    Hinweis:
    - Der Optimierungsalgorithmus (pymoo) greift NICHT auf dieses Feld zu.
    """