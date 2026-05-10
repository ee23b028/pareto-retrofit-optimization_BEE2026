"""
config/optimization_settings.py

Einstellungen für den Optimierungsalgorithmus (NSGA-II).

ABGRENZUNG:
- Keine fachlichen Modellparameter.
- Ausschließlich algorithmische und numerische Einstellungen.
"""

optimization_settings = {

    # -------------------------------------------------------------
    # Algorithmus: NSGA-II
    # -------------------------------------------------------------
    "algorithm": "NSGA2",

    # -------------------------------------------------------------
    # Populationsparameter
    # -------------------------------------------------------------
    "pop_size": 300,              # Populationsgröße (Anzahl Lösungen pro Generation)
    "n_generations": 500,         # Anzahl Generationen (Iterationsschritte)

    # -------------------------------------------------------------
    # Reproduzierbarkeit
    # -------------------------------------------------------------
    "seed": 1,                    # fester Seed für Vergleichbarkeit
    "eliminate_duplicates": True,

    # -------------------------------------------------------------
    # pymoo-spezifisch
    # -------------------------------------------------------------
    "save_history": False,
    "verbose": True,
}
