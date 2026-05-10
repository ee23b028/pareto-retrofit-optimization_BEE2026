"""
init.py

Startskript für die Multi-Objective-Optimierung der Gebäudesanierung.

AUFGABE DIESES SKRIPTS:
- Laden der Modell- und Optimierungsparameter
- Initialisierung des Optimierungsproblems
- Konfiguration und Ausführung des NSGA-II Algorithmus
- Auslesen der Pareto-Lösungen
- Export und Visualisierung der Ergebnisse

WICHTIGE ABGRENZUNG:
- Dieses Skript enthält KEINE Modelllogik.
- Alle fachlichen Annahmen sind in den Modulen:
  * model/*
  * economics/*
  * ecology/*
  * policy/*
  * optimization/evaluator.py
  definiert.
"""

# =====================================================================
# 0) IMPORTS – Standard
# =====================================================================

import numpy as np

# =====================================================================
# 1) IMPORTS – Optimierung (pymoo)
# =====================================================================

from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.optimize import minimize
from pymoo.termination import get_termination

# =====================================================================
# 2) IMPORTS – Projektmodule
# =====================================================================

# Fachliche Modellparameter
from config.parameters import parameters

# Optimierungseinstellungen (Algorithmus, Populationsgröße, etc.)
from config.optimization_settings import optimization_settings as opt

# Optimierungsproblem (pymoo-Hülle)
from optimization.problems import RetrofitProblem

# Export & Visualisierung
from utils.export import (
    export_pareto_csv,
    export_pareto_excel,
    save_plot_2d,
    save_plot_spec_2d,
    save_plot_3d,
    save_plot_3d_colored,
    save_plot_matrix,
    save_plot_matrix_specific,
    save_plot_matrix_zoomed,
    save_plot_matrix_zoomed_specific
)

# Designvariablen-Namen (für CSV/Excel)
from optimization.decision_space import variable_names

# Datum und Uhrzeit für Export-Dateinamen
import os
from datetime import datetime


# =====================================================================
# 3) OPTIMIERUNGSPROBLEM INITIALISIEREN
# =====================================================================

# Kritische Zeile:
# Das Problem kapselt den Evaluator und damit das gesamte Modell.
problem = RetrofitProblem(parameters)


# =====================================================================
# 4) OPTIMIERUNGSALGORITHMUS KONFIGURIEREN
# =====================================================================

# NSGA-II Algorithmus
algorithm = NSGA2(
    pop_size=opt["pop_size"],
    eliminate_duplicates=opt["eliminate_duplicates"]
)

# Abbruchkriterium: fixe Anzahl an Generationen
termination = get_termination("n_gen", opt["n_generations"])


# =====================================================================
# 5) OPTIMIERUNG AUSFÜHREN
# =====================================================================

print("=== Starte NSGA-II Optimierung ===")

result = minimize(
    problem=problem,
    algorithm=algorithm,
    termination=termination,
    seed=opt["seed"],          # Reproduzierbarkeit
    save_history=opt["save_history"],
    verbose=opt["verbose"]
)

print("=== Optimierung abgeschlossen ===")


# =====================================================================
# 6) ERGEBNISSE AUSLESEN
# =====================================================================

# Entscheidungsvariablen der Pareto-Lösungen
X = result.X     # shape: (n_solutions, n_var)
# Zielwerte der Pareto-Lösungen
F = result.F

print(f"Anzahl Pareto-Lösungen: {len(X)}")


# =====================================================================
# 7) EXPORT DER ERGEBNISSE
# =====================================================================
# =====================================================================
# OUTPUT-ORDNER PRO RUN (Datum + Uhrzeit)
# =====================================================================

timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
output_dir = os.path.join("output", timestamp)
os.makedirs(output_dir, exist_ok=True)
            

print("=== Exportiere Ergebnisse ===")

# Namen der Designvariablen
var_names = variable_names()

# Namen der Zielfunktionen (für CSV/Excel & Plots)
obj_names = [
    "CAPEX_eff",
    "Q_new_total",
    "LCC",
    "CO2_total"
]

# CSV-Export (immer)
csv_path = export_pareto_csv(
    X=X,
    F=F,
    params=parameters,
    var_names=var_names,
    obj_names=obj_names,
    base_filename="Pareto_Optimierung",
    folder=output_dir,
    top_k=10
)
print(f"CSV exportiert: {csv_path}")

# Excel-Export (optional, nur wenn openpyxl installiert ist)
excel_path = export_pareto_excel(
    X=X,
    F=F,
    params=parameters,
    var_names=var_names,
    obj_names=obj_names,
    base_filename="Pareto_Optimierung",
    folder=output_dir,
    top_k=10
)

if excel_path:
    print(f"Excel exportiert: {excel_path}")
else:
    print("Excel-Export nicht verfügbar (openpyxl nicht installiert).")


# =====================================================================
# 8) VISUALISIERUNG – PARETO-PLOTS
# =====================================================================

print("=== Erzeuge Pareto-Plots ===")

# Achsenlabels (absolute Werte)
labels_abs = [
    "CAPEX [€]",
    "Q_new [kWh/a]",
    "LCC [€]",
    "CO2 [kg CO2-eq]"
]

