"""
policy/wwfsg_calc.py

Monetäre Bemessung der WWFSG-Förderung (Zuschuss) auf Basis einer Förderstufe.

Dieses Modul enthält ausschließlich:
- Berechnung des Zuschusses [€] aus:
  * Förderstufe
  * Zuschuss €/m²
  * förderrelevanter Fläche
  * Kappung als maximaler Anteil der förderfähigen Kosten

NICHT enthalten:
- keine Stufenlogik (-> policy/wwfsg_logic.py)
- keine Gebäudephysik / Energiemodell (-> model/*)
- keine Lebenszykluskosten (-> economics/lcc_npv.py)

Wichtige Architekturentscheidung:
- Logik (welche Stufe?) und Monetarisierung (wie viel €?) sind getrennt,
  damit spätere Anpassungen am Regelwerk oder an Beträgen isoliert möglich sind.
"""

from dataclasses import dataclass
from typing import Dict, Optional

from policy.wwfsg_logic import determine_foerderstufe


# =====================================================================
# 1) Datenstruktur: Monetarisierung je Stufe
# =====================================================================

@dataclass(frozen=True)
class GrantRule:
    """
    Monetäre Parameter einer Förderstufe.

    Attribute:
    - name                 : z.B. "Stufe 2"
    - grant_per_m2         : Zuschuss [€/m²] (förderrelevante Nutzfläche)
    - max_ratio_total_cost : max. Förderquote bezogen auf förderfähige Kosten [-]
    """
    name: str
    grant_per_m2: float
    max_ratio_total_cost: float


# =====================================================================
# 2) Kernfunktion: Zuschuss aus HWB-Werten berechnen
# =====================================================================

def calc_subsidy_wwfsg(
    hwb_old: float,
    hwb_new: float,
    hwb_nsteg: float,
    area_nf: float,
    capex_eligible: float,
    grant_rules: Dict[str, GrantRule],
    extra_measures: bool = False,
    clamp_nonnegative: bool = True
) -> Dict[str, float]:
    """
    Berechnet den WWFSG-Zuschuss als monetäre Bemessung der Förderstufe.

    Ablauf:
    1) Förderstufe über policy/wwfsg_logic.py bestimmen (ODER-Logik)
    2) Basiszuschuss = grant_per_m2 * area_nf
    3) Kappung: Zuschuss <= max_ratio_total_cost * capex_eligible
    4) Rückgabe strukturierter Ergebnisse

    Parameter:
    - hwb_old         : HWB Ausgangszustand [kWh/(m²*a)]
    - hwb_new         : HWB nach Sanierung [kWh/(m²*a)]
    - hwb_nsteg       : Referenzwert nstEG [kWh/(m²*a)] (Gebäudereferenz)
    - area_nf         : förderrelevante Nutzfläche [m²]
    - capex_eligible  : förderfähige Investitionskosten [€]
    - grant_rules     : Monetarisierung je Stufe (Dict: name -> GrantRule)
    - extra_measures  : Zusatzmaßnahmen (relevant für Stufe 5)
    - clamp_nonnegative: verhindert negative Ergebnisse (numerischer Schutz)

    Rückgabe (Dictionary):
    - stage_name        : Name der Stufe (oder "keine")
    - subsidy_eur       : Zuschuss gesamt [€]
    - subsidy_per_m2    : Zuschuss je m² [€/m²]
    - capped_by_ratio   : 1.0 wenn Kappung aktiv war, sonst 0.0
    """

    # -------------------------------------------------------------
    # A) Eingangsprüfung / Robustheit
    # -------------------------------------------------------------
    if area_nf < 0:
        raise ValueError("area_nf darf nicht negativ sein.")
    if capex_eligible < 0:
        raise ValueError("capex_eligible darf nicht negativ sein.")

    # -------------------------------------------------------------
    # B) Förderstufe bestimmen (Logik: ODER-Pfade + Sonderregel Stufe 5)
    # -------------------------------------------------------------
    stage = determine_foerderstufe(
        hwb_old=hwb_old,
        hwb_new=hwb_new,
        hwb_nsteg=hwb_nsteg,
        extra_measures=extra_measures
    )

    if stage is None:
        return {
            "stage_name": "keine",
            "subsidy_eur": 0.0,
            "subsidy_per_m2": 0.0,
            "capped_by_ratio": 0.0,
        }

    stage_name = stage.name

    # -------------------------------------------------------------
    # C) Monetäre Parameter zur Stufe auflösen
    # -------------------------------------------------------------
    if stage_name not in grant_rules:
        raise KeyError(f"GrantRule für '{stage_name}' fehlt in grant_rules.")

    rule = grant_rules[stage_name]

    if rule.grant_per_m2 < 0:
        raise ValueError("grant_per_m2 darf nicht negativ sein.")
    if rule.max_ratio_total_cost < 0:
        raise ValueError("max_ratio_total_cost darf nicht negativ sein.")

    # -------------------------------------------------------------
    # D) Zuschuss berechnen (Basis + Kappung)
    # -------------------------------------------------------------
    # Basiszuschuss: €/m² * Fläche
    subsidy_base = float(rule.grant_per_m2) * float(area_nf)

    # Kappung: max. Anteil der förderfähigen Kosten
    subsidy_cap = float(rule.max_ratio_total_cost) * float(capex_eligible)

    # tatsächlicher Zuschuss ist die kleinere Größe
    subsidy_final = min(subsidy_base, subsidy_cap)

    if clamp_nonnegative:
        subsidy_final = max(0.0, subsidy_final)

    capped = 1.0 if subsidy_final < subsidy_base else 0.0

    return {
        "stage_name": stage_name,
        "subsidy_eur": float(subsidy_final),
        "subsidy_per_m2": float(subsidy_final / area_nf) if area_nf > 0 else 0.0,
        "capped_by_ratio": float(capped),
    }


