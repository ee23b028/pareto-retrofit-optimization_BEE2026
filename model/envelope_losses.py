"""
model/envelope_losses.py

Transmissionswärmeverluste (Gebäudehülle) als Jahreswert auf Basis von Heizgradtagen (HGT).

Abgebildet wird ausschließlich:
- Q_tr je Bauteil: Q_tr = U * A * HGT * 24 / 1000   [kWh/a]

ABGRENZUNG:
- Keine U-Wert-Berechnung (Schichtaufbau / Zusatzdämmung -> eigenes Modul).
- Keine Lüftung (-> eigenes Modul).
- Keine Endenergie / Systemwirkungsgrade (-> Systemebene).

"""

from typing import Dict, Iterable


# =====================================================================
# 1) Q_tr für ein einzelnes Bauteil
# =====================================================================

def calc_q_tr_annual(
    U: float,
    A: float,
    HGT: float
) -> float:
    """
    Berechnet den jährlichen Transmissionswärmeverlust eines Bauteils.

    Formel (HGT-Ansatz):
    Q_tr [kWh/a] = U [W/(m²K)] * A [m²] * HGT [K*d] * 24 [h/d] / 1000

    Parameter:
    - U   : Wärmedurchgangskoeffizient [W/(m²K)]
    - A   : Bauteilfläche [m²]
    - HGT : Heizgradtage [K*d]

    Rückgabe:
    - Q_tr [kWh/a]
    """

    # Umrechnung von W*d -> kWh (24 h/d und /1000)
    Q_tr = U * A * HGT * 24.0 / 1000.0
    return float(Q_tr)


# =====================================================================
# 2) Q_tr für mehrere Bauteile (Komponentenliste)
# =====================================================================

def calc_transmission_losses(
    components: Iterable[Dict[str, float]],
    HGT: float
) -> Dict[str, float]:
    """
    Berechnet Transmissionsverluste für eine Menge an Bauteilen.

    Erwartetes Format je Komponente (Dictionary):
    - "name": Bezeichnung (z.B. "wall", "roof", ...)
    - "U"   : U-Wert [W/(m²K)]
    - "A"   : Fläche [m²]

    Rückgabe:
    - Dictionary mit Einzelverlusten je "name" sowie "Q_tr_sum"
      (Summe aller Transmissionsverluste)
    """

    results: Dict[str, float] = {}
    Q_sum = 0.0

    for comp in components:
        name = str(comp["name"])
        U = float(comp["U"])
        A = float(comp["A"])

        Q_i = calc_q_tr_annual(U=U, A=A, HGT=HGT)
        results[f"Q_tr_{name}"] = Q_i

        Q_sum += Q_i

    results["Q_tr_sum"] = float(Q_sum)
    return results


# =====================================================================
# 3) Convenience: Standardhülle als Dict übergeben (ohne Listenformat)
# =====================================================================

def calc_transmission_losses_from_dict(
    U_by_part: Dict[str, float],
    A_by_part: Dict[str, float],
    HGT: float
) -> Dict[str, float]:
    """
    Alternative Schnittstelle, wenn U- und A-Werte als Dictionaries vorliegen.

    Parameter:
    - U_by_part : z.B. {"wall": 0.8, "roof": 0.2, ...}
    - A_by_part : z.B. {"wall": 300.0, "roof": 90.0, ...}
    - HGT       : Heizgradtage [K*d]

    Rückgabe:
    - wie calc_transmission_losses(): Einzelverluste + "Q_tr_sum"
    """

    components = []
    for name, U in U_by_part.items():
        if name not in A_by_part:
            raise KeyError(f"Fläche A für Bauteil '{name}' fehlt in A_by_part.")
        components.append({"name": name, "U": float(U), "A": float(A_by_part[name])})

    return calc_transmission_losses(components=components, HGT=HGT)


# =====================================================================
# 4) Optionaler Selbsttest (nur bei direktem Aufruf)
# =====================================================================

if __name__ == "__main__":
    print("=== Test: model/envelope_losses.py ===")

    # Beispielwerte nur zur Plausibilitätsprüfung (keine Projektwerte)
    comps = [
        {"name": "wall", "U": 0.8, "A": 100.0},
        {"name": "roof", "U": 0.2, "A": 50.0},
    ]
    out = calc_transmission_losses(components=comps, HGT=3000.0)
    print(out)