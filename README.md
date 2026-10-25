# Angul solar employment-effort model: evidence package (CM 617)

## Folder contents
- `data/input_*.csv`   : every input number, with source document and page
- `data/output_*.csv`  : model outputs (scenario grid, static estimate at s=1, skill mix); `output_console_log.txt` is the full run log
- `code/angul_solar_employment.py` : main model + figures (numpy/pandas/matplotlib)
- `code/verify_independent.py`     : independent check (see below)
- `source_pages/`      : screenshots of the exact source pages the inputs were read from
- `fig1..3_*.png`      : report figures

## How to run
    pip install numpy pandas matplotlib
    cd code
    python angul_solar_employment.py     # reproduces tables + figures (written to the current folder)
    python verify_independent.py         # prints ALL CHECKS PASSED if everything reconciles

## Where the inputs come from (page numbers = printed page numbers)
| Input | Source | Location |
|---|---|---|
| 934 / 4,646 / 1,925 / 3,300 MW (total 10,805) | iFOREST (2022) Angul report | Table 8, p.107 |
| Floating-solar method, Rengali 300 MW phase 1 | same | p.106 |
| Coal workforce by category (168,721; 116,493 informal) | same | Table 8, p.69 |
| Phase coefficients, ground-mounted | CEEW-NRDC (2026) | Fig 4, p.17 (PDF page 33) |
| Phase coefficients, floating | CEEW-NRDC (2026) | Fig 5, p.17 (PDF page 33) |
| Skill shares by phase | CEEW-NRDC (2026) | Figs 7-8, p.19 (PDF page 35) |
| Sample sizes (19 ground, 3 floating) | CEEW-NRDC (2026) | Table 3, p.10 (PDF page 26) |

## What the verification script checks
1. CSV inputs equal the values hard-coded in the model; coefficient totals are 1.00 and 2.21; skill rows sum to 100; coal rows add up (formal + informal = total).
2. A second, plain-Python implementation of the timeline model reproduces all 12 scenarios.
3. Closed-form formulas agree: one-off = s*sum(P*(b_BD+b_D+b_C)); O&M plateau = s*sum(P*b_OM) for T<=25, scaled by 25/T for T>25; lifetime = one-off + 25*O&M.
4. Every number quoted in the report text (J_total, shares, sensitivities, skill percentages, coal ratios, Rengali check) is recomputed.

## Known limits (please read)
- The inputs are published numbers; the *model assumptions* are ours, not the sources': rollout evenly over T years, BD 2 yrs / design 1 yr before commissioning, O&M coefficient read as FTE per operating year, 25-year O&M life with no repowering, +-30% sensitivity. They are listed in the report's assumptions table.
- iFOREST Table 8 (p.69): category rows sum to 168,722 total and 116,494 informal versus printed 168,721 and 116,493. This is rounding inside the source; we use the printed totals.
- Floating-solar coefficients rest on 3 companies (CEEW-NRDC Table 3).
- The checks prove the arithmetic and the transcription of inputs; they do not prove that the assumptions are right.
