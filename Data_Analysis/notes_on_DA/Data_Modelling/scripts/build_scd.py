import sys
sys.path.insert(0, "/tmp/dm_workshop")
from diagram_utils import draw_data_table, new_fig, save, HILITE, NEWROW

IMG = "/tmp/dm_workshop/images"

# Scenario used throughout: Arjun Mehta (CUST-02) relocates from Pune to Mumbai on 2026-07-10.
# BEFORE state is identical for all three types.

BEFORE_HEADERS = ["customer_key", "customer_id", "customer_name", "city", "loyalty_tier"]
BEFORE_ROWS = [
    [501, "CUST-01", "Ritu Sharma", "Mumbai", "Gold"],
    [502, "CUST-02", "Arjun Mehta", "Pune",   "Silver"],
]

# =========================================================
# SCD TYPE 1 — overwrite, no history kept
# =========================================================
fig, ax = new_fig((10, 5.2))
ax.set_xlim(0, 10)
ax.set_ylim(0, 5.2)

cw = [1.7, 1.7, 2.0, 1.4, 1.6]
b_bottom = draw_data_table(ax, 0.2, 5.0, cw, BEFORE_HEADERS, BEFORE_ROWS,
                            title="BEFORE  (as of 2026-07-01)")

AFTER1_ROWS = [
    [501, "CUST-01", "Ritu Sharma", "Mumbai", "Gold"],
    [502, "CUST-02", "Arjun Mehta", "Mumbai", "Silver"],
]
a_bottom = draw_data_table(ax, 0.2, 2.5, cw, BEFORE_HEADERS, AFTER1_ROWS,
                            title="AFTER  (2026-07-10 update, Type 1: overwrite in place)",
                            highlight_cells={(1, 3)})

ax.annotate("", xy=(2.6, 2.15), xytext=(2.6, 2.45),
            arrowprops=dict(arrowstyle="->", color="#455A64", lw=1.6))
ax.text(6.3, 0.15, "Row is UPDATED in place. Old value 'Pune' is gone — no history, one row per customer, query stays simple.",
        ha="center", va="center", fontsize=9.5, style="italic", color="#455A64")
save(fig, f"{IMG}/scd_type1.png")

# =========================================================
# SCD TYPE 2 — new row, full history with surrogate key + version columns
# =========================================================
fig, ax = new_fig((12.6, 5.6))
ax.set_xlim(0, 12.6)
ax.set_ylim(0, 5.6)

hdr2 = ["cust_key", "customer_id", "customer_name", "city", "start_date", "end_date", "is_current"]
before2 = [
    [501, "CUST-01", "Ritu Sharma", "Mumbai", "2025-01-01", "9999-12-31", "Y"],
    [502, "CUST-02", "Arjun Mehta", "Pune",   "2025-01-01", "9999-12-31", "Y"],
]
cw2 = [1.3, 1.5, 2.0, 1.3, 1.5, 1.5, 1.5]
draw_data_table(ax, 0.2, 5.4, cw2, hdr2, before2, title="BEFORE  (as of 2026-07-01)")

after2 = [
    [501, "CUST-01", "Ritu Sharma", "Mumbai", "2025-01-01", "9999-12-31", "Y"],
    [502, "CUST-02", "Arjun Mehta", "Pune",   "2025-01-01", "2026-07-09", "N"],
    [901, "CUST-02", "Arjun Mehta", "Mumbai", "2026-07-10", "9999-12-31", "Y"],
]
draw_data_table(ax, 0.2, 2.85, cw2, hdr2, after2,
                 title="AFTER  (2026-07-10 update, Type 2: expire old row, insert new row)",
                 highlight_cells={(1, 5), (1, 6)}, highlight_rows={2: NEWROW})

ax.text(6.3, 0.35,
        "Old row (cust_key 502) is closed off: end_date + is_current='N'.\n"
        "A NEW row is inserted with a NEW surrogate key (901) and the new city — full history preserved.\n"
        "Fact rows loaded before 2026-07-10 still point to cust_key 502 (Pune); new fact rows point to 901 (Mumbai).",
        ha="center", va="center", fontsize=9.3, style="italic", color="#455A64")
save(fig, f"{IMG}/scd_type2.png")

# =========================================================
# SCD TYPE 3 — add a column to keep limited (usually just prior) history
# =========================================================
fig, ax = new_fig((11.2, 5.2))
ax.set_xlim(0, 11.2)
ax.set_ylim(0, 5.2)

hdr3 = ["customer_key", "customer_id", "customer_name", "current_city", "previous_city"]
before3 = [
    [501, "CUST-01", "Ritu Sharma", "Mumbai", "-"],
    [502, "CUST-02", "Arjun Mehta", "Pune",   "-"],
]
cw3 = [1.8, 1.7, 2.1, 1.7, 1.7]
draw_data_table(ax, 0.2, 5.0, cw3, hdr3, before3, title="BEFORE  (as of 2026-07-01)")

after3 = [
    [501, "CUST-01", "Ritu Sharma", "Mumbai", "-"],
    [502, "CUST-02", "Arjun Mehta", "Mumbai", "Pune"],
]
draw_data_table(ax, 0.2, 2.5, cw3, hdr3, after3,
                 title="AFTER  (2026-07-10 update, Type 3: add 'previous_city' column)",
                 highlight_cells={(1, 3), (1, 4)})

ax.text(5.6, 0.4,
        "Row stays the SAME (key 502). 'current_city' is overwritten, but the immediately-prior\n"
        "value is preserved in a new column. Keeps only ONE step of history, no new rows/keys.",
        ha="center", va="center", fontsize=9.5, style="italic", color="#455A64")
save(fig, f"{IMG}/scd_type3.png")
