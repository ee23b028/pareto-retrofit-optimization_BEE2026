"""
optimization/decision_space.py

Definition und Handhabung des Entscheidungsraums (Design Space).

Dieses Modul kapselt:
- Bounds (xl/xu) für pymoo
- robustes Casting diskreter Variablen (round + clip)
- Dekodierung eines x-Vektors in verständliche Variablen
- optionale Namen/Struktur für Debug und Export

ABGRENZUNG:
- Keine Modelllogik (keine Berechnungen von Energie, Kosten oder CO2).
- Keine Parameterwerte fest codiert -> alles kommt aus params.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple
import numpy as np


# =====================================================================
# 1) Helper: Diskrete Variablen robust casten (pymoo liefert floats)
# =====================================================================

def as_int(x: float, lo: int, hi: int) -> int:
    """
    Wandelt eine reelle Zahl in einen zulässigen diskreten Index um.

    Vorgehen:
    - Round: nächstliegende ganze Zahl
    - Clip: Begrenzung auf [lo, hi]

    Hinweis:
    - Dieser Schritt ist essenziell, weil Optimierer diskrete Variablen
      als floats liefern können.
    """

    #  Round + Clip sorgt für echte Diskretheit
    return int(np.clip(np.round(x), lo, hi))


# =====================================================================
# 2) Dataclass: Dekodierte Lösung (klarer Container statt lose Variablen)
# =====================================================================

@dataclass(frozen=True)
class DecisionVector:
    """
    Dekodierte Entscheidungsvariablen (interpretierbare Form).

    Stetige Variablen:
    - d_wall, d_roof, d_floor [m]

    Diskrete Variablen (Indices):
    - window_lvl (0..2)
    - system_idx (0..4)
    - night_flag (0/1)
    - mat_wall, mat_roof, mat_floor (0..2)
    - vent_level (0..2)
    """

    d_wall: float
    d_roof: float
    d_floor: float

    window_lvl: int
    system_idx: int
    night_flag: int

    mat_wall: int
    mat_roof: int
    mat_floor: int

    vent_level: int


# =====================================================================
# 3) Bounds für pymoo erzeugen (ein zentraler Ort)
# =====================================================================

def build_bounds(params: dict) -> Tuple[np.ndarray, np.ndarray]:
    """
    Erzeugt die Bounds (xl, xu) für das Optimierungsproblem.

    Rückgabe:
    - xl, xu als numpy arrays (dtype=float), passend für pymoo

    WICHTIG:
    - Diskrete Variablen werden als float-bounded geführt
      (z.B. 0..2), die echte Diskretheit erfolgt in decode_x().
    """

    xl = np.array([
        params["d_wall_min"],   # x0: Dämmstärke Wand [m]
        params["d_roof_min"],   # x1: Dämmstärke Dach [m]
        params["d_floor_min"],  # x2: Dämmstärke Boden [m]
        0.0,                    # x3: Fensterstufe
        0.0,                    # x4: Heizsystemindex
        0.0,                    # x5: Nachtabsenkung
        0.0,                    # x6: Dämmmaterial Wand
        0.0,                    # x7: Dämmmaterial Dach
        0.0,                    # x8: Dämmmaterial Boden
        0.0                     # x9: Lüftungssystem
    ], dtype=float)

    xu = np.array([
        params["d_wall_max"],
        params["d_roof_max"],
        params["d_floor_max"],
        2.0,  # Fenster (0..2)
        4.0,  # System (0..4)
        1.0,  # Nacht (0/1)
        2.0,  # Mat Wand (0..2)
        2.0,  # Mat Dach (0..2)
        2.0,  # Mat Boden (0..2)
        2.0   # Lüftung (0..2)
    ], dtype=float)

    return xl, xu


# =====================================================================
# 4) Dekodierung eines x-Vektors (zentral, damit Evaluator schlank bleibt)
# =====================================================================

def decode_x(x: np.ndarray) -> DecisionVector:
    """
    Dekodiert einen rohen x-Vektor (floats) in eine interpretierbare Struktur.

    Parameter:
    - x: numpy array mit Länge 10

    Rückgabe:
    - DecisionVector

    Hinweis:
    - Stetige Variablen werden als float übernommen.
    - Diskrete Variablen werden über as_int() gerundet und geclippt.
    """

    if len(x) != 10:
        raise ValueError("x muss Länge 10 haben (gemäß Modelldefinition).")

    # Stetige Variablen
    d_wall = float(x[0])
    d_roof = float(x[1])
    d_floor = float(x[2])

    # Diskrete Variablen
    window_lvl = as_int(x[3], 0, 2)
    system_idx = as_int(x[4], 0, 4)
    night_flag = as_int(x[5], 0, 1)

    mat_wall = as_int(x[6], 0, 2)
    mat_roof = as_int(x[7], 0, 2)
    mat_floor = as_int(x[8], 0, 2)

    vent_level = as_int(x[9], 0, 2)

    return DecisionVector(
        d_wall=d_wall,
        d_roof=d_roof,
        d_floor=d_floor,
        window_lvl=window_lvl,
        system_idx=system_idx,
        night_flag=night_flag,
        mat_wall=mat_wall,
        mat_roof=mat_roof,
        mat_floor=mat_floor,
        vent_level=vent_level
    )


# =====================================================================
# 5) Optional: Variable Names (hilft bei Export/Debugging)
# =====================================================================

def variable_names() -> List[str]:
    """
    Liefert die Namen der Designvariablen in der Reihenfolge von x.

    Nutzen:
    - Debug-Ausgaben
    - CSV/Excel Export (Spaltennamen)
    - Nachvollziehbarkeit in der Arbeit
    """

    return [
        "d_wall_m",
        "d_roof_m",
        "d_floor_m",
        "window_lvl",
        "system_idx",
        "night_flag",
        "mat_wall",
        "mat_roof",
        "mat_floor",
        "vent_level",
    ]
# =====================================================================
# 6) Export-Helper: DecisionVector -> Dict (dekodierte Entscheidungen)
# =====================================================================

def decision_vector_to_dict(dv: DecisionVector) -> dict:
    """
    Wandelt einen dekodierten DecisionVector in ein exportfähiges Dict um.

    Zweck:
    - Exportiert werden die tatsächlich bewerteten Entscheidungen (diskret & stetig)
    - Keine rohen Optimierer-Koordinaten (floats) in Excel/CSV
    - Dadurch bleiben Output und Modellzustand konsistent

    Hinweis:
    - Diese Funktion enthält KEINE Modelllogik, nur Mapping.
    """

    return {
        # Stetige Variablen (in Meter)
        "d_wall_m": dv.d_wall,
        "d_roof_m": dv.d_roof,
        "d_floor_m": dv.d_floor,

        # Diskrete Entscheidungen (Indices)
        "window_lvl": dv.window_lvl,
        "system_idx": dv.system_idx,
        "night_flag": dv.night_flag,
        "mat_wall": dv.mat_wall,
        "mat_roof": dv.mat_roof,
        "mat_floor": dv.mat_floor,
        "vent_level": dv.vent_level,
    }

# =====================================================================
# 7) Optionaler Selbsttest (nur bei direktem Aufruf)
# =====================================================================

if __name__ == "__main__":
    print("=== Test: optimization/decision_space.py ===")

    x_test = np.array([0.12, 0.25, 0.10, 1.7, 3.2, 0.4, 2.0, 0.2, 1.9, -0.3])
    dec = decode_x(x_test)

    print(dec)
    print(variable_names())

