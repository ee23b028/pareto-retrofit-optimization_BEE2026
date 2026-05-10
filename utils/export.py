"""
utils/export.py

Export- und Visualisierungsfunktionen für die Pareto-Optimierung.

Dieses Modul übernimmt ausschließlich:
- Ergebnisaufbereitung (Strukturierung, Ranking)
- Export (CSV, optional Excel)
- Visualisierung (Pareto-Plots, Plot-Matrizen, Zoom-Matrizen)

WICHTIGE ABGRENZUNG:
- Keine Modelllogik
- Keine Förderlogik
- Keine Parameterdefinitionen
- Keine erneuten Berechnungen von Energie, Kosten oder CO2

Alle Berechnungen stammen aus dem Evaluator.
Dieses Modul ist rein passiv (Auswertung & Darstellung).
"""

# =====================================================================
# 0) IMPORTS
# =====================================================================

import os
import csv
from typing import Dict, List, Optional, Tuple

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.lines import Line2D

# Excel optional (robust: kein Fehler, wenn nicht installiert)
try:
    import openpyxl
except ImportError:
    openpyxl = None

# Dekodierung der Entscheidungsvariablen (KEINE Logik, nur Mapping)
from config import parameters
from optimization.decision_space import decode_x, decision_vector_to_dict


# =====================================================================
# 1) VISUAL STYLE – EINHEITLICH FÜR ALLE PLOTS
# =====================================================================

PLOT_STYLE = {
    # Gesamte Pareto-Menge (Hintergrund)

    "all": {
        # deutlich sichtbarer Hintergrund
        "color": "#9e9e9e",     
        "marker": "o",
        "size": 14,              
        "alpha": 0.45,           
        "edgecolor": "none",
        "label": "Alle Pareto-Lösungen"
    },

    # Top-k Lösungen nach RankSum
    "top": {
        "color": "tab:blue",
        "marker": "o",
        "size": 50,
        "alpha": 1.00,
        "edgecolor": "black",
        "label": "Top-k Lösungen (RankSum)"
    }   
}
# Zusätzliche Marker für Extrempunkte je Zielfunktion
EXTREME_STYLE = {
    "capex": {
        "color": "tab:green",
        "marker": "^",
        "size": 50,
        "label": "Minimum CAPEX"
    },
    "q": {
        "color": "tab:orange",
        "marker": "v",
        "size": 50,
        "label": "Minimum Q"
    },
    "lcc": {
        "color": "tab:purple",
        "marker": "s",
        "size": 50,
        "label": "Minimum LCC"
    },
    "co2": {
        "color": "tab:red",
        "marker": "D",
        "size": 50,
        "label": "Minimum CO₂"
    }
}

# =====================================================================
# 2) HILFSFUNKTIONEN – FORMAT & DATEIHANDLING
# =====================================================================

def get_next_filename(base_name: str, folder: str, ext: str) -> str:
    """
    Erzeugt versionierte Dateinamen:
    base_v01.csv, base_v02.csv, ...
    """
    os.makedirs(folder, exist_ok=True)
    i = 1
    while True:
        path = os.path.join(folder, f"{base_name}_v{i:02d}{ext}")
        if not os.path.exists(path):
            return path
        i += 1


def thousands_dot_formatter():
    """
    Tausendertrennung mit Punkt statt Komma (z. B. 12.345).
    Locale-unabhängig und reproduzierbar.
    """
    def _fmt(x, pos):
        try:
            return f"{int(x):,}".replace(",", ".")
        except Exception:
            return ""
    return mticker.FuncFormatter(_fmt)

def get_extended_legend_handles(include_extremes: bool = True):
    """
    Erzeugt Legendeneinträge für:
    - Alle Pareto-Lösungen (grau)
    - Top-k Lösungen (blau)
    - Optional: Extrempunkte je Zielfunktion (Referenzmarker)
    """
    LEGEND_MARKER_SIZE = 10  # <<< ZENTRALE Steuerung (pt)
    handles = []

    # Standard: All + Top (dein bestehendes Schema)
    for key in ["all", "top"]:
        s = PLOT_STYLE[key]
        handles.append(
            Line2D(
                [], [], linestyle="None",
                marker=s["marker"],
                color=s["color"],
                markeredgecolor=s["edgecolor"],
                markersize=LEGEND_MARKER_SIZE,
                alpha=s["alpha"],
                label=s["label"]
            )
        )

    if include_extremes:
        for k, st in EXTREME_STYLE.items():
            handles.append(
                Line2D(
                    [], [], linestyle="None",
                    marker=st["marker"],
                    color=st["color"],
                    markeredgecolor="black",
                    markersize=LEGEND_MARKER_SIZE,
                    alpha=1.0,
                    label=st["label"]
                )
            )

    return handles

