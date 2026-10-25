"""Independent re-check: (1) input CSVs match the model's hard-coded inputs and sums,
(2) a second, plain-Python implementation (no numpy/pandas) of the timeline model,
(3) closed-form formulas, (4) every number quoted in the report text."""
import csv, math, sys, os
sys.path.insert(0, os.path.dirname(__file__))
import angul_solar_employment as M

D = os.path.join(os.path.dirname(__file__), "..", "data")
rd = lambda f: list(csv.DictReader(open(os.path.join(D, f))))

# ---- (1) inputs from CSV == inputs inside model ----
cap = rd("input_capacity_iforest2022.csv")
g = sum(float(r["potential_MW"]) for r in cap if r["technology"] == "ground")
f = sum(float(r["potential_MW"]) for r in cap if r["technology"] == "floating")
assert (g, f) == (7505.0, 3300.0) and g + f == 10805
assert M.P == {"ground": g, "floating": f}
beta = {"ground": {}, "floating": {}}
key = {"Business development": "BD", "Design/pre-construction": "Design", "Construction/commissioning": "Construction", "O&M": "O&M"}
for r in rd("input_coefficients_ceew2026.csv"):
    beta[r["technology"]][key[r["phase"]]] = float(r["fte_job_years_per_MW"])
assert beta == M.BETA
assert round(sum(beta["ground"].values()), 2) == 1.00 and round(sum(beta["floating"].values()), 2) == 2.21
for r in rd("input_skill_shares_ceew2026.csv"):
    h, s, l = (float(r[k]) for k in ("highly_skilled_pct", "semi_skilled_pct", "low_skilled_pct"))
    assert h + s + l == 100, r
    assert M.SKILL[r["technology"]][key[r["phase"]]] == (h, s, l)
coal = {r["category"]: r for r in rd("input_coal_workforce_iforest2022.csv")}
body = [r for k, r in coal.items() if k != "Total"]
for col in ("total", "formal", "informal"):
    diff = sum(int(r[col]) for r in body) - int(coal["Total"][col])
    assert abs(diff) <= 1, col          # source Table 8 rows sum to 168,722 / 116,494 vs printed 168,721 / 116,493 (rounding in source)
    print("   note: Table 8 %s rows sum differs from printed total by %+d (source rounding)" % (col, diff))
for r in body:
    assert int(r["formal"]) + int(r["informal"]) == int(r["total"])
print("1. inputs OK (CSV == model; sums & row checks pass)")

# ---- (2) independent plain-python timeline ----
L, LEAD = 25, {"BD": 2, "Design": 1, "Construction": 0}
def sim(s, T):
    years = {}
    for k in ("ground", "floating"):
        dC = s * M.P[k] / T
        for c in range(1, T + 1):
            for p, lead in LEAD.items():
                years.setdefault(c - lead, [0.0, 0.0])[0] += dC * beta[k][p]
            for y in range(c + 1, c + L + 1):
                years.setdefault(y, [0.0, 0.0])[1] += dC * beta[k]["O&M"]
    oneoff = sum(v[0] for v in years.values()); om = [v[1] for v in years.values()]
    return oneoff, max(om), sum(om), max(v[0] + v[1] for v in years.values())
grid = {(round(float(r["share"]), 2), int(r["T"])): r for r in rd("output_scenario_grid.csv")}
for s in M.SHARES:
    for T in M.PERIODS:
        oo, omp, omlife, pk = sim(s, T)
        r = grid[(s, T)]
        assert math.isclose(oo, float(r["oneoff_jy"]), rel_tol=1e-9)
        assert math.isclose(omp, float(r["om_peak_FTE"]), rel_tol=1e-9)
        assert math.isclose(oo + omlife, float(r["lifetime_jy"]), rel_tol=1e-9)
        assert math.isclose(pk, float(r["peak_total_FTE"]), rel_tol=1e-9)
        # ---- (3) closed form ----
        oo_cf = s * sum(M.P[k] * (beta[k]["BD"] + beta[k]["Design"] + beta[k]["Construction"]) for k in M.P)
        om_cf = s * sum(M.P[k] * beta[k]["O&M"] for k in M.P)
        assert math.isclose(oo, oo_cf, rel_tol=1e-9)
        assert math.isclose(omp, om_cf * min(1, L / T), rel_tol=1e-9)
        assert math.isclose(omlife, om_cf * L, rel_tol=1e-9)
print("2-3. 12 scenarios: numpy model == plain-python model == closed form")

# ---- (4) numbers quoted in the report ----
def near(a, b, tol=0.5): assert abs(a - b) <= tol, (a, b)
oo = 1.0 * sum(M.P[k] * (beta[k]["BD"] + beta[k]["Design"] + beta[k]["Construction"]) for k in M.P)
om = sum(M.P[k] * beta[k]["O&M"] for k in M.P)
Jt = oo + om
near(Jt, 14798); near(oo, 8227); near(om, 6571)
near(M.P["ground"] * 1.00, 7505); near(M.P["floating"] * 2.21, 7293)
near(100 * M.P["floating"] / 10805, 30.5, .05)
near(100 * M.P["floating"] * 2.21 / Jt, 49.3, .05)
near(100 * M.P["floating"] * 1.40 / om, 70.3, .05)
near(100 * (1 - 10805 / Jt), 27, .5)
near(100 * om / 168721, 3.9, .05); near(100 * om / 116493, 5.6, .05)
near(100 * 5580 / 10805, 51.6, .05)
near(100 * 300 / 3300, 9.1, .05); near(300 * (0.05 + 0.18 + 0.58), 243, .5); near(300 * 1.40, 420, .5)
near(0.30 * M.P["floating"] * 1.40, 1386, .5); near(0.30 * M.P["ground"] * 0.45, 1013, .5)
near(100 * 1386 / Jt, 9.4, .05); near(100 * 1013 / Jt, 6.8, .05)
near(100 * (M.P["floating"] * 2.21 + M.P["ground"] * 1.0 - Jt), 0, 1e-6)
# lifetime split at s=1
life_f = M.P["floating"] * (0.05 + 0.18 + 0.58) + M.P["floating"] * 1.40 * L
life_g = M.P["ground"] * (0.18 + 0.11 + 0.45) + M.P["ground"] * 0.26 * L
near(life_f, 118173, 1); near(life_g, 54336, 1); near(life_f + life_g, 172509, 1)
near(100 * life_f / (life_f + life_g), 68.5, .05)
near(100 * (0.5 * om * L) / (0.5 * (oo + om * L)), 95.2, .1)
# skills (O&M, s=1)
def sk(tech_list, phases):
    tot = h = m = l = 0
    for k in tech_list:
        for p in phases:
            J = M.P[k] * beta[k][p]; a, b, c = M.SKILL[k][p]
            tot += J; h += J * a / 100; m += J * b / 100; l += J * c / 100
    return tot, h, m, l
t, h, m, l = sk(["ground", "floating"], ["O&M"])
near(100 * h / t, 23.7, .05); near(100 * m / t, 31.3, .05); near(100 * l / t, 45.0, .05)
near(h, 1559, 1); near(m, 2056, 1); near(l, 2955, 1)
t, h, m, l = sk(["ground", "floating"], ["BD", "Design", "Construction"])
near(100 * h / t, 23.6, .05); near(100 * m / t, 39.4, .05); near(100 * l / t, 37.0, .05)
print("4. all numbers quoted in the report reproduce")
print("ALL CHECKS PASSED")
