"""
optimization/evaluator.py

Zentrale Orchestrierung des Gesamtmodells.

Dieses Modul:
- decodiert eine Lösung x (stetig + diskret)
- ruft die Fachmodule in definierter Reihenfolge auf
- liefert die Zielfunktionen als EvalResult zurück

WICHTIGE ABGRENZUNG:
- Der Evaluator enthält keine neue Modelllogik.
- Alle fachlichen Annahmen liegen in den jeweiligen Modulen

Optimierungstechnische Entscheidung:
- Q_other (Kalibrier-Restterm) wird einmalig aus dem Ausgangszustand ermittelt.
- GrantRules werden einmalig aus params aufgebaut.
"""

from dataclasses import dataclass
from typing import Dict

import numpy as np

from domain.types import EvalResult
from optimization.decision_space import decode_x

# -----------------------------
# Gebäudeebene
# -----------------------------
from model.envelope_u import calc_u_with_additional_insulation
from model.envelope_losses import calc_transmission_losses
from model.ventilation import calc_ventilation_losses
from model.demand import calibrate_q_other, calc_q_new_total

# -----------------------------
# Systemebene
# -----------------------------
from model.sizing import calc_heating_load_approx
from model.system_energy import (
    calc_end_energy_heating,
    calc_auxiliary_electric_energy
)

# -----------------------------
# Ökonomie
# -----------------------------
from economics.capex_blocks import (
    capex_insulation_affine,
    capex_windows_per_unit,
    capex_heating_system_from_index,
    capex_ventilation_per_area,
    capex_night_reduction,
    capex_total_from_components,
    capex_effective
)
from economics.annual_costs import annual_energy_cost_total
from economics.lcc_npv import lcc_from_annual_cost

# -----------------------------
# Ökologie
# -----------------------------
from ecology.operational import calc_co2_operational_multi
from ecology.embodied import calc_co2_embodied_total

# -----------------------------
# Förderung (Policy)
# -----------------------------
from policy.wwfsg_calc import (
    calc_subsidy_wwfsg_from_energy,
    build_grant_rules_from_params
)


# =====================================================================
# 1) Context: einmalige Vorberechnungen (Cache)
# =====================================================================

@dataclass(frozen=True)
class EvaluatorContext:
    """
    Enthält einmalig vorberechnete Größen, die für alle Individuen gleich sind.
    """
    Q_other: float
    grant_rules: Dict  # Dict[str, GrantRule] – Typ offen gelassen, um Imports minimal zu halten


def build_context(params: dict) -> EvaluatorContext:
    """
    Erstellt den EvaluatorContext aus params.

    Enthält:
    - Q_other: Kalibrierter Restterm, so dass Ausgangszustand reproduziert werden kann
    - grant_rules: Monetarisierung der Förderstufen aus params

    Hinweis:
    - Diese Funktion wird einmalig beim Modellstart aufgerufen.
    """

    # -------------------------------------------------------------
    # A) Ausgangszustand: Transmission alt
    # -------------------------------------------------------------
    transmission_old = calc_transmission_losses(
        components=[
            {"name": "wall",   "U": params["U_wall_old"],   "A": params["A_wall"]},
            {"name": "roof",   "U": params["U_roof_old"],   "A": params["A_roof"]},
            {"name": "floor",  "U": params["U_floor_old"],  "A": params["A_floor"]},
            {"name": "window", "U": params["U_window_old"], "A": params["A_window"]},
        ],
        HGT=params["HGT"]
    )
    Q_tr_sum_old = transmission_old["Q_tr_sum"]

    # -------------------------------------------------------------
    # B) Ausgangszustand: Lüftung alt
    # -------------------------------------------------------------
    ventilation_old = calc_ventilation_losses(
        L_v_base=params["L_v_old"],
        HGT=params["HGT"],
        ventilation_factor=1.0,
        heat_recovery_efficiency=0.0
    )
    Q_vent_old = ventilation_old["Q_vent"]

    # -------------------------------------------------------------
    # C) Kalibrierter Restterm Q_other
    # -------------------------------------------------------------
    Q_other = calibrate_q_other(
        Q_old_total=params["Q_old_total"],
        Q_tr_sum_old=Q_tr_sum_old,
        Q_vent_old=Q_vent_old,
        clamp_nonnegative=True
    )

    # -------------------------------------------------------------
    # D) Förderregeln (Monetarisierung) aus params
    # -------------------------------------------------------------
    grant_rules = build_grant_rules_from_params(params)

    return EvaluatorContext(Q_other=Q_other, grant_rules=grant_rules)


