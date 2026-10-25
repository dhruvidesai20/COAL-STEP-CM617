"""
Solar employment effort for Angul, Odisha -- scenario model (CM 617)
Sources (all secondary, as in main.tex):
  P_k  : iFOREST (2022) Angul report, Table 8, p.107  (assessed potential, MW)
  beta : CEEW-NRDC (2026) Driving Energy Transition, Figs 4-5 (FTE job-years/MW)
  skill: CEEW-NRDC (2026) Figs 7-8 (% highly/semi/low-skilled by phase)
  coal : iFOREST (2022) Angul report, Table 8, p.69 (direct coal dependence, context only)
"""
import numpy as np, pandas as pd, json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---------------- inputs ----------------
P = {"ground": 7505.0, "floating": 3300.0}            # MW  (934+4646+1925 ; 3300)
PHASES = ["BD", "Design", "Construction", "O&M"]
BETA = {                                              # FTE job-years / MW
    "ground":   dict(zip(PHASES, [0.18, 0.11, 0.45, 0.26])),
    "floating": dict(zip(PHASES, [0.05, 0.18, 0.58, 1.40])),
}
SKILL = {  # % (highly, semi, low)
    "ground":   {"BD": (48,52,0), "Design": (38,62,0), "Construction": (11,30,59), "O&M": (16,32,52)},
    "floating": {"BD": (48,52,0), "Design": (54,46,0), "Construction": (11,34,55), "O&M": (27,31,42)},
}
SHARES = [0.25, 0.50, 0.75, 1.00]
PERIODS = [10, 20, 30]
LIFE = 25      # years of O&M per cohort (CEEW-NRDC: 25-30 yr plant life for ground-mounted); no repowering
LEAD = {"BD": 2, "Design": 1, "Construction": 0}   # phase happens LEAD years before commissioning year
COAL_DIRECT = dict(total=168721, formal=52228, informal=116493)   # Angul 2022, Table 8 p.69

assert abs(sum(BETA["ground"].values()) - 1.00) < 1e-9
assert abs(sum(BETA["floating"].values()) - 2.21) < 1e-9
assert P["ground"] == 934 + 4646 + 1925 and P["ground"] + P["floating"] == 10805

# ---------------- static estimate  J_{k,p} = C_{k,s} * beta_{k,p} ----------------
def static(s, beta=BETA, P=P):
    rows = []
    for k in P:
        C = s * P[k]
        for p in PHASES:
            rows.append(dict(tech=k, phase=p, C_MW=C, beta=beta[k][p], J=C * beta[k][p]))
    return pd.DataFrame(rows)

# ---------------- dynamic profile ----------------
def profile(s, T, beta=BETA, P=P, life=LIFE, shares=None):
    """Annual FTE by tech & category. Year 1..T = commissioning years (dC = sP/T per year).
    BD / design occur LEAD years earlier; O&M runs for `life` years starting the year after commissioning."""
    yrs = np.arange(-2, T + life + 2)
    idx = {y: i for i, y in enumerate(yrs)}
    out = {}
    for k in P:
        dC = s * P[k] / T
        arr = {p: np.zeros(len(yrs)) for p in PHASES}
        for c in range(1, T + 1):                    # cohort commissioned in year c
            for p in ("BD", "Design", "Construction"):
                arr[p][idx[c - LEAD[p]]] += dC * beta[k][p]
            for y in range(c + 1, c + life + 1):
                arr["O&M"][idx[y]] += dC * beta[k]["O&M"]
        out[k] = arr
    return yrs, out

def summarise(s, T, **kw):
    yrs, out = profile(s, T, **kw)
    oneoff = sum(out[k][p] for k in out for p in ("BD", "Design", "Construction"))
    om = sum(out[k]["O&M"] for k in out)
    tot = oneoff + om
    rollout = (yrs >= 1) & (yrs <= T)
    return dict(share=s, T=T,
                cap_MW=s * sum(P.values()),
                oneoff_jy=oneoff.sum(), om_peak_FTE=om.max(), om_jy_life=om.sum(),
                lifetime_jy=tot.sum(), peak_total_FTE=tot.max(),
                mean_oneoff_FTE_per_yr=oneoff.sum() / T,
                peak_oneoff_FTE=oneoff.max())

