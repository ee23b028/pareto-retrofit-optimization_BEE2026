"""
optimization/problems.py

pymoo-Problemdefinition (RetrofitProblem).

Dieses Modul enthält:
- Definition des Entscheidungsraums (n_var, xl/xu)
- Übergabe von x an den Evaluator
- Rückgabe der Zielfunktionen an pymoo

KEINE Modelllogik:
- Alle Berechnungen erfolgen in optimization/evaluator.py
"""

import numpy as np
from pymoo.core.problem import ElementwiseProblem

from optimization.decision_space import build_bounds
from optimization.evaluator import ModelEvaluator


class RetrofitProblem(ElementwiseProblem):
    """
    Multi-Objective-Optimierungsproblem.

    Zielfunktionen (Minimierung):
    f1 = CAPEX_eff   [€]
    f2 = Q_new_total [kWh/a]
    f3 = LCC         [€]
    f4 = CO2_total   [kg]
    """

    def __init__(self, params: dict):
        # Eindeutige Parameterquelle (kein globales params)
        self.p = params

        # Evaluator-Objekt mit Context (Q_other, grant_rules)
        self.evaluator = ModelEvaluator(self.p)

        # Bounds zentral aus decision_space.py
        xl, xu = build_bounds(self.p)

        # Problemdefinition für pymoo
        super().__init__(n_var=10, n_obj=4, xl=xl, xu=xu)

    def _evaluate(self, x, out, *args, **kwargs):
        """
        Elementweise Bewertung einer Lösung x.
        """

        res = self.evaluator.evaluate(x)

        # Reihenfolge der Ziele muss konsistent bleiben
        out["F"] = np.array(
            [res.capex_eff, res.q_new_total, res.lcc, res.co2_total],
            dtype=float
        )