labels_spec = [
    "CAPEX [€/m²]",
    "Q_new [kWh/(m²·a)]",
    "LCC [€/m²]",
    "CO2 [kg CO2-eq/m²]"
]

# 2D-Pareto-Plots (typische Zielkonflikte)
save_plot_2d(F, 0, 1, labels_abs[0], labels_abs[1], name="Pareto_CAPEX_vs_Q",folder=output_dir, top_k=10)
save_plot_2d(F, 0, 2, labels_abs[0], labels_abs[2], name="Pareto_CAPEX_vs_LCC",folder=output_dir, top_k=10)
save_plot_2d(F, 0, 3, labels_abs[0], labels_abs[3], name="Pareto_CAPEX_vs_CO2",folder=output_dir, top_k=10)
save_plot_2d(F, 1, 2, labels_abs[1], labels_abs[2], name="Pareto_Q_vs_LCC",folder=output_dir, top_k=10)
save_plot_2d(F, 1, 3, labels_abs[1], labels_abs[3], name="Pareto_Q_vs_CO2",folder=output_dir, top_k=10)
save_plot_2d(F, 2, 3, labels_abs[2], labels_abs[3], name="Pareto_LCC_vs_CO2",folder=output_dir, top_k=10)

# 2D-Pareto-Plots (typische Zielkonflikte)
save_plot_spec_2d(F, A_ref=parameters["A_ref"], ix=0, iy=1, labels_spec=labels_spec, name="Pareto_CAPEX_vs_Q", folder=output_dir, top_k=10)
save_plot_spec_2d(F, A_ref=parameters["A_ref"], ix=0, iy=2, labels_spec=labels_spec, name="Pareto_CAPEX_vs_LCC", folder=output_dir, top_k=10)
save_plot_spec_2d(F, A_ref=parameters["A_ref"], ix=0, iy=3, labels_spec=labels_spec, name="Pareto_CAPEX_vs_CO2", folder=output_dir, top_k=10)
save_plot_spec_2d(F, A_ref=parameters["A_ref"], ix=1, iy=2, labels_spec=labels_spec, name="Pareto_Q_vs_LCC", folder=output_dir, top_k=10)
save_plot_spec_2d(F, A_ref=parameters["A_ref"], ix=1, iy=3, labels_spec=labels_spec, name="Pareto_Q_vs_CO2", folder=output_dir, top_k=10)
save_plot_spec_2d(F, A_ref=parameters["A_ref"], ix=2, iy=3, labels_spec=labels_spec, name="Pareto_LCC_vs_CO2", folder=output_dir, top_k=10)


# 3D-Pareto-Plot mit CAPEX, Q_new und CO2 (absolute Werte)
save_plot_3d(
    F,
    0, 1, 3,
    labels_abs[0],
    labels_abs[1],
    labels_abs[3],
    name="Pareto_3D_CAPEX_Q_CO2",
    folder=output_dir,
)
# 3D-Pareto-Plot mit CAPEX, Q_new und LCC (absolute Werte)
save_plot_3d(
    F,
    0, 1, 2,
    labels_abs[0],
    labels_abs[1],
    labels_abs[2],
    name="Pareto_3D_CAPEX_Q_LCC",
    folder=output_dir
)
# 3D-Pareto-Plot mit CAPEX, Q_new und CO2-Emissionen (absolute Werte)
save_plot_3d(
    F,
    1, 2, 3,
    labels_abs[1],
    labels_abs[2],
    labels_abs[3],
    name="Pareto_3D_CAPEX_Q_CO2",
    folder=output_dir
)

# 3D-Pareto-Plot mit Farbe für CO2-Emissionen absolute Werte
save_plot_3d_colored(
    F,
    ix=0,  # CAPEX
    iy=1,  # Q_new
    iz=2,  # LCC
    ic=3,  # CO2 (Farbe)
    labels=labels_abs,
    name="Pareto_3D_CAPEX_Q_LCC_CO2",
    folder=output_dir,
    top_k=10
)

# 4x4 Plot-Matrix (absolute Werte)
save_plot_matrix(
    F,
    labels_abs,
    name="Pareto_Matrix_abs",
    folder=output_dir,
)

# 4x4 Plot-Matrix (spezifische Werte /m²)

save_plot_matrix_specific(
    F,
    labels_spec,
    A_ref=parameters["A_ref"],
    name="Pareto_Matrix_spec",
    folder=output_dir
)


# -------------------------------------------------------------
# 4x4 Plot-Matrix – gezoomt auf Top-k Lösungen
# -------------------------------------------------------------

# Zoom-Matrix (absolute Werte)
save_plot_matrix_zoomed(
    F,
    labels_abs,
    name="Pareto_Matrix_Zoom_abs",
    top_k=10,
    margin=0.15,
    folder=output_dir
)

# Zoom-Matrix (spezifische Werte)
save_plot_matrix_zoomed_specific(
    F,
    labels_spec,
    A_ref=parameters["A_ref"],
    name="Pareto_Matrix_Zoom_spec",
    top_k=10,
    margin=0.15,
    folder=output_dir
)

# =====================================================================
# 9) ABSCHLUSS
# =====================================================================

print("=== Optimierung & Auswertung abgeschlossen ===")