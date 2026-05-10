"""
model/ventilation.py

Lüftungswärmeverluste auf Gebäudeebene als Jahreswert (Nutzenergie).

Abgebildet werden:
- effektiver Lüftungsleitwert L_v,eff [W/K]
- jährlicher Lüftungswärmeverlust Q_vent [kWh/a]

ABGRENZUNG:
- Keine Infiltration als eigener Term (in normativen Luftwechselraten enthalten).
- Keine zeitliche Auflösung (Jahresansatz über Heizgradtage).
- Keine elektrische Hilfsenergie (Ventilatorstrom -> Systemebene).
"""

from typing import Dict


# =====================================================================
# 1) Lüftungsleitwert L_v nach EN ISO 52016-1
# =====================================================================

def calc_l_v(
    air_change_rate: float,
    volume: float,
    c_air: float = 0.34
) -> float:
    """
    Berechnet den Lüftungsleitwert L_v [W/K].

    Formel:
    L_v = n * V * c_air

    Parameter:
    - air_change_rate (n): Luftwechselrate [1/h]
    - volume (V)         : Luftvolumen [m³]
    - c_air              : spezifische Wärmekapazität der Luft
                            [Wh/(m³·K)], normativ ≈ 0.34

    Rückgabe:
    - L_v [W/K]

    Normative Herkunft:
    - EN ISO 52016-1, EN 16798-1
    """

    # Direkte Umsetzung der normativen Definition des Lüftungsleitwertes
    L_v = air_change_rate * volume * c_air

    return float(L_v)


# =====================================================================
# 2) Effektiver Lüftungsleitwert inkl. Systemfaktor & WRG
# =====================================================================

def calc_l_v_effective(
    L_v_base: float,
    ventilation_factor: float = 1.0,
    heat_recovery_efficiency: float = 0.0
) -> float:
    """
    Berechnet den effektiven Lüftungsleitwert L_v,eff [W/K].

    Modelllogik:
    - ventilation_factor bildet reduzierte Luftwechselraten ab
      (z.B. bei mechanischer Abluft)
    - heat_recovery_efficiency (η_WRG) reduziert die Lüftungswärmeverluste
      bei kontrollierter Wohnraumlüftung mit Wärmerückgewinnung

    Formel:
    L_v,eff = L_v_base * ventilation_factor * (1 - η_WRG)

    Parameter:
    - L_v_base                : Basis-Lüftungsleitwert [W/K]
    - ventilation_factor      : Faktor [-] (z.B. 0.85 bei Abluft)
    - heat_recovery_efficiency: Wärmerückgewinnungsgrad η_WRG [-]

    Rückgabe:
    - L_v,eff [W/K]

    """

    # WRG reduziert nur den wirksamen Wärmeverlust, nicht den Luftwechsel selbst
    L_v_eff = L_v_base * ventilation_factor * (1.0 - heat_recovery_efficiency)

    return float(L_v_eff)


# =====================================================================
# 3) Jährlicher Lüftungswärmeverlust über Heizgradtage
# =====================================================================

def calc_q_vent_annual(
    L_v_eff: float,
    HGT: float
) -> float:
    """
    Berechnet den jährlichen Lüftungswärmeverlust Q_vent [kWh/a]
    über Heizgradtage.

    Formel:
    Q_vent = L_v,eff * HGT * 24 / 1000

    Parameter:
    - L_v_eff : effektiver Lüftungsleitwert [W/K]
    - HGT     : Heizgradtage [K·d]

    Rückgabe:
    - Q_vent [kWh/a]

    Methodik:
    - Jahresbilanz auf Basis von Heizgradtagen
    - konsistent zum Transmissionsansatz (Q_tr)
    """

    # Umrechnung von W·d -> kWh (24 h/d und Division durch 1000)
    Q_vent = L_v_eff * HGT * 24.0 / 1000.0

    return float(Q_vent)


# =====================================================================
# 4) Convenience-Funktion: Q_vent aus Parametern
# =====================================================================

def calc_ventilation_losses(
    L_v_base: float,
    HGT: float,
    ventilation_factor: float = 1.0,
    heat_recovery_efficiency: float = 0.0
) -> Dict[str, float]:
    """
    Convenience-Funktion zur Berechnung der Lüftungswärmeverluste
    in einem Schritt.

    Parameter:
    - L_v_base                : Basis-Lüftungsleitwert [W/K]
    - HGT                     : Heizgradtage [K·d]
    - ventilation_factor      : Faktor für reduzierte Luftwechsel [-]
    - heat_recovery_efficiency: Wärmerückgewinnungsgrad η_WRG [-]

    Rückgabe (Dictionary):
    - L_v_eff : effektiver Lüftungsleitwert [W/K]
    - Q_vent  : jährlicher Lüftungswärmeverlust [kWh/a]
    """

    L_v_eff = calc_l_v_effective(
        L_v_base=L_v_base,
        ventilation_factor=ventilation_factor,
        heat_recovery_efficiency=heat_recovery_efficiency
    )

    Q_vent = calc_q_vent_annual(
        L_v_eff=L_v_eff,
        HGT=HGT
    )

    return {
        "L_v_eff": float(L_v_eff),
        "Q_vent": float(Q_vent),
    }


# =====================================================================
# 5) Optionaler Selbsttest (nur bei direktem Aufruf)
# =====================================================================

if __name__ == "__main__":
    print("=== Test: model/ventilation.py ===")

    # Beispielwerte (nur Plausibilitätscheck)
    L_v_base = 120.0      # [W/K]
    HGT = 3000.0          # [K*d]
    vent_factor = 0.85    # Abluft
    eta_wrg = 0.75        # KWL mit WRG

    out = calc_ventilation_losses(
        L_v_base=L_v_base,
        HGT=HGT,
        ventilation_factor=vent_factor,
        heat_recovery_efficiency=eta_wrg
    )

    print(out)