if __name__ == "__main__":
    # ---- Table A: full-potential static estimate (s=1) ----
    A = static(1.0)
    pivA = A.pivot(index="phase", columns="tech", values="J").loc[PHASES]
    pivA["total"] = pivA.sum(axis=1)
    pivA.loc["Total"] = pivA.sum()
    print("\nTable A  J_{k,p} at s=1.00 (FTE job-years; O&M row = FTE per operating year)\n", pivA.round(1))

    oneoff_g = pivA.loc[["BD","Design","Construction"],"ground"].sum()
    oneoff_f = pivA.loc[["BD","Design","Construction"],"floating"].sum()
    print("one-off job-years  ground %.1f  floating %.1f  total %.1f" % (oneoff_g, oneoff_f, oneoff_g+oneoff_f))
    print("steady O&M FTE     ground %.1f  floating %.1f  total %.1f" % (pivA.loc["O&M","ground"], pivA.loc["O&M","floating"], pivA.loc["O&M","total"]))
    mw_share_f = P["floating"]/sum(P.values())
    print("floating share of MW %.1f%% ; of J_total %.1f%% ; of O&M FTE %.1f%%" % (
        100*mw_share_f, 100*pivA.loc["Total","floating"]/pivA.loc["Total","total"], 100*pivA.loc["O&M","floating"]/pivA.loc["O&M","total"]))
    all_ground = sum(P.values()) * 1.0
    print("if all 10,805 MW used ground-mounted beta: %.0f  vs mix %.0f (+%.0f%%)" % (all_ground, pivA.loc["Total","total"], 100*(pivA.loc["Total","total"]/all_ground-1)))

    # ---- Table B: scenario grid ----
    grid = pd.DataFrame([summarise(s, T) for s in SHARES for T in PERIODS])
    pd.set_option("display.width", 200)
    print("\nTable B scenario grid\n", grid.round({"share":2,"cap_MW":0,"oneoff_jy":0,"om_peak_FTE":0,"om_jy_life":0,"lifetime_jy":0,"peak_total_FTE":0,"mean_oneoff_FTE_per_yr":0,"peak_oneoff_FTE":0}).astype({"T":int}).to_string(index=False))
    grid.to_csv("scenario_grid.csv", index=False)
    pivA.to_csv("static_estimate_s1.csv")

    # ---- Pipeline-anchored check: floating limited to Rengali phase-1 300 MW (Angul report p.106) ----
    P_pipe = {"ground": P["ground"] * 0.5, "floating": 300.0}
    sp = static(1.0, P=P_pipe)
    print("\nPipeline-anchored check (50%% ground, floating=300 MW): oneoff %.0f jy ; O&M %.0f FTE" % (
        sp[sp.phase != "O&M"].J.sum(), sp[sp.phase == "O&M"].J.sum()))

    # ---- Skill composition of steady-state O&M and of one-off effort (s=1) ----
    sk_rows = []
    for k in P:
        for p in PHASES:
            J = P[k] * BETA[k][p]
            h, m, l = SKILL[k][p]
            sk_rows.append(dict(tech=k, phase=p, J=J, high=J*h/100, semi=J*m/100, low=J*l/100))
    SK = pd.DataFrame(sk_rows)
    SK["group"] = np.where(SK.phase == "O&M", "O&M (recurring)", "Development+construction (one-off)")
    skg = SK.groupby("group")[["J","high","semi","low"]].sum()
    skg_pct = skg[["high","semi","low"]].div(skg.J, axis=0) * 100
    print("\nSkill mix (s=1), %:\n", skg_pct.round(1))
    sk_tech = SK[SK.phase=="O&M"].groupby("tech")[["J","high","semi","low"]].sum()
    print("\nO&M FTE by skill (s=1):\n", sk_tech.round(0))
    skg.to_csv("skill_mix_s1.csv")

    # ---- Context: scale vs. coal direct dependence (units differ -> indicative only) ----
    g1 = summarise(1.0, 20)
    print("\nContext: peak annual FTE (s=1,T=20) = %.0f ; = %.1f%% of 168,721 direct coal-dependent workers (not like-for-like)" % (
        g1["peak_total_FTE"], 100*g1["peak_total_FTE"]/COAL_DIRECT["total"]))
    print("informal coal workers (Angul 2022 T8):", COAL_DIRECT["informal"], "=", round(100*COAL_DIRECT["informal"]/COAL_DIRECT["total"],1), "%")
    print("max solar O&M FTE vs coal-mining informal+all: ", pivA.loc["O&M","total"]/COAL_DIRECT["total"]*100)

    # ======================= FIGURES =======================
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                         "figure.dpi": 150, "savefig.bbox": "tight"})
    C_OM, C_G, C_F = "#1b7837", "#d6604d", "#4393c3"

    # ---- Figure 1: annual profile across rollout scenarios (central s=0.50) ----
    s0 = 0.50
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.2), sharey=True)
    for ax, T in zip(axes, PERIODS):
        yrs, out = profile(s0, T)
        base = sum(out[k][p] for k in out for p in ("BD","Design","Construction"))
        om = sum(out[k]["O&M"] for k in out)
        ax.stackplot(yrs, base, om, colors=["#d6604d", "#1b7837"], alpha=.9,
                     labels=["Development + construction (one-off)", "O&M (recurring)"])
        ax.set_title(f"T = {T} yr", fontsize=9)
        ax.set_xlabel("Year (1 = first commissioning)")
        ax.axvspan(1, T, color="grey", alpha=.08, lw=0)
    axes[0].set_ylabel("FTE per year (job-years/yr)")
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=2, frameon=False, bbox_to_anchor=(.5, -.1))
    fig.suptitle("Annual employment effort, s = 0.50 (5,403 MW); shaded = rollout period", fontsize=9, y=1.02)
    fig.tight_layout(); fig.savefig("fig1_annual_profile.png"); fig.savefig("fig1_annual_profile.pdf")

    # ---- Figure 2: sensitivity (a) share x technology ; (b) coefficient tornado ----
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.2, 2.5), gridspec_kw={"width_ratios": [1, 1.25]})
    x = np.arange(len(SHARES)); w = .38
    for i, kind in enumerate(["oneoff", "om"]):
        gv = [static(s).query("tech=='ground'").pipe(lambda d: d[d.phase != "O&M"].J.sum() if kind=="oneoff" else d[d.phase=="O&M"].J.sum()) for s in SHARES]
        fv = [static(s).query("tech=='floating'").pipe(lambda d: d[d.phase != "O&M"].J.sum() if kind=="oneoff" else d[d.phase=="O&M"].J.sum()) for s in SHARES]
        pos = x + (i - .5) * w
        a.bar(pos, gv, w*.95, color=C_G, label="Ground-mounted" if i==0 else None, hatch="" if kind=="oneoff" else "//", edgecolor="white")
        a.bar(pos, fv, w*.95, bottom=gv, color=C_F, label="Floating" if i==0 else None, hatch="" if kind=="oneoff" else "//", edgecolor="white")
    a.set_xticks(x); a.set_xticklabels([f"{int(s*100)}%" for s in SHARES])
    a.set_xlabel("Share of assessed potential developed (s)"); a.set_ylabel("FTE job-years  /  FTE")
    a.set_title("(a) Deployment share (left bar: one-off job-years;\nright hatched: steady O&M FTE)", fontsize=8)
    a.legend(frameon=False, fontsize=7, loc="upper left")

    base_tot = pivA.loc["Total","total"]
    labels, lo, hi = [], [], []
    for k in P:
        for p in PHASES:
            res = []
            for f in (0.7, 1.3):
                bb = {kk: dict(v) for kk, v in BETA.items()}
                bb[k][p] *= f
                res.append(static(1.0, beta=bb).J.sum() - base_tot)
            labels.append(f"{'Ground' if k=='ground' else 'Floating'}: {p}"); lo.append(res[0]); hi.append(res[1])
    order = np.argsort([abs(h_ - l_) for h_, l_ in zip(hi, lo)])
    for j, i in enumerate(order):
        b.barh(j, lo[i], color="#92c5de"); b.barh(j, hi[i], color="#f4a582")
    b.set_yticks(range(len(order))); b.set_yticklabels([labels[i] for i in order], fontsize=7)
    b.axvline(0, color="k", lw=.6)
    b.set_xlabel(f"Change in $J_{{total}}$ (base {base_tot:,.0f}), ±30% on one $\\beta$", fontsize=8)
    b.set_title("(b) Coefficient sensitivity, s = 1.00", fontsize=8)
    fig.tight_layout(); fig.savefig("fig2_sensitivity.png"); fig.savefig("fig2_sensitivity.pdf")

    # ---- Figure 3 (supplementary): skill mix ----
    fig, ax = plt.subplots(figsize=(5.2, 2.0))
    cats = [("Ground: dev.+constr.", "ground", False), ("Ground: O&M", "ground", True),
            ("Floating: dev.+constr.", "floating", False), ("Floating: O&M", "floating", True)]
    for j, (lab, k, om_) in enumerate(cats):
        d = SK[(SK.tech == k) & ((SK.phase == "O&M") == om_)]
        v = d[["high","semi","low"]].sum() / d.J.sum() * 100
        left = 0
        for val, col, nm in zip(v, ["#7b3294", "#c2a5cf", "#e0e0e0"], ["Highly skilled","Semi-skilled","Low-skilled"]):
            ax.barh(j, val, left=left, color=col, label=nm if j == 0 else None, edgecolor="white")
            if val > 6: ax.text(left + val/2, j, f"{val:.0f}", ha="center", va="center", fontsize=7)
            left += val
    ax.set_yticks(range(4)); ax.set_yticklabels([c[0] for c in cats], fontsize=8); ax.invert_yaxis()
    ax.set_xlabel("% of FTE"); ax.legend(ncol=3, frameon=False, fontsize=7, loc="lower center", bbox_to_anchor=(.5, 1.0))
    fig.savefig("fig3_skill_mix.png"); fig.savefig("fig3_skill_mix.pdf")

    # export key numbers for the report
    key = dict(oneoff_total=float(oneoff_g+oneoff_f), om_total=float(pivA.loc["O&M","total"]),
               J_total=float(pivA.loc["Total","total"]),
               skill_pct=skg_pct.round(1).to_dict())
    json.dump(key, open("key_numbers.json", "w"), indent=1)
