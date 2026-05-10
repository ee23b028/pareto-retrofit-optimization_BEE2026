"""
economics/capex_blocks.py

CAPEX-Bausteine (Investitionskosten) für das Sanierungs-Optimierungsmodell.

Abgebildet werden:
- Dämmmaßnahmen (Volumenansatz)
- Fenstertausch (€/Fenster)
- Heizsysteme (leistungsabhängig, €/kW) inkl. Fernwärme (fix + variabel)
- Lüftungssysteme (€/m² Bezugsfläche)
- Nachtabsenkung (pauschal)
- Summierung zu CAPEX_brutto
- CAPEX_eff nach Abzug der Förderung

ABGRENZUNG:
- Keine Förderlogik (nur CAPEX_eff = CAPEX_brutto - Zuschuss).
- Keine Lebenszykluskosten (NPV) -> eigenes Modul.
- Keine Emissionen -> eigene Module.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


# =====================================================================
# 1) Datencontainer für transparentes Debugging (optional)
# =====================================================================

@dataclass(frozen=True)
class CapexBreakdown:
    """
    Container für CAPEX-Komponenten (hilft bei Export und Plausibilitätschecks).
    Alle Werte in [€].
    """
    wall: float = 0.0
    roof: float = 0.0
    floor: float = 0.0
    windows: float = 0.0
    heating_system: float = 0.0
    ventilation: float = 0.0
    night_reduction: float = 0.0

    def total(self) -> float:
        # Kritische Zeile: zentrale Summierung (einheitliche Quelle für Gesamt-CAPEX)
        return float(
            self.wall + self.roof + self.floor +
            self.windows + self.heating_system +
            self.ventilation + self.night_reduction
        )


# =====================================================================
# 2) CAPEX – Dämmung (Volumenansatz)
# =====================================================================


def capex_insulation_affine(
    area_m2: float,
    thickness_m: float,
    cost_per_cm_m2: float,
    fixed_cost_m2: float
) -> float:
    """
    Affiner Kostenansatz für Dämmung:
    CAPEX = A * (k + d * x)
    """
    thickness_cm = thickness_m * 100.0
    return area_m2 * (
        fixed_cost_m2 + cost_per_cm_m2 * thickness_cm
    )




# =====================================================================
# 3) CAPEX – Fenster (€/Fenster)
# =====================================================================

def capex_windows_per_unit(
    n_windows: int,
    cost_per_window: float
) -> float:
    """
    CAPEX Fenster als Kostenblock pro Fenster:
    CAPEX = Anzahl * Kosten je Fenster

    Parameter:
    - n_windows        : Anzahl Fenster [-]
    - cost_per_window  : Kosten je Fenster [€/Fenster]

    Rückgabe:
    - Investitionskosten [€]
    """

    if n_windows < 0:
        raise ValueError("n_windows darf nicht negativ sein.")
    if cost_per_window < 0:
        raise ValueError("cost_per_window darf nicht negativ sein.")

    capex = float(n_windows) * float(cost_per_window)
    return float(capex)


# =====================================================================
# 4) CAPEX – Heizsysteme (leistungsabhängig)
# =====================================================================

def capex_heating_system_variable(
    heating_load_kw: float,
    cost_per_kw: float
) -> float:
    """
    CAPEX eines Heizsystems proportional zur Heizlast:
    CAPEX = Heizlast [kW] * spezifische Kosten [€/kW]

    Parameter:
    - heating_load_kw : Heizlast (Vorbemessung) [kW]
    - cost_per_kw     : spezifische Kosten [€/kW]

    Rückgabe:
    - Investitionskosten [€]
    """

    if heating_load_kw < 0:
        raise ValueError("heating_load_kw darf nicht negativ sein.")
    if cost_per_kw < 0:
        raise ValueError("cost_per_kw darf nicht negativ sein.")

    capex = heating_load_kw * cost_per_kw
    return float(capex)


def capex_district_heating(
    heating_load_kw: float,
    fixed_cost: float,
    cost_per_kw: float
) -> float:
    """
    CAPEX Fernwärme als Kombination aus fixem und leistungsabhängigem Anteil:
    CAPEX_FW = CAPEX_fix + (Heizlast [kW] * €/kW)

    Parameter:
    - heating_load_kw : Heizlast (Vorbemessung) [kW]
    - fixed_cost      : fixer Anteil [€]
    - cost_per_kw     : variabler Anteil [€/kW]

    Rückgabe:
    - Investitionskosten [€]
    """

    if fixed_cost < 0:
        raise ValueError("fixed_cost darf nicht negativ sein.")
    # heating_load_kw / cost_per_kw werden in capex_heating_system_variable geprüft

    capex_var = capex_heating_system_variable(heating_load_kw, cost_per_kw)
    capex_total = float(fixed_cost) + capex_var
    return float(capex_total)


def capex_heating_system_from_index(
    system_idx: int,
    heating_load_kw: float,
    capex_gas_fixed: float,
    capex_fw_fixed: float,
    capex_fw_per_kw: float,
    capex_per_kw_wp: Dict[int, float]
) -> float:
    """
    Convenience-Funktion: Heizsystem-CAPEX über einen Systemindex.

    Erwartete Indexlogik (konsistent zu deinem bisherigen Modell):
    - 0 = Gas (Bestand) -> fixer Block (typisch 0 €)
    - 1 = Fernwärme     -> fix + variabel
    - 2..4 = Wärmepumpen -> variabel (€/kW), Kostensatz aus capex_per_kw_wp

    Parameter:
    - system_idx       : Systemindex [-]
    - heating_load_kw  : Heizlast (Vorbemessung) [kW]
    - capex_gas_fixed  : fixer CAPEX für Gas [€]
    - capex_fw_fixed   : fixer CAPEX für Fernwärme [€]
    - capex_fw_per_kw  : variabler CAPEX für Fernwärme [€/kW]
    - capex_per_kw_wp  : Mapping {idx: €/kW} für WP-Systeme

    Rückgabe:
    - Investitionskosten [€]
    """

    if system_idx == 0:
        if capex_gas_fixed < 0:
            raise ValueError("capex_gas_fixed darf nicht negativ sein.")
        return float(capex_gas_fixed)

    if system_idx == 1:
        return capex_district_heating(
            heating_load_kw=heating_load_kw,
            fixed_cost=capex_fw_fixed,
            cost_per_kw=capex_fw_per_kw
        )

    # WP oder andere Systeme: vollständig leistungsabhängig
    if system_idx not in capex_per_kw_wp:
        raise KeyError(f"Kein €/kW-Kostensatz für system_idx={system_idx} in capex_per_kw_wp definiert.")

    return capex_heating_system_variable(
        heating_load_kw=heating_load_kw,
        cost_per_kw=float(capex_per_kw_wp[system_idx])
    )


# =====================================================================
# 5) CAPEX – Lüftung (€/m² Bezugsfläche)
# =====================================================================

def capex_ventilation_per_area(
    reference_area_m2: float,
    cost_per_m2: float
) -> float:
    """
    CAPEX Lüftung als flächenbezogener Ansatz:
    CAPEX = A_ref [m²] * c [€/m²]

    Parameter:
    - reference_area_m2 : Bezugsfläche (z.B. WNF) [m²]
    - cost_per_m2       : spezifische Kosten [€/m²]

    Rückgabe:
    - Investitionskosten [€]
    """

    if reference_area_m2 < 0:
        raise ValueError("reference_area_m2 darf nicht negativ sein.")
    if cost_per_m2 < 0:
        raise ValueError("cost_per_m2 darf nicht negativ sein.")

    capex = reference_area_m2 * cost_per_m2
    return float(capex)


# =====================================================================
# 6) CAPEX – Nachtabsenkung (pauschal)
# =====================================================================

def capex_night_reduction(
    fixed_cost: float,
    is_active: bool
) -> float:
    """
    Nachtabsenkung als pauschaler CAPEX-Block:
    - aktiv -> fixed_cost
    - inaktiv -> 0

    Parameter:
    - fixed_cost : Pauschalkosten [€]
    - is_active  : bool

    Rückgabe:
    - Investitionskosten [€]
    """

    if fixed_cost < 0:
        raise ValueError("fixed_cost darf nicht negativ sein.")

    return float(fixed_cost) if is_active else 0.0


# =====================================================================
# 7) CAPEX Summierung und effektiver CAPEX
# =====================================================================

def capex_total_from_components(components: List[float]) -> float:
    """
    Summiert CAPEX-Komponenten zu CAPEX_brutto.

    Parameter:
    - components: Liste von Kostenanteilen [€]

    Rückgabe:
    - CAPEX_brutto [€]
    """
    return float(sum(float(c) for c in components))


def capex_effective(
    capex_brutto: float,
    subsidy_eur: float,
    clamp_to_zero: bool = True
) -> float:
    """
    Effektive Investitionskosten nach Abzug der Förderung:
    CAPEX_eff = CAPEX_brutto - subsidy

    Parameter:
    - capex_brutto   : Bruttoinvestition [€]
    - subsidy_eur    : Zuschuss [€]
    - clamp_to_zero  : verhindert negative CAPEX_eff

    Rückgabe:
    - CAPEX_eff [€]
    """

    if capex_brutto < 0:
        raise ValueError("capex_brutto darf nicht negativ sein.")
    if subsidy_eur < 0:
        raise ValueError("subsidy_eur darf nicht negativ sein.")

    capex_eff = float(capex_brutto) - float(subsidy_eur)

    # Kritische Zeile: Schutz gegen negative effektive Investition
    if clamp_to_zero:
        capex_eff = max(0.0, capex_eff)

    return float(capex_eff)


# =====================================================================
# 8) Optionaler Selbsttest (nur bei direktem Aufruf)
# =====================================================================

if __name__ == "__main__":
    print("=== Test: economics/capex_blocks.py ===")

    # Beispielhafte Plausibilitätschecks (keine Projektwerte)
    cap_wall = capex_insulation_affine(382, 20, 100, 10)
    cap_win = capex_windows_per_unit(10, 1500.0)

    cap_sys = capex_heating_system_from_index(
        system_idx=1,
        heating_load_kw=20.0,
        capex_gas_fixed=0.0,
        capex_fw_fixed=20000.0,
        capex_fw_per_kw=400.0,
        capex_per_kw_wp={2: 1800.0, 3: 2200.0, 4: 2400.0}
    )

    cap_total = capex_total_from_components([cap_wall, cap_win, cap_sys])
    cap_eff = capex_effective(cap_total, subsidy_eur=5000.0)

    print(f"CAPEX_brutto: {cap_total:.2f} €")
    print(f"CAPEX_eff:    {cap_eff:.2f} €")