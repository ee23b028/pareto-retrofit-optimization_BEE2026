"""
model/envelope_u.py

Berechnung von Wärmedurchgangskoeffizienten (U-Werten) bei zusätzlicher Dämmung.

Abgebildet wird:
- Umrechnung eines bestehenden U-Wertes in einen Wärmedurchlasswiderstand
- Addition des Widerstands einer zusätzlichen Dämmschicht
- Rückrechnung in einen neuen U-Wert

ABGRENZUNG:
- Keine detaillierte Schichtmodellierung des Bestands.
- Bestehender U-Wert wird als aggregierter Widerstand interpretiert.
- Keine Feuchte-, Alterungs- oder Wärmebrückenaufschläge.
"""

# =====================================================================
# 1) Umrechnung U-Wert -> Wärmedurchlasswiderstand
# =====================================================================

def u_to_r(U_value: float) -> float:
    """
    Wandelt einen U-Wert in einen Wärmedurchlasswiderstand um.

    Formel:
    R = 1 / U

    Parameter:
    - U_value : Wärmedurchgangskoeffizient [W/(m²·K)]

    Rückgabe:
    - Wärmedurchlasswiderstand R [m²·K/W]

    """

    if U_value <= 0:
        raise ValueError("U-Wert muss größer als 0 sein.")

    # Kehrwertbildung 
    R_value = 1.0 / U_value

    return float(R_value)


# =====================================================================
# 2) Wärmedurchlasswiderstand einer Dämmschicht
# =====================================================================

def insulation_r_value(
    insulation_thickness: float,
    lambda_insulation: float
) -> float:
    """
    Berechnet den Wärmedurchlasswiderstand einer Dämmschicht.

    Formel:
    R_ins = d / λ

    Parameter:
    - insulation_thickness : Dämmstärke d [m]
    - lambda_insulation    : Wärmeleitfähigkeit λ [W/(m·K)]

    Rückgabe:
    - Wärmedurchlasswiderstand der Dämmung [m²·K/W]

    """

    if insulation_thickness < 0:
        raise ValueError("Dämmstärke darf nicht negativ sein.")
    if lambda_insulation <= 0:
        raise ValueError("Wärmeleitfähigkeit muss größer als 0 sein.")

    # Widerstand als Verhältnis von Dicke zu Leitfähigkeit
    R_ins = insulation_thickness / lambda_insulation

    return float(R_ins)


# =====================================================================
# 3) Neuer U-Wert bei zusätzlicher Dämmung
# =====================================================================

def calc_u_with_additional_insulation(
    U_existing: float,
    insulation_thickness: float,
    lambda_insulation: float
) -> float:
    """
    Berechnet den neuen U-Wert eines Bauteils nach zusätzlicher Dämmung.

    Methodik:
    1) Umrechnung des bestehenden U-Werts in einen Widerstand R_existing
    2) Berechnung des Widerstands der neuen Dämmschicht R_ins
    3) Addition der Widerstände (serieller Ansatz)
    4) Rückrechnung in einen neuen U-Wert

    Formel:
    U_neu = 1 / (R_existing + R_ins)

    Parameter:
    - U_existing          : bestehender U-Wert [W/(m²·K)]
    - insulation_thickness: Dämmstärke d [m]
    - lambda_insulation   : Wärmeleitfähigkeit λ [W/(m·K)]

    Rückgabe:
    - Neuer U-Wert [W/(m²·K)]

    """

    # -------------------------------------------------------------
    # A) Bestehenden U-Wert in Widerstand umrechnen
    # -------------------------------------------------------------
    R_existing = u_to_r(U_existing)

    # -------------------------------------------------------------
    # B) Widerstand der zusätzlichen Dämmung
    # -------------------------------------------------------------
    R_ins = insulation_r_value(
        insulation_thickness=insulation_thickness,
        lambda_insulation=lambda_insulation
    )

    # -------------------------------------------------------------
    # C) Serieller Widerstandsansatz
    # -------------------------------------------------------------
    R_total = R_existing + R_ins

    # -------------------------------------------------------------
    # D) Rückrechnung in neuen U-Wert
    # -------------------------------------------------------------
    # neuer U-Wert als Kehrwert des Gesamtwiderstands
    U_new = 1.0 / R_total

    return float(U_new)


# =====================================================================
# 4) Convenience-Funktion für Variantenrechnungen
# =====================================================================

def calc_u_variants(
    U_existing: float,
    insulation_thicknesses: list,
    lambda_insulation: float
) -> dict:
    """
    Berechnet mehrere U-Werte für verschiedene Dämmstärken.

    Parameter:
    - U_existing            : bestehender U-Wert [W/(m²·K)]
    - insulation_thicknesses: Liste von Dämmstärken [m]
    - lambda_insulation     : Wärmeleitfähigkeit [W/(m·K)]

    Rückgabe:
    - Dictionary {d: U_neu} mit Dämmstärke als Schlüssel
    """

    results = {}

    for d in insulation_thicknesses:
        U_new = calc_u_with_additional_insulation(
            U_existing=U_existing,
            insulation_thickness=d,
            lambda_insulation=lambda_insulation
        )
        results[float(d)] = float(U_new)

    return results


# =====================================================================
# 5) Optionaler Selbsttest (nur bei direktem Aufruf)
# =====================================================================

if __name__ == "__main__":
    print("=== Test: model/envelope_u.py ===")

    # Beispielwerte (nur Plausibilitätsprüfung)
    U_alt = 0.9
    d_ins = 0.12
    lambda_ins = 0.035

    U_neu = calc_u_with_additional_insulation(
        U_existing=U_alt,
        insulation_thickness=d_ins,
        lambda_insulation=lambda_ins
    )

    print(f"U_alt = {U_alt:.3f} W/(m²K)")
    print(f"U_neu = {U_neu:.3f} W/(m²K)")