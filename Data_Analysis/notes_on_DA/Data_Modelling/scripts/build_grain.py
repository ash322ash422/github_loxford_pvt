import sys
sys.path.insert(0, "/tmp/dm_workshop")
from diagram_utils import draw_data_table, new_fig, save

IMG = "/tmp/dm_workshop/images"

# =========================================================
# GRANULARITY — same raw sales, three different grain choices
# =========================================================
fig, ax = new_fig((13, 6.6))
ax.set_xlim(0, 13)
ax.set_ylim(0, 6.6)

hdr_line = ["sales_key", "transaction_id", "product", "quantity", "sales_amount"]
rows_line = [
    [1, "TXN-9001", "AeroBuds Pro",   2, 4998],
    [2, "TXN-9001", "VoltCharge 65W", 1, 1299],
    [3, "TXN-9002", "PixelView 24",   1, 13999],
]
cw_line = [1.7, 2.4, 2.6, 1.7, 2.1]
draw_data_table(ax, 0.2, 6.4, cw_line, hdr_line, rows_line,
                 title="GRAIN = one row per PRODUCT LINE within a transaction  (finest)")

hdr_txn = ["transaction_id", "num_items", "total_amount"]
rows_txn = [
    ["TXN-9001", 2, 6297],
    ["TXN-9002", 1, 13999],
]
cw_txn = [3.0, 2.3, 2.6]
draw_data_table(ax, 0.2, 4.15, cw_txn, hdr_txn, rows_txn,
                 title="GRAIN = one row per TRANSACTION  (coarser — line items are summed)")

hdr_day = ["date", "store", "total_amount"]
rows_day = [
    ["2026-06-01", "ST-101", 6297],
]
cw_day = [2.4, 2.2, 2.6]
draw_data_table(ax, 0.2, 2.15, cw_day, hdr_day, rows_day,
                 title="GRAIN = one row per STORE per DAY  (coarsest — everything rolled up)")

ax.text(6.4, 0.35,
        "Rule: declare the grain BEFORE choosing dimensions/measures. Finer grain = more flexibility & more rows.\n"
        "You can always aggregate UP from a fine grain in a query; you can never recover detail from a grain that's too coarse.",
        ha="center", va="center", fontsize=9.8, style="italic", color="#455A64")

save(fig, f"{IMG}/granularity.png")

# =========================================================
# SURROGATE KEY vs NATURAL KEY
# =========================================================
fig, ax = new_fig((13.2, 4.4))
ax.set_xlim(0, 13.2)
ax.set_ylim(0, 4.4)

hdr = ["Aspect", "Natural Key (e.g. SKU / Email)", "Surrogate Key (e.g. product_key)"]
rows = [
    ["Meaning",        "Business-meaningful identifier", "System-generated, meaningless integer"],
    ["Example",        "SKU-5001",                        "1"],
    ["Stable over time?", "Can change (re-branding, merges)", "Never changes — assigned once, forever"],
    ["Handles SCD Type 2?", "No — one SKU can't represent two\nversions of the same product", "Yes — new surrogate key per version\n(e.g. 1 and 2 both map to SKU-5001)"],
    ["Join performance", "Slower (strings, composite keys)", "Fast (single integer join)"],
]
cw = [2.6, 4.9, 5.5]
draw_data_table(ax, 0.2, 4.2, cw, hdr, rows, row_h=0.62, fontsize=9.3)

save(fig, f"{IMG}/surrogate_vs_natural_key.png")