# =====================================================================
# 3) Wrapper: Zuschuss aus Energiekennwerten Q [kWh/a]
# =====================================================================

def calc_subsidy_wwfsg_from_energy(
    Q_old_total: float,
    Q_new_total: float,
    A_ref: float,
    hwb_nsteg: float,
    area_nf: float,
    capex_eligible: float,
    grant_rules: Dict[str, GrantRule],
    extra_measures: bool = False
) -> Dict[str, float]:
    """
    Wrapper, der Jahresenergiemengen [kWh/a] in spezifische HWB-Werte [kWh/(m²*a)]
    umrechnet und danach calc_subsidy_wwfsg() aufruft.

    Parameter:
    - Q_old_total : Jahresbedarf Ausgangszustand [kWh/a]
    - Q_new_total : Jahresbedarf nach Sanierung [kWh/a]
    - A_ref       : Bezugsfläche für HWB-Umrechnung [m²]
    - hwb_nsteg   : Referenzwert nstEG [kWh/(m²*a)]
    - area_nf     : förderrelevante Nutzfläche [m²]
    - capex_eligible: förderfähige Kosten [€]
    - grant_rules : Monetarisierung je Stufe
    - extra_measures: Zusatzmaßnahmen (Stufe 5)

    Hinweis:
    - A_ref und area_nf können identisch sein (z.B. WNF),
      werden aber bewusst getrennt geführt, um Modellabgrenzungen
      transparent zu halten.
    """

    if A_ref <= 0:
        raise ValueError("A_ref muss > 0 sein.")

    # Kritische Zeile: Umrechnung kWh/a -> kWh/(m²*a)
    hwb_old = float(Q_old_total) / float(A_ref)
    hwb_new = float(Q_new_total) / float(A_ref)

    return calc_subsidy_wwfsg(
        hwb_old=hwb_old,
        hwb_new=hwb_new,
        hwb_nsteg=hwb_nsteg,
        area_nf=area_nf,
        capex_eligible=capex_eligible,
        grant_rules=grant_rules,
        extra_measures=extra_measures
    )


# =====================================================================
# 4) Helper: GrantRules aus params erzeugen (optional)
# =====================================================================

def build_grant_rules_from_params(params: dict) -> Dict[str, GrantRule]:
    """
    Baut ein grant_rules-Dictionary aus einem Parameterobjekt.

    Erwartete Struktur im params (Beispiel):
    params["wwfsg"]["grants"] = {
        "Stufe 0": {"grant_per_m2": ..., "max_ratio_total_cost": ...},
        ...
    }
    """

    if "wwfsg" not in params or "grants" not in params["wwfsg"]:
        raise KeyError("params['wwfsg']['grants'] fehlt.")

    grants = params["wwfsg"]["grants"]
    rules: Dict[str, GrantRule] = {}

    for name, g in grants.items():
        rules[str(name)] = GrantRule(
            name=str(name),
            grant_per_m2=float(g["grant_per_m2"]),
            max_ratio_total_cost=float(g["max_ratio_total_cost"])
        )

    return rules


# =====================================================================
# 5) Optionaler Selbsttest (nur bei direktem Aufruf)
# =====================================================================

if __name__ == "__main__":
    print("=== Test: policy/wwfsg_calc.py ===")

    # Beispielhafte Parameter
    grant_rules = {
        "Stufe 0": GrantRule("Stufe 0", grant_per_m2=35.0, max_ratio_total_cost=0.20),
        "Stufe 1": GrantRule("Stufe 1", grant_per_m2=80.0, max_ratio_total_cost=0.25),
        "Stufe 2": GrantRule("Stufe 2", grant_per_m2=120.0, max_ratio_total_cost=0.30),
        "Stufe 3": GrantRule("Stufe 3", grant_per_m2=160.0, max_ratio_total_cost=0.35),
        "Stufe 4": GrantRule("Stufe 4", grant_per_m2=200.0, max_ratio_total_cost=0.40),
        "Stufe 5": GrantRule("Stufe 5", grant_per_m2=220.0, max_ratio_total_cost=0.40),
    }

    out = calc_subsidy_wwfsg(
        hwb_old=180.0,
        hwb_new=90.0,
        hwb_nsteg=27.24,
        area_nf=400.0,
        capex_eligible=150000.0,
        grant_rules=grant_rules,
        extra_measures=True
    )

    print(out)