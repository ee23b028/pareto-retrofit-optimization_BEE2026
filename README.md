# Multi-Objective Optimization of Thermal Retrofit Strategies

##  Overview

This repository contains the implementation of a **Multi-Objective Optimization (MOO)** model developed as part of a Bachelor’s thesis.

The model is designed to evaluate thermal retrofit strategies for existing residential buildings while considering multiple conflicting objectives:

- Investment costs (CAPEX)
- Energy demand (Heating demand / HWB)
- CO₂ emissions
- Life-cycle costs (LCC)

The optimization is performed using the NSGA-II algorithm, generating a set of Pareto-optimal solutions that represent trade-offs between these objectives.

---

## Objective

The primary goal of this project is to support decision-making in building renovation by:

- identifying Pareto-optimal retrofit strategies
- making trade-offs between cost, energy, and environmental impact transparent
- providing a structured basis for evaluating different solutions

---

## Methodology

The optimization model follows a modular workflow:

1. Definition of input parameters (building characteristics, cost data, systems)
2. Generation of decision variables (retrofit measures and system configurations)
3. Evaluation of each solution:
   - Heating demand (HWB)
   - Life-cycle costs (LCC)
   - CO₂ emissions
4. Application of NSGA-II optimization
5. Generation of a Pareto-front
6. Ranking of solutions using RankSum (Borda Score)
7. Export and visualization of results

---

## Project Structure

project_root/
├── config/        → parameter & settings
├── domain/        → datatypes & structures
├── ecology/       → CO2 calculation
├── economics/     → (CAPEX, LCC)
├── model/         → energetical model
├── optimization/  → NSGA-II & evaluation
├── policy/        → subsidys
├── utils/         → export & visualization
├── output/        → results
└── init.py        → start of program

## full program Strukture
project_root/

├── config/
│   ├── parameters.py
│   └── optimization_settings.py
│
├── domain/
│   └── types.py
│
├── ecology/
│   ├── embodied.py
│   └── operational.py
│
├── economics/
│   ├── annual_costs.py
│   ├── capex_blocks.py
│   └── lcc_npy.py
│
├── model/
│   ├── demand.py
│   ├── envelope_losses.py
│   ├── envelope_u.py
│   ├── sizing.py
│   ├── system_energy.py
│   └── ventilation.py
│
├── optimization/
│   ├── decision_space.py
│   ├── evaluator.py
│   └── problems.py
│
├── policy/
│   ├── wwfsg_logic.py
│   └── wwfsg_calc.py
│
├── utils/
│   └── export.py
│
├── output/
│   └── (generated results)
│
└── init.py