# =====================================================================
# 3) RANKING (AUSWERTUNG, KEINE OPTIMIERUNGSLOGIK)
# =====================================================================

def compute_ranks(F: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Berechnet für jede Zielfunktion einen Rang (1 = beste Lösung)
    sowie die Rangsumme (RankSum / Borda).

    Annahme:
    - Alle Zielfunktionen werden minimiert.
    """
    n, m = F.shape
    ranks = np.zeros((n, m), dtype=int)

    for j in range(m):
        order = np.argsort(F[:, j])
        ranks[order, j] = np.arange(1, n + 1)

    return ranks, ranks.sum(axis=1)


def get_top_k_indices(rank_sum: np.ndarray, k: int = 10) -> np.ndarray:
    """
    Liefert die Indizes der Top-k Lösungen nach RankSum.
    """
    return np.argsort(rank_sum)[:int(k)]

def get_extreme_indices(F: np.ndarray) -> Dict[str, int]:
    """
    Liefert die Indizes der jeweils besten Lösung je Zielfunktion (Minimum).

    WICHTIG:
    - Annahme: alle Zielfunktionen werden minimiert.
    - Das ist reine Auswertung auf Basis von F (keine Modelllogik).
    """
    return {
        "capex": int(np.argmin(F[:, 0])),  # Minimum CAPEX_eff
        "q":     int(np.argmin(F[:, 1])),  # Minimum Q_new_total
        "lcc":   int(np.argmin(F[:, 2])),  # Minimum LCC
        "co2":   int(np.argmin(F[:, 3])),  # Minimum CO2_total
    }

# =====================================================================
# 4) CSV-EXPORT (DEKODIERTE ENTSCHEIDUNGEN)
# =====================================================================

def export_pareto_csv(
    X: np.ndarray,
    F: np.ndarray,
    params: dict,
    var_names: List[str],
    obj_names: List[str],
    base_filename: str = "Pareto_Optimierung",
    folder: str = "output",
    top_k: int = 10
) -> str:
    """
    Exportiert Pareto-Lösungen als CSV-Datei.

    Inhalt:
    - dekodierte Entscheidungsvariablen (keine rohen X-Werte)
    - Zielfunktionen (F)
    - Rang je Zielfunktion
    - RankSum (Borda)
    - spezifische Zielfunktionen (/m²)
    """

    path = get_next_filename(base_filename, folder, ".csv")

    # Ranking berechnen
    ranks, rank_sum = compute_ranks(F)

    # Bezugsfläche für spezifische Werte
    A_ref = float(params.get("A_ref", 1.0))

    # Entscheidungsvariablen dekodieren
    
    from optimization.evaluator import ModelEvaluator
    evaluator = ModelEvaluator(params)

    decoded = [decision_vector_to_dict(decode_x(x)) for x in X]
    decision_keys = list(decoded[0].keys())

    header = []
    header += decision_keys
    header += ["CAPEX_brutto", "subsidy_stage"]
    header += obj_names
    header += [f"{n}_spec" for n in obj_names]
    header += [f"Rank_{n}" for n in obj_names]
    header += ["RankSum"]

    with open(path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(header)

        for i in range(len(X)):
            row = []

            # 1) Entscheidungsvariablen
            row += [decoded[i][k] for k in decision_keys]

            # 2) Zusatzgrößen (NICHT Teil von F!)
            eval_result = evaluator.evaluate(X[i])
            row += [eval_result.capex_brutto]
            row += [eval_result.subsidy_stage]

            # 3) Zielfunktionen (genau in dieser Reihenfolge!)
            # F[:,0]=CAPEX_eff, F[:,1]=Q_new_total, ...
            row += list(F[i])

            # 4) spezifische Zielfunktionen
            row += list(F[i] / A_ref)

            # 5) Ränge
            row += list(ranks[i])
            row += [int(rank_sum[i])]

            writer.writerow(row)




    return path


# =====================================================================
# 5) EXCEL-EXPORT (OPTIONAL)
# =====================================================================

def export_pareto_excel(
    X: np.ndarray,
    F: np.ndarray,
    params: dict,
    var_names: List[str],
    obj_names: List[str],
    base_filename: str = "Pareto_Optimierung",
    folder: str = "output",
    top_k: int = 10
) -> Optional[str]:
    """
    Exportiert Pareto-Lösungen als Excel-Datei (.xlsx).
    Falls openpyxl nicht installiert ist, wird None zurückgegeben.
    """
    if openpyxl is None:
        return None

    path = get_next_filename(base_filename, folder, ".xlsx")

    ranks, rank_sum = compute_ranks(F)
    A_ref = float(params.get("A_ref", 1.0))

    from optimization.evaluator import ModelEvaluator
    evaluator = ModelEvaluator(params)
    decoded = [decision_vector_to_dict(decode_x(x)) for x in X]
    decision_keys = list(decoded[0].keys())

    header = []
    header += decision_keys
    header += ["CAPEX_brutto", "subsidy_stage"]
    header += obj_names
    header += [f"{n}_spec" for n in obj_names]
    header += [f"Rank_{n}" for n in obj_names]
    header += ["RankSum"]

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Pareto_All"
    ws.append(header)


    for i in range(len(X)):
        row = []

        row += [decoded[i][k] for k in decision_keys]

        eval_result = evaluator.evaluate(X[i])
        row += [eval_result.capex_brutto]
        row += [eval_result.subsidy_stage]

        row += list(F[i])
        row += list(F[i] / A_ref)
        row += list(ranks[i])
        row += [int(rank_sum[i])]

        ws.append(row)



    wb.save(path)
    return path

# =====================================================================
# 5a) 2D-PARETO-PLOT (einheitlicher Stil)
# =====================================================================

def save_plot_2d(
    F: np.ndarray,
    ix: int,
    iy: int,
    xlabel: str,
    ylabel: str,
    name: str,
    folder: str = "output",
    top_k: int = 10
) -> str:
    """
    2D-Pareto-Plot zweier Zielfunktionen.

    Darstellung:
    - Alle Lösungen: grau, transparent
    - Top-k Lösungen (RankSum): blau hervorgehoben

    KEINE Modelllogik - reine Visualisierung.
    """

    # Ranking bestimmen
    ranks, rank_sum = compute_ranks(F)
    top_idx = get_top_k_indices(rank_sum, top_k)

    fig, ax = plt.subplots(figsize=(7, 5))

    # Alle Lösungen
    ax.scatter(
        F[:, ix], F[:, iy],
        s=PLOT_STYLE["all"]["size"],
        alpha=PLOT_STYLE["all"]["alpha"],
        color=PLOT_STYLE["all"]["color"]
    )

    # Top-k Lösungen
    ax.scatter(
        F[top_idx, ix], F[top_idx, iy],
        s=PLOT_STYLE["top"]["size"],
        alpha=PLOT_STYLE["top"]["alpha"],
        color=PLOT_STYLE["top"]["color"],
        edgecolors=PLOT_STYLE["top"]["edgecolor"]
    )

    extreme_idx = get_extreme_indices(F)

    for key, idx in extreme_idx.items():
        st = EXTREME_STYLE[key]

        ax.scatter(
            F[idx, ix], F[idx, iy],
            s=st["size"],
            color=st["color"],
            marker=st["marker"],
            edgecolors="black",
            linewidths=0.8,
            zorder=10  # Kritische Zeile: Extrempunkte liegen sichtbar über allen Punkten
        )

    # Achsenbeschriftung
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)

    # Tausendertrennung mit Punkt
    fmt = thousands_dot_formatter()
    ax.xaxis.set_major_formatter(fmt)
    ax.yaxis.set_major_formatter(fmt)

    ax.grid(True, alpha=0.45, linestyle="--")

    # Einheitliche Legende
    ax.legend(handles=get_extended_legend_handles(include_extremes=True))

    path = get_next_filename(name, folder, ".png")
    plt.tight_layout()
    plt.savefig(path, dpi=300)
    plt.close()
    return path

def save_plot_spec_2d(
    F: np.ndarray,
    A_ref: float,
    ix: int,
    iy: int,
    labels_spec: list,
    name: str,
    folder: str = "output",
    top_k: int = 10
) -> str:
    """
    2D-Pareto-Plot zweier Zielfunktionen (spezifische Werte /m²).

    Darstellung:
    - Alle Lösungen: grau
    - Top-k Lösungen (RankSum): blau hervorgehoben
    - Extrempunkte der einzelnen Zielfunktionen

    KEINE Modelllogik - reine Visualisierung.
    """

    # Spezifische Werte
    F_spec = F / float(A_ref)

    # Ranking (immer auf Basis der absoluten Zielfunktionen!)
    ranks, rank_sum = compute_ranks(F)
    top_idx = get_top_k_indices(rank_sum, top_k)

    fig, ax = plt.subplots(figsize=(7, 5))

    # Alle Lösungen
    ax.scatter(
        F_spec[:, ix], F_spec[:, iy],
        s=PLOT_STYLE["all"]["size"],
        alpha=PLOT_STYLE["all"]["alpha"],
        color=PLOT_STYLE["all"]["color"]
    )

    # Top-k Lösungen
    ax.scatter(
        F_spec[top_idx, ix], F_spec[top_idx, iy],
        s=PLOT_STYLE["top"]["size"],
        alpha=PLOT_STYLE["top"]["alpha"],
        color=PLOT_STYLE["top"]["color"],
        edgecolors=PLOT_STYLE["top"]["edgecolor"]
    )

    # Extrempunkte (Index aus F, Darstellung aus F_spec)
    extreme_idx = get_extreme_indices(F)
    for key, idx in extreme_idx.items():
        st = EXTREME_STYLE[key]
        ax.scatter(
            F_spec[idx, ix], F_spec[idx, iy],
            s=st["size"],
            color=st["color"],
            marker=st["marker"],
            edgecolors="black",
            linewidths=0.8,
            zorder=10
        )

    # Achsenbeschriftung aus labels_spec
    ax.set_xlabel(labels_spec[ix])
    ax.set_ylabel(labels_spec[iy])

    # Formatierung
    fmt = thousands_dot_formatter()
    ax.xaxis.set_major_formatter(fmt)
    ax.yaxis.set_major_formatter(fmt)
    ax.grid(True, alpha=0.45, linestyle="--")

    ax.legend(handles=get_extended_legend_handles(include_extremes=True))

    path = get_next_filename(name, folder, ".png")
    plt.tight_layout()
    plt.savefig(path, dpi=300)
    plt.close()

    return path

# =====================================================================
# 5b) 3D-PARETO-PLOT (einheitlicher Stil + optional Farbcodierung für 4. Zielfunktion)
# =====================================================================

def save_plot_3d( 
    F: np.ndarray,
    ix: int,
    iy: int,
    iz: int,
    xl: str,
    yl: str,
    zl: str,
    name: str,
    folder: str = "output",
    top_k: int = 10
) -> str:
    """
    Klassischer 3D-Pareto-Plot (ohne Farbcodierung).

    Darstellung:
    - Alle Lösungen: grau, transparent
    - Top-k Lösungen: blau hervorgehoben

    KEINE Modelllogik - reine Visualisierung.
    """

    from mpl_toolkits.mplot3d import Axes3D  # noqa

    ranks, rank_sum = compute_ranks(F)
    top_idx = get_top_k_indices(rank_sum, top_k)

    fig = plt.figure(figsize=(8, 6))
    ax = fig.add_subplot(111, projection="3d")

    # Alle Lösungen
    ax.scatter(
        F[:, ix], F[:, iy], F[:, iz],
        s=PLOT_STYLE["all"]["size"],
        alpha=PLOT_STYLE["all"]["alpha"],
        color=PLOT_STYLE["all"]["color"]
    )

    # Top-k Lösungen
    ax.scatter(
        F[top_idx, ix], F[top_idx, iy], F[top_idx, iz],
        s=PLOT_STYLE["top"]["size"],
        alpha=PLOT_STYLE["top"]["alpha"],
        color=PLOT_STYLE["top"]["color"],
        edgecolors=PLOT_STYLE["top"]["edgecolor"]
    )
    # =====================================================================
    # 4.5) Extrempunkte in 3D markieren
    # =====================================================================

    extreme_idx = get_extreme_indices(F)

    for key, idx in extreme_idx.items():
        st = EXTREME_STYLE[key]

        ax.scatter(
            F[idx, ix], F[idx, iy], F[idx, iz],
            s=st["size"],
            color=st["color"],
            marker=st["marker"],
            edgecolors="black",
            linewidths=0.8,
            zorder=10
        )

    ax.set_xlabel(xl)
    ax.set_ylabel(yl)
    ax.set_zlabel(zl)

    ax.legend(handles=get_extended_legend_handles(include_extremes=True), loc="best")

    path = get_next_filename(name, folder, ".png")
    plt.tight_layout()
    plt.savefig(path, dpi=300)
    plt.close()
    return path


def save_plot_3d_colored(
    F: np.ndarray,
    ix: int,
    iy: int,
    iz: int,
    ic: int,
    labels: list,
    name: str = "Pareto_3D_colored",
    folder: str = "output",
    top_k: int = 10,
    cmap: str = "viridis"
):
    """
    3D-Pareto-Plot mit Farbcodierung einer vierten Zielfunktion.

    Darstellung:
    - Achsen: F[:, ix], F[:, iy], F[:, iz]
    - Farbe: F[:, ic] (z.B. CO2)
    - Alle Lösungen: klein, transparent
    - Top-k Lösungen (RankSum): größer, schwarze Kante

    KEINE Modelllogik - reine Visualisierung.
    """

    from mpl_toolkits.mplot3d import Axes3D  # noqa
    from utils.export import compute_ranks, get_top_k_indices

    # -------------------------------------------------------------
    # Ranking für Top-k bestimmen
    # -------------------------------------------------------------
    ranks, rank_sum = compute_ranks(F)
    top_idx = get_top_k_indices(rank_sum, top_k)

    # -------------------------------------------------------------
    # Figure & 3D-Achse
    # -------------------------------------------------------------
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection="3d")

    # -------------------------------------------------------------
    # Alle Lösungen (Hintergrund)
    # -------------------------------------------------------------
    sc_all = ax.scatter(
        F[:, ix], F[:, iy], F[:, iz],
        c=F[:, ic],
        cmap=cmap,
        s=PLOT_STYLE["all"]["size"],
        alpha=PLOT_STYLE["all"]["alpha"]
    )

    # -------------------------------------------------------------
    # Top-k Lösungen hervorheben
    # -------------------------------------------------------------
    ax.scatter(
        F[top_idx, ix], F[top_idx, iy], F[top_idx, iz],
        c=F[top_idx, ic],
        cmap=cmap,
        s=PLOT_STYLE["top"]["size"],
        alpha=PLOT_STYLE["top"]["alpha"],
        edgecolors=PLOT_STYLE["top"]["edgecolor"]
    )

    # -------------------------------------------------------------
    # Achsenbeschriftungen
    # -------------------------------------------------------------
    ax.set_xlabel(labels[ix])
    ax.set_ylabel(labels[iy])
    ax.set_zlabel(labels[iz])

    # -------------------------------------------------------------
    # Farbskala (Colorbar)
    # -------------------------------------------------------------
    cbar = fig.colorbar(sc_all, ax=ax, pad=0.1)
    cbar.set_label(labels[ic])

    # -------------------------------------------------------------
    # Einheitliche Legende (Form erklärt, Farbe über Colorbar)
    # -------------------------------------------------------------
    ax.legend(
        handles=get_extended_legend_handles(include_extremes=False),
        loc="best"
    )

    # -------------------------------------------------------------
    # Speichern
    # -------------------------------------------------------------
    path = get_next_filename(name, folder, ".png")
    plt.tight_layout()
    plt.savefig(path, dpi=300)
    plt.close()
    return path

# =====================================================================
# 6) GLOBALE + ZOOM-PLOT-MATRIX (SPEZIFISCH /m²)
# =====================================================================

def save_plot_matrix(
    F: np.ndarray,
    labels: List[str],
    name: str = "Pareto_Matrix",
    folder: str = "output",
    bins: int = 20,
    show_diagonal_identity: bool = False


) -> str:
    """
    Globale 4x4 Plot-Matrix (ohne Zoom).

    Darstellung:
    -  Scatter (alle Lösungen + Top-k Hervorhebung)

    Hinweis:
    - Diese Matrix dient als Überblick über die Gesamtstreuung der Pareto-Menge.
    - Die Zoom-Matrix ergänzt diese Darstellung für Detailunterschiede.
    """

    # Ranking für Top-k bestimmen
    ranks, rank_sum = compute_ranks(F)
    top_idx = get_top_k_indices(rank_sum, k=10)

    fmt = thousands_dot_formatter()

    n_obj = F.shape[1]
    fig, axes = plt.subplots(n_obj, n_obj, figsize=(12, 12))

    for i in range(n_obj):
        for j in range(n_obj):
            ax = axes[i, j]

            # Alle Lösungen (Hintergrund)

            ax.scatter(
                F[:, j], F[:, i],
                s=PLOT_STYLE["all"]["size"],
                alpha=PLOT_STYLE["all"]["alpha"],
                color=PLOT_STYLE["all"]["color"]
            )

            # Top-k Lösungen (Hervorhebung)

            ax.scatter(
                F[top_idx, j], F[top_idx, i],
                s=PLOT_STYLE["top"]["size"],
                alpha=PLOT_STYLE["top"]["alpha"],
                color=PLOT_STYLE["top"]["color"],
                edgecolors=PLOT_STYLE["top"]["edgecolor"]
            )

            # ---------------------------------------------------------
            # Diagonale mit Referenzlinie (x=y)
            # ---------------------------------------------------------
            if show_diagonal_identity and i == j:
                vmin = np.min(F[:, i])
                vmax = np.max(F[:, i])
                ax.plot([vmin, vmax], [vmin, vmax], linestyle="--", linewidth=1, color="#666666", alpha=0.6)
            # =====================================================================
            # 4.6) Extrempunkte in der Plot-Matrix markieren
            # =====================================================================

            extreme_idx = get_extreme_indices(F)  # einmalig vor den Schleifen berechnen!

            # ... innerhalb jeder Subplot-Achse ax:

            for key, idx in extreme_idx.items():
                st = EXTREME_STYLE[key]
                ax.scatter(
                    F[idx, j], F[idx, i],
                    s=st["size"],
                    color=st["color"],
                    marker=st["marker"],
                    edgecolors="black",
                    linewidths=0.6,
                    zorder=10
                )
            # Tick-Formatierung (Tausenderpunkt)
            ax.xaxis.set_major_formatter(fmt)
            ax.yaxis.set_major_formatter(fmt)

            # Achsenlabels nur außen
            if i == n_obj - 1:
                ax.set_xlabel(labels[j])
            else:
                ax.set_xticklabels([])

            if j == 0:
                ax.set_ylabel(labels[i])
            else:
                ax.set_yticklabels([])

            ax.grid(True, alpha=0.2)

    # Einheitliche Legende (nur einmal pro Figure)
    fig.legend(
        handles=get_extended_legend_handles(include_extremes=True),
        loc="lower center",
        ncol=2,
        frameon=True
    )

    plt.tight_layout(rect=[0, 0.05, 1, 1])
    path = get_next_filename(name, folder, ".png")
    plt.savefig(path, dpi=300)
    plt.close()
    return path

def save_plot_matrix_specific(
    F: np.ndarray,
    labels: List[str],
    A_ref: float,
    name: str = "Pareto_Matrix_Specific",
    folder: str = "output",
    **kwargs
) -> str:
    """
    Globale 4x4 Plot-Matrix mit spezifischen Kennwerten (/m²).

    Funktionsweise:
    - Umrechnung aller Zielfunktionen auf spezifische Werte:
        F_spec = F / A_ref
    - Weiterleitung an save_plot_matrix (globale Darstellung)

    Zweck:
    - Vergleichbarkeit unabhängig von der Gebäudegröße
    - Normnahe Darstellung (z. B. kWh/(m²*a), €/m²)

    KEINE Modelllogik:
    - Es erfolgt ausschließlich eine lineare Skalierung
      der bereits berechneten Zielfunktionen.
    """

    # -------------------------------------------------------------
    # Sicherheitsprüfung: Bezugsfläche
    # -------------------------------------------------------------
    if A_ref <= 0:
        raise ValueError("A_ref muss größer als 0 sein für spezifische Werte.")

    # -------------------------------------------------------------
    # Umrechnung auf spezifische Werte (/m²)
    # -------------------------------------------------------------
    F_spec = F / float(A_ref)

    # -------------------------------------------------------------
    # Achsenbeschriftungen anpassen
    # -------------------------------------------------------------
    labels_spec = [f"{label}" for label in labels]

    # -------------------------------------------------------------
    # Aufruf der globalen Matrixfunktion
    # -------------------------------------------------------------
    return save_plot_matrix(
        F=F_spec,
        labels=labels_spec,
        name=name,
        folder=folder,
        **kwargs
    )

def save_plot_matrix_zoomed(
    F: np.ndarray,
    labels: List[str],
    name: str = "Pareto_Matrix_Zoom",
    folder: str = "output",
    top_k: int = 10,
    margin: float = 0.15,
    show_diagonal_identity: bool = False

) -> str:
    """
    Gezoomte 4x4 Pareto-Plot-Matrix (absolute Werte).
    Zoom-Bereich wird aus Top-k Lösungen bestimmt.
    """

    ranks, rank_sum = compute_ranks(F)
    top_idx = get_top_k_indices(rank_sum, top_k)

    mins = F[top_idx].min(axis=0)
    maxs = F[top_idx].max(axis=0)
    span = maxs - mins

    xmin = mins - margin * span
    xmax = maxs + margin * span

    fmt = thousands_dot_formatter()

    fig, axes = plt.subplots(F.shape[1], F.shape[1], figsize=(12, 12))

    for i in range(F.shape[1]):
        for j in range(F.shape[1]):
            ax = axes[i, j]

            ax.scatter(
                F[:, j], F[:, i],
                s=PLOT_STYLE["all"]["size"],
                alpha=PLOT_STYLE["all"]["alpha"],
                color=PLOT_STYLE["all"]["color"]
            )

            ax.scatter(
                F[top_idx, j], F[top_idx, i],
                s=PLOT_STYLE["top"]["size"],
                alpha=PLOT_STYLE["top"]["alpha"],
                color=PLOT_STYLE["top"]["color"],
                edgecolors=PLOT_STYLE["top"]["edgecolor"]
            )
            # =====================================================================
            # 4.6) Extrempunkte in der Plot-Matrix markieren
            # =====================================================================

            extreme_idx = get_extreme_indices(F)  # einmalig vor den Schleifen berechnen!

            # ... innerhalb jeder Subplot-Achse ax:

            for key, idx in extreme_idx.items():
                st = EXTREME_STYLE[key]
                ax.scatter(
                    F[idx, j], F[idx, i],
                    s=st["size"],
                    color=st["color"],
                    marker=st["marker"],
                    edgecolors="black",
                    linewidths=0.6,
                    zorder=10
                )

            # ---------------------------------------------------------
            # Diagonale mit Referenzlinie (x=y)
            # ---------------------------------------------------------
            if show_diagonal_identity and i == j:
                vmin = np.min(F[:, i])
                vmax = np.max(F[:, i])
                ax.plot([vmin, vmax], [vmin, vmax], linestyle="--", linewidth=1, color="#666666", alpha=0.6)

            ax.set_xlim(xmin[j], xmax[j])
            ax.set_ylim(xmin[i], xmax[i])

            ax.xaxis.set_major_formatter(fmt)
            ax.yaxis.set_major_formatter(fmt)

            if i == F.shape[1] - 1:
                ax.set_xlabel(labels[j])
            else:
                ax.set_xticklabels([])

            if j == 0:
                ax.set_ylabel(labels[i])
            else:
                ax.set_yticklabels([])

            ax.grid(True, alpha=0.3)

    fig.legend(
        handles=get_extended_legend_handles(include_extremes=True),
        loc="lower center",
        ncol=2,
        frameon=True
    )

    plt.tight_layout(rect=[0, 0.05, 1, 1])
    path = get_next_filename(name, folder, ".png")
    plt.savefig(path, dpi=300)
    plt.close()
    return path

def save_plot_matrix_zoomed_specific(
    F: np.ndarray,
    labels: List[str],
    A_ref: float,
    name: str = "Pareto_Matrix_Zoom_Specific",
    **kwargs
) -> str:
    """
    Gezoomte Pareto-Plot-Matrix mit spezifischen Kennwerten (/m²).
    """
    F_spec = F / float(A_ref)
    labels_spec = [f"{l}" for l in labels]

    return save_plot_matrix_zoomed(
        F=F_spec,
        labels=labels_spec,
        name=name,
        **kwargs
    )