# =====================================================================
# 2) Evaluator als Objekt (sauber in RetrofitProblem injizierbar)
# =====================================================================

class ModelEvaluator:
    """
    Bewertet Lösungen x für gegebene params.
    Enthält einen Context mit konstanten Größen.
    """

    def __init__(self, params: dict):
        self.p = params
        self.ctx = build_context(params)

    def __call__(self, x: np.ndarray) -> EvalResult:
        return self.evaluate(x)

    def evaluate(self, x: np.ndarray) -> EvalResult:
        """
        Vollständige Bewertung einer Lösung x.
        """

        p = self.p
        ctx = self.ctx

        # ==========================================================
        # A) x dekodieren (diskrete Variablen round+clip)
        # ==========================================================
        dv = decode_x(x)

        # ==========================================================
        # B) Gebäudeebene: U-Werte neu
        # ==========================================================
        U_wall_new = calc_u_with_additional_insulation(
            U_existing=p["U_wall_old"],
            insulation_thickness=dv.d_wall,
            lambda_insulation=p["lambda_ins_wall"][dv.mat_wall]
        )
        U_roof_new = calc_u_with_additional_insulation(
            U_existing=p["U_roof_old"],
            insulation_thickness=dv.d_roof,
            lambda_insulation=p["lambda_ins_roof"][dv.mat_roof]
        )
        U_floor_new = calc_u_with_additional_insulation(
            U_existing=p["U_floor_old"],
            insulation_thickness=dv.d_floor,
            lambda_insulation=p["lambda_ins_floor"][dv.mat_floor]
        )
        U_window_new = p["U_window_levels"][dv.window_lvl]

        # ==========================================================
        # C) Gebäudeebene: Transmission neu
        # ==========================================================
        transmission = calc_transmission_losses(
            components=[
                {"name": "wall",   "U": U_wall_new,   "A": p["A_wall"]},
                {"name": "roof",   "U": U_roof_new,   "A": p["A_roof"]},
                {"name": "floor",  "U": U_floor_new,  "A": p["A_floor"]},
                {"name": "window", "U": U_window_new, "A": p["A_window"]},
            ],
            HGT=p["HGT"]
        )
        Q_tr_sum = transmission["Q_tr_sum"]

        # ==========================================================
        # D) Gebäudeebene: Lüftung neu
        # ==========================================================
        ventilation = calc_ventilation_losses(
            L_v_base=p["L_v_old"],
            HGT=p["HGT"],
            ventilation_factor=p["vent_factor"][dv.vent_level],
            heat_recovery_efficiency=p["vent_eta_wrg"][dv.vent_level]
        )
        Q_vent = ventilation["Q_vent"]

        # ==========================================================
        # E) Heizwärmebedarf (Nutzenergie) Q_new_total
        # ==========================================================
        demand = calc_q_new_total(
            Q_tr_sum=Q_tr_sum,
            Q_vent=Q_vent,
            Q_other=ctx.Q_other,
            night_active=(dv.night_flag == 1),
            night_reduction_factor=p["night_reduction_factor"]
        )
        Q_new_total = demand["Q_new_total"]

        # ==========================================================
        # F) Systemebene: Heizlast (Vorbemessung) + Endenergie + Hilfsstrom
        # ==========================================================
        heating_load_kw = calc_heating_load_approx(
            Q_heat_demand=Q_new_total,
            full_load_hours=p["full_load_hours"],
            min_heating_load_kw=p["min_heating_load_kw"]
        )

        Q_end_heat = calc_end_energy_heating(
            Q_heat_demand=Q_new_total,
            system_efficiency=p["system_eta"][dv.system_idx]
        )

        Q_el_aux = calc_auxiliary_electric_energy(
            specific_el_energy=p["vent_el_per_m2a"][dv.vent_level],
            reference_area=p["A_ref"]
        )

        # ==========================================================
        # G) Ökonomie: CAPEX brutto
        # ==========================================================
        cap_wall = capex_insulation_affine(
            area_m2=p["A_wall"],
            thickness_m=dv.d_wall,
            cost_per_cm_m2=p["c_ins_wall_per_cm_m2"][dv.mat_wall],
            fixed_cost_m2=p["c_ins_wall_fix_m2"]
        )
        cap_roof = capex_insulation_affine(
            area_m2=p["A_roof"],
            thickness_m=dv.d_roof,
            cost_per_cm_m2=p["c_ins_roof_per_cm_m2"][dv.mat_roof],
            fixed_cost_m2=p["c_ins_roof_fix_m2"]
        )
        cap_floor = capex_insulation_affine(
            area_m2=p["A_floor"],
            thickness_m=dv.d_floor,
            cost_per_cm_m2=p["c_ins_floor_per_cm_m2"][dv.mat_floor],
            fixed_cost_m2=p["c_ins_floor_fix_m2"]
        )

        cap_windows = capex_windows_per_unit(p["n_windows"], p["capex_per_window_levels"][dv.window_lvl])

        cap_system = capex_heating_system_from_index(
            system_idx=dv.system_idx,
            heating_load_kw=heating_load_kw,
            capex_gas_fixed=p["capex_gas_fixed"],
            capex_fw_fixed=p["capex_fw_fixed"],
            capex_fw_per_kw=p["capex_fw_per_kw"],
            capex_per_kw_wp=p["capex_per_kw_wp"]
        )

        cap_vent = capex_ventilation_per_area(p["A_ref"], p["capex_vent_per_m2"][dv.vent_level])
        cap_night = capex_night_reduction(p["capex_night"], is_active=(dv.night_flag == 1))

        capex_brutto = capex_total_from_components(
            [cap_wall, cap_roof, cap_floor, cap_windows, cap_system, cap_vent, cap_night]
        )

        # ==========================================================
        # H) Förderung: Zuschuss + CAPEX_eff
        # ==========================================================
        subsidy = calc_subsidy_wwfsg_from_energy(
            Q_old_total=p["Q_old_total"],
            Q_new_total=Q_new_total,
            A_ref=p["A_ref"],
            hwb_nsteg=10*(1+3/p["lc"]), # Referenzwert nstEG, kWh/(m²·a)
            area_nf=p["A_ref"],
            capex_eligible=capex_brutto,
            grant_rules=ctx.grant_rules,
            extra_measures=(dv.system_idx != 0)
        )
        subsidy_eur = subsidy["subsidy_eur"]
        stage_name = subsidy.get("stage_name", "keine")
        if stage_name == "keine":
            subsidy_stage = 0
        else:
            subsidy_stage = int(stage_name.replace("Stufe ", ""))
        capex_eff = capex_effective(capex_brutto=capex_brutto, subsidy_eur=subsidy_eur)

        # ==========================================================
        # I) Jahreskosten + LCC (NPV)
        # ==========================================================
        annual_costs = annual_energy_cost_total(
            Q_end_heating=Q_end_heat,
            price_heat_per_kwh=p["system_energy_price"][dv.system_idx],
            Q_el_aux=Q_el_aux,
            price_el_per_kwh=p["electricity_price"]
        )

        lcc = lcc_from_annual_cost(
            capex_effective=capex_eff,
            annual_cost_eur=annual_costs["cost_total_eur_a"],
            lifetime=p["lifetime"],
            discount_rate=p["discount_rate"]
        )

        # ==========================================================
        # J) Ökologie: CO2_total (Betrieb + embodied Dämmung)
        # ==========================================================
        co2_operational = calc_co2_operational_multi(
            energy_flows={
                "heating": {"Q": Q_end_heat, "EF": p["system_EF_op"][dv.system_idx]},
                "electricity": {"Q": Q_el_aux, "EF": p["electricity_EF_op"]}
            },
            lifetime=p["lifetime"]
        )["CO2_operational_total"]

        co2_embodied = calc_co2_embodied_total(
            insulation_elements={
                "wall": {"A": p["A_wall"], "d": dv.d_wall, "EF": p["EF_emb_wall_per_m3"][dv.mat_wall]},
                "roof": {"A": p["A_roof"], "d": dv.d_roof, "EF": p["EF_emb_roof_per_m3"][dv.mat_roof]},
                "floor": {"A": p["A_floor"], "d": dv.d_floor, "EF": p["EF_emb_floor_per_m3"][dv.mat_floor]},
            }
        )["CO2_embodied_total"]

        co2_total = co2_operational + co2_embodied

        # ==========================================================
        # K) Rückgabe (Zielfunktionen + optional Debug)
        # ==========================================================
        debug = {
            "Q_tr_sum": Q_tr_sum,
            "Q_vent": Q_vent,
            "Q_other": ctx.Q_other,
            "heating_load_kw": heating_load_kw,
            "capex_brutto": capex_brutto,
            "subsidy_eur": subsidy_eur,
            "annual_cost_eur_a": annual_costs["cost_total_eur_a"],
        }

        return EvalResult(
            capex_brutto=capex_brutto,
            capex_eff=capex_eff,
            subsidy_stage=subsidy_stage,
            q_new_total=Q_new_total,
            lcc=lcc,
            co2_total=co2_total,
            debug=debug
        )