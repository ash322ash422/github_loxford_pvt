"""
demo_cta.py
-----------
LIVE DEMO for "Continuous Transaction Auditing" (1-hr session).
Run cell-by-cell (or top to bottom) in front of the audience.

Story arc:
  PART 0 — Load the full year of transactions (what a quarterly sample would
            have missed 96% of).
  PART 1 — Rule-based checks a rules engine can run on every single
            transaction, in real time, as it posts:
              1a. Benford's Law digit test
              1b. Duplicate payment detection
              1c. Just-below-approval-threshold clustering
              1d. Weekend / after-hours postings
              1e. Suspiciously round amounts
  PART 2 — Machine-learning layer: Isolation Forest flags multivariate
            outliers the simple rules miss (e.g. a new vendor paid an
            amount that's fine in isolation but abnormal for that vendor).
  PART 3 — Combine rule flags + ML score into a single risk-ranked worklist
            an auditor would triage — and reveal how many of the 145
            planted anomalies were caught.

Run: python3 demo_cta.py
Outputs: PNG charts in ./charts/ and a ranked worklist CSV in ./output/
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.ensemble import IsolationForest

# ----------------------------------------------------------------------
# Palette (fixed, validated — see workshop dataviz notes)
# ----------------------------------------------------------------------
INK = "#0b0b0b"
MUTED = "#898781"
GRID = "#e1e0d9"
SURFACE = "#fcfcfb"
BLUE = "#2a78d6"      # normal / categorical slot 1
RED = "#d03b3b"       # critical / flagged
ORANGE = "#eb6834"    # categorical slot 2
AQUA = "#1baf7a"       # categorical slot 3

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK,
    "text.color": INK, "xtick.color": MUTED, "ytick.color": MUTED,
    "grid.color": GRID, "font.size": 11,
})

os.makedirs("charts", exist_ok=True)
os.makedirs("output", exist_ok=True)

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 140)

print("=" * 70)
print("PART 0 — LOAD THE FULL YEAR OF TRANSACTIONS")
print("=" * 70)

df = pd.read_csv("data/transactions.csv", parse_dates=["posting_datetime"])
GROUND_TRUTH = df[["transaction_id", "is_planted_anomaly", "anomaly_type"]].copy()

# In a real engagement the auditor would NOT have these columns — drop them
# to analyze "blind", and only reattach at the very end to score ourselves.
work = df.drop(columns=["is_planted_anomaly", "anomaly_type"]).copy()

print(f"Total FY2025 transactions: {len(work):,}")
n_sample = round(len(work) * 0.04)
print(f"A typical quarterly-sample audit tests roughly {n_sample:,} of these "
      f"(~4% coverage) and never sees the other {len(work)-n_sample:,}.")
print()

# ------------------------------------------------------------------
# PART 1a — Benford's Law leading-digit test
# ------------------------------------------------------------------
print("=" * 70)
print("PART 1a — BENFORD'S LAW (leading first-digit test)")
print("=" * 70)

def leading_digit(x):
    x = abs(x)
    while x < 1:
        x *= 10
    return int(str(x)[0])

work["leading_digit"] = work["amount"].apply(leading_digit)
benford_expected = {d: np.log10(1 + 1 / d) for d in range(1, 10)}

observed = work["leading_digit"].value_counts(normalize=True).sort_index()
expected = pd.Series(benford_expected)

fig, ax = plt.subplots(figsize=(7, 4.2))
x = np.arange(1, 10)
width = 0.38
ax.bar(x - width / 2, [observed.get(d, 0) for d in x], width,
       label="Observed (all transactions)", color=BLUE)
ax.bar(x + width / 2, [expected[d] for d in x], width,
       label="Expected (Benford's Law)", color=MUTED)
ax.set_xticks(x)
ax.set_xlabel("Leading digit")
ax.set_ylabel("Proportion of transactions")
ax.set_title("Benford's Law: observed vs. expected leading-digit distribution")
ax.legend(frameon=False)
ax.grid(axis="y", linewidth=0.6)
for spine in ["top", "right"]:
    ax.spines[spine].set_visible(False)
fig.tight_layout()
fig.savefig("charts/01_benford_overall.png", dpi=150)
plt.close(fig)
print("Saved charts/01_benford_overall.png")

# Per-vendor Benford chi-square to isolate WHICH vendor is off
def benford_chi_square(amounts):
    digits = amounts.apply(leading_digit)
    obs_counts = digits.value_counts().reindex(range(1, 10), fill_value=0)
    n = obs_counts.sum()
    exp_counts = pd.Series({d: benford_expected[d] * n for d in range(1, 10)})
    chi2 = ((obs_counts - exp_counts) ** 2 / exp_counts).sum()
    return chi2, n

vendor_chi = []
for vid, grp in work.groupby("vendor_id"):
    if len(grp) < 15:
        continue  # need enough transactions for the test to be meaningful
    chi2, n = benford_chi_square(grp["amount"])
    vendor_chi.append((vid, grp["vendor_name"].iloc[0], n, chi2))

vendor_chi_df = pd.DataFrame(
    vendor_chi, columns=["vendor_id", "vendor_name", "n_transactions", "chi_square"]
).sort_values("chi_square", ascending=False)

print("\nTop 5 vendors by Benford chi-square (highest = most suspicious):")
print(vendor_chi_df.head(5).to_string(index=False))
flagged_vendors_benford = set(vendor_chi_df.head(3)["vendor_id"])
work["flag_benford_vendor"] = work["vendor_id"].isin(flagged_vendors_benford)
print()

# ------------------------------------------------------------------
# PART 1b — Duplicate payment detection
# ------------------------------------------------------------------
print("=" * 70)
print("PART 1b — DUPLICATE PAYMENT DETECTION")
print("=" * 70)

work_sorted = work.sort_values(["vendor_id", "amount", "posting_datetime"])
work["posting_date"] = work["posting_datetime"].dt.date
dupe_flags = set()
for (vid, amt), grp in work.groupby(["vendor_id", "amount"]):
    if len(grp) < 2:
        continue
    dates = grp.sort_values("posting_date")["posting_date"].tolist()
    ids = grp.sort_values("posting_date")["transaction_id"].tolist()
    for i in range(1, len(dates)):
        if (dates[i] - dates[i - 1]).days <= 3:
            dupe_flags.add(ids[i])
            dupe_flags.add(ids[i - 1])

work["flag_duplicate"] = work["transaction_id"].isin(dupe_flags)
print(f"Same vendor + same amount within 3 days: {work['flag_duplicate'].sum()} "
      f"transactions flagged ({len(dupe_flags)//2} candidate duplicate pairs)")
print()

# ------------------------------------------------------------------
# PART 1c — Just-below-threshold clustering
# ------------------------------------------------------------------
print("=" * 70)
print("PART 1c — JUST-BELOW-APPROVAL-THRESHOLD CLUSTERING")
print("=" * 70)

THRESHOLD = 10000
BAND = 350
work["flag_below_threshold"] = work["amount"].between(THRESHOLD - BAND, THRESHOLD - 1)
by_dept = work[work["flag_below_threshold"]]["department"].value_counts()
print(f"Transactions in the ${THRESHOLD-BAND:,}-${THRESHOLD-1:,} band "
      f"(just under the ${THRESHOLD:,} secondary-approval limit): "
      f"{work['flag_below_threshold'].sum()}")
print("By department:")
print(by_dept.to_string())
print()

# ------------------------------------------------------------------
# PART 1d — Weekend / after-hours postings
# ------------------------------------------------------------------
print("=" * 70)
print("PART 1d — WEEKEND / AFTER-HOURS POSTINGS")
print("=" * 70)

work["is_weekend"] = work["posting_datetime"].dt.weekday >= 5
work["hour"] = work["posting_datetime"].dt.hour
work["is_after_hours"] = ~work["hour"].between(7, 19)
work["flag_timing"] = work["is_weekend"] | work["is_after_hours"]
print(f"Weekend postings: {work['is_weekend'].sum()}")
print(f"After-hours postings (outside 07:00-19:00): {work['is_after_hours'].sum()}")
print(f"Total timing-flagged: {work['flag_timing'].sum()}")
print()

# ------------------------------------------------------------------
# PART 1e — Suspiciously round amounts
# ------------------------------------------------------------------
print("=" * 70)
print("PART 1e — SUSPICIOUSLY ROUND AMOUNTS")
print("=" * 70)

work["flag_round"] = (work["amount"] % 500 == 0) & (work["amount"] >= 1000)
print(f"Amounts that are exact multiples of $500 (>= $1,000): "
      f"{work['flag_round'].sum()}")
print()

rule_cols = ["flag_benford_vendor", "flag_duplicate", "flag_below_threshold",
             "flag_timing", "flag_round"]
work["rule_flag_count"] = work[rule_cols].sum(axis=1)
work["any_rule_flag"] = work["rule_flag_count"] > 0
print(f"RULE-BASED LAYER TOTAL: {work['any_rule_flag'].sum()} transactions "
      f"flagged by at least one rule out of {len(work):,} "
      f"({work['any_rule_flag'].mean()*100:.1f}%)")
print()

# ------------------------------------------------------------------
# PART 2 — Machine learning: Isolation Forest
# ------------------------------------------------------------------
print("=" * 70)
print("PART 2 — ISOLATION FOREST (multivariate ML anomaly detection)")
print("=" * 70)
print("Rules catch what we already know to look for. ML catches what we")
print("didn't think to write a rule for -- e.g. 'this amount is fine in")
print("general, but abnormal FOR THIS VENDOR'.\n")

# Feature engineering: express each transaction relative to its own vendor's
# normal behaviour, so the model can catch vendor-relative outliers.
vendor_stats = work.groupby("vendor_id")["amount"].agg(["mean", "std", "count"])
vendor_stats["std"] = vendor_stats["std"].fillna(vendor_stats["std"].median())
work = work.merge(vendor_stats, left_on="vendor_id", right_index=True,
                   suffixes=("", "_vendor"))
work["amount_zscore_vendor"] = (
    (work["amount"] - work["mean"]) / work["std"].replace(0, 1)
)
work["log_amount"] = np.log1p(work["amount"])
work["dept_freq"] = work["department"].map(work["department"].value_counts(normalize=True))

features = work[[
    "log_amount", "amount_zscore_vendor", "hour", "is_weekend", "count"
]].fillna(0)
features["is_weekend"] = features["is_weekend"].astype(int)

iso = IsolationForest(
    n_estimators=300, contamination=0.03, random_state=42
)
work["ml_anomaly_score"] = -iso.fit(features).score_samples(features)
work["flag_ml"] = iso.predict(features) == -1

print(f"ML LAYER: {work['flag_ml'].sum()} transactions flagged as "
      f"multivariate outliers (contamination=3%)")
print()

fig, ax = plt.subplots(figsize=(7, 4.2))
ax.hist(work.loc[~work["flag_ml"], "ml_anomaly_score"], bins=50,
        color=BLUE, alpha=0.85, label="Normal")
ax.hist(work.loc[work["flag_ml"], "ml_anomaly_score"], bins=50,
        color=RED, alpha=0.85, label="ML-flagged")
ax.set_xlabel("Isolation Forest anomaly score (higher = more anomalous)")
ax.set_ylabel("Number of transactions")
ax.set_title("Distribution of ML anomaly scores")
ax.legend(frameon=False)
for spine in ["top", "right"]:
    ax.spines[spine].set_visible(False)
fig.tight_layout()
fig.savefig("charts/02_ml_score_distribution.png", dpi=150)
plt.close(fig)
print("Saved charts/02_ml_score_distribution.png")
print()

# ------------------------------------------------------------------
# PART 3 — Combined risk-ranked worklist
# ------------------------------------------------------------------
print("=" * 70)
print("PART 3 — COMBINED RISK-RANKED WORKLIST")
print("=" * 70)

# Simple, explainable composite score an auditor can defend:
#   +1 per rule triggered, plus normalized ML score (0-1) weighted x2
ml_min, ml_max = work["ml_anomaly_score"].min(), work["ml_anomaly_score"].max()
work["ml_score_norm"] = (work["ml_anomaly_score"] - ml_min) / (ml_max - ml_min)
work["composite_risk_score"] = work["rule_flag_count"] + 2 * work["ml_score_norm"]
work["any_flag"] = work["any_rule_flag"] | work["flag_ml"]

worklist = work.sort_values("composite_risk_score", ascending=False).head(50)
worklist_out = worklist[[
    "transaction_id", "vendor_name", "department", "amount", "posting_datetime",
    "rule_flag_count", "flag_ml", "composite_risk_score"
]]
worklist_out.to_csv("output/risk_ranked_worklist_top50.csv", index=False)
print("Top 10 highest-risk transactions for auditor triage:")
print(worklist_out.head(10).to_string(index=False))
print("\nFull top-50 worklist saved to output/risk_ranked_worklist_top50.csv")
print()

# ------------------------------------------------------------------
# PART 3b — Reveal ground truth: how did we do?
# ------------------------------------------------------------------
print("=" * 70)
print("PART 3b — SCORING AGAINST KNOWN PLANTED ANOMALIES (reveal)")
print("=" * 70)

scored = work.merge(GROUND_TRUTH, on="transaction_id")
total_planted = scored["is_planted_anomaly"].sum()
caught_any = scored.loc[scored["is_planted_anomaly"], "any_flag"].sum()
caught_rules = scored.loc[scored["is_planted_anomaly"], "any_rule_flag"].sum()
caught_ml = scored.loc[scored["is_planted_anomaly"], "flag_ml"].sum()

precision = scored["any_flag"].sum() and caught_any / scored["any_flag"].sum()
recall = caught_any / total_planted

print(f"Planted anomalies in the dataset: {total_planted}")
print(f"Caught by rules only:            {caught_rules}")
print(f"Caught by ML only:                {caught_ml}")
print(f"Caught by rules AND/OR ML:        {caught_any} "
      f"({caught_any/total_planted*100:.0f}% recall)")
print(f"Total transactions flagged (either layer): {scored['any_flag'].sum()} "
      f"of {len(scored):,} ({scored['any_flag'].mean()*100:.1f}% of the population)")
print(f"Precision of combined flags: {precision*100:.0f}%")

print("\nRecall by anomaly type:")
by_type = scored[scored["is_planted_anomaly"]].groupby("anomaly_type")["any_flag"].agg(
    ["sum", "count"])
by_type["recall_%"] = (by_type["sum"] / by_type["count"] * 100).round(0)
print(by_type.rename(columns={"sum": "caught", "count": "planted"}).to_string())

# Chart: coverage comparison, sample audit vs CTA
fig, ax = plt.subplots(figsize=(7, 4.2))
categories = ["Traditional\nquarterly sample\n(~4% coverage)",
              "Continuous\ntransaction auditing\n(100% coverage)"]
coverage_pct = [4, 100]
anomalies_seen = [round(total_planted * 0.04), caught_any]
bars = ax.bar(categories, coverage_pct, color=[MUTED, BLUE], width=0.5)
ax.set_ylabel("% of transaction population reviewed")
ax.set_title("Coverage: sample-based vs. continuous transaction auditing")
for b, seen in zip(bars, anomalies_seen):
    ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 2,
            f"~{seen} of {total_planted}\nanomalies visible", ha="center",
            fontsize=9.5, color=INK)
ax.set_ylim(0, 115)
for spine in ["top", "right"]:
    ax.spines[spine].set_visible(False)
ax.grid(axis="y", linewidth=0.6)
fig.tight_layout()
fig.savefig("charts/03_coverage_comparison.png", dpi=150)
plt.close(fig)
print("\nSaved charts/03_coverage_comparison.png")

print("\n" + "=" * 70)
print("DEMO COMPLETE")
print("=" * 70)
