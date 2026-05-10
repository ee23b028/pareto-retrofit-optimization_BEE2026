"""
config/parameters.py

Zentrale Sammlung aller fachlichen Modellparameter.

Enthalten sind:
- Gebäudegeometrie und Bestandskennwerte
- Material- und Systemparameter
- Kostenparameter (CAPEX, Energiepreise)
- Ökologische Parameter (Emissionsfaktoren)
- Förderparameter (WWFSG)

WICHTIGE ABGRENZUNG:
- Keine Optimierungsparameter (Populationsgröße, Generationen, etc.)
  -> siehe optimization_settings.py
- Alle Zahlenwerte sind projekt- und standortspezifisch
  und werden in Kapitel 5 der Arbeit dokumentiert.
"""

# =====================================================================
# 1) GEBÄUDE – Geometrie & Bestand
# =====================================================================

parameters = {
    #Bestand: 
    "lc": 1.74, #m Charakeristische Länge


    # -------------------------
    # Flächen [m²]
    # -------------------------
    "A_wall": 382.34,     # Außenwand
    "A_roof": 88.96,      # Dach / oberste Geschossdecke
    "A_floor": 160.22,    # Kellerdecke / Boden
    "A_window": 67.69,    # Fensterfläche gesamt
    "A_ref": 480.26,      # Bezugsfläche (z.B. BGF, auch förderrelevant)

    # -------------------------
    # Bestands-U-Werte [W/(m²K)]
    # -------------------------
    "U_wall_old": 0.962,
    "U_roof_old": 0.166,
    "U_floor_old": 0.767,
    "U_window_old": 1.72,

    # -------------------------
    # Klimaparameter
    # -------------------------
    "HGT": 3532.0,            # Heizgradtage [K*d]
    "Q_old_total": 66987.0,   # Heizwärmebedarf Bestand [kWh/a]

# =====================================================================
# 2) DÄMMSTOFFE – Materialparameter
# =====================================================================

    # Wärmeleitfähigkeit λ [W/(mK)]
    "lambda_ins_wall":  [0.040, 0.035, 0.044],
    "lambda_ins_roof":  [0.035, 0.039, 0.044],
    "lambda_ins_floor": [0.032, 0.028, 0.035],
 
    # Graue Emissionen [kgCO2/m³] – EPD-basiert (EN 15804 A1–A3)
    "EF_emb_wall_per_m3":  [66.52, 40.89, -118.56],
    "EF_emb_roof_per_m3":  [40.89, -25.135, -118.56],
    "EF_emb_floor_per_m3": [66.52, 137.92, 150.04],
    
# =====================================================================
# 3) FENSTER
# =====================================================================

    "U_window_levels": [1.72, 1.30, 0.80],      # Bestand / Standard / Passiv
    "n_windows": 17,
    "capex_per_window_levels": [0.0, 282.18, 1184.96],  # Bestand / Standard / Passiv

# =====================================================================
# 4) LÜFTUNG
# =====================================================================

    "L_v_old": 129.06,                 # Lüftungsleitwert Bestand [W/K]
    "vent_factor": [1.0, 0.85, 1.0],   # Fenster / Abluft / KWL
    "vent_eta_wrg": [0.0, 0.0, 0.75],  # Wärmerückgewinnung
    "vent_el_per_m2a": [0.0, 1.0, 3.0],# Hilfsstrom [kWh/(m²a)]
    "capex_vent_per_m2": [0.0, 16.67, 71.0],  # Bestand / Abluft / KWL

# =====================================================================
# 5) HEIZSYSTEME
# =====================================================================

    "system_eta": [0.90, 0.95, 3.0, 4.0, 4.5],  # Gas / FW / WP
    "system_energy_price": [0.10, 0.09, 0.20, 0.20, 0.20],  # €/kWh
    "system_EF_op": [0.201, 0.118, 0.074, 0.074, 0.074],      # kgCO2/kWh

    # Heizlast-Vorbemessung
    "full_load_hours": 2000.0,
    "min_heating_load_kw": 1.0,

    # CAPEX Heizsysteme
    "capex_gas_fixed": 0,
    "capex_fw_fixed": 25000.0,
    "capex_fw_per_kw": 250.0,
    "capex_per_kw_wp": {2: 1391.67, 3: 3706.67, 4: 3140.00}, # WP 2: Luft-Wasser, WP 3: Sole-Wasser, WP 4: Wasser-Wasser

# =====================================================================
# 6) NACHTABSENKUNG
# =====================================================================

    "night_reduction_factor": 0.05,
    "capex_night": 2000.0,

# =====================================================================
# 7) ÖKONOMIE
# =====================================================================

    "electricity_price": 0.20,
    "electricity_EF_op": 0.074,
    "lifetime": 30,
    "discount_rate": 0.03,
    
    # Dämmkosten Außenwand (WDVS): k + d * x
    "c_ins_wall_per_cm_m2": {
    0: 1.00,  # EPS
    1: 0.90,  # Mineralwolle
    2: 2.20,  # Holzfaser
    },
    "c_ins_wall_fix_m2": 158.0,

    # Dämmkosten oberste Geschoßdecke
    "c_ins_roof_per_cm_m2": {
    0: 0.90,  # Mineralwolle
    1: 2.30,  # Zellulose
    2: 2.20,  # Holzfaser
    },
    "c_ins_roof_fix_m2": 15.0,

    # Dämmkosten Kellerdecke
    "c_ins_floor_per_cm_m2": {
    0: 1.50,  # XPS
    1: 1.40,  # PUR/PIR
    2: 1.10,  # druckfeste Mineralwolle
    },
    "c_ins_floor_fix_m2": 15.0,

# =====================================================================
# 8) FÖRDERUNG – WWFSG (nur Parameter, keine Logik)
# =====================================================================

'''
"HWB_ref_rk": 124.7,  # Referenzwert nstEG

    "wwfsg": {
        "grants": {
            "Stufe 0": {"grant_per_m2": 35.0,  "max_ratio_total_cost": 0.20},
            "Stufe 1": {"grant_per_m2": 80.0,  "max_ratio_total_cost": 0.25},
            "Stufe 2": {"grant_per_m2": 120.0, "max_ratio_total_cost": 0.30},
            "Stufe 3": {"grant_per_m2": 160.0, "max_ratio_total_cost": 0.35},
            "Stufe 4": {"grant_per_m2": 200.0, "max_ratio_total_cost": 0.40},
            "Stufe 5": {"grant_per_m2": 220.0, "max_ratio_total_cost": 0.40},
        }
    },
'''
"HWB_ref_rk": 124.7,  # Referenzwert nstEG

    "wwfsg": {
        "grants": {
            "Stufe 0": {"grant_per_m2": 0,  "max_ratio_total_cost": 0.0},
            "Stufe 1": {"grant_per_m2": 0,  "max_ratio_total_cost": 0.0},
            "Stufe 2": {"grant_per_m2": 0, "max_ratio_total_cost": 0.0},
            "Stufe 3": {"grant_per_m2": 0, "max_ratio_total_cost": 0.0},
            "Stufe 4": {"grant_per_m2": 0, "max_ratio_total_cost": 0.0},
            "Stufe 5": {"grant_per_m2": 0, "max_ratio_total_cost": 0.0},
        }
    },
# =====================================================================
# 9) ENTSCHEIDUNGSVARIABLEN – BOUNDS
# =====================================================================

    "d_wall_min": 0.00,
    "d_wall_max": 0.24,
    "d_roof_min": 0.00,
    "d_roof_max": 0.30,
    "d_floor_min": 0.00,
    "d_floor_max": 0.16,
}