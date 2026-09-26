import sys
sys.path.insert(0, "/tmp/dm_workshop")
from diagram_utils import draw_data_table, new_fig, save, HILITE

IMG = "/tmp/dm_workshop/images"

# =========================================================
# DENORMALIZED — one wide table, customer info repeated on every order line
# =========================================================
fig, ax = new_fig((12.5, 5.6))
ax.set_xlim(0, 12.5)
ax.set_ylim(0, 5.6)

hdr = ["order_id", "customer_name", "customer_email", "customer_city", "product", "price"]
rows = [
    ["ORD-1001", "Ritu Sharma", "ritu.s@mail.com", "Mumbai", "AeroBuds Pro",   2499],
    ["ORD-1002", "Ritu Sharma", "ritu.s@mail.com", "Mumbai", "VoltCharge 65W", 1299],
    ["ORD-1003", "Arjun Mehta", "arjun.m@mail.com","Pune",   "PixelView 24",  13999],
    ["ORD-1004", "Ritu Sharma", "ritu.s@mail.com", "Mumbai", "VoltCharge 65W", 1299],
]
cw = [1.7, 2.0, 2.5, 1.8, 2.2, 1.3]
# highlight the repeated customer cells to show redundancy
redundant = {(0,1),(0,2),(0,3),(1,1),(1,2),(1,3),(3,1),(3,2),(3,3)}
draw_data_table(ax, 0.2, 5.4, cw, hdr, rows,
                 title="DENORMALIZED  —  one flat table",
                 highlight_cells=redundant)

ax.text(6.25, 0.85,
        "Customer_name / email / city repeat on every order row (highlighted).\n"
        "Fast to query (no JOIN) — but if Ritu Sharma's email changes, THREE rows must be updated.\n"
        "Miss one row → the same customer now has two different emails (an update anomaly).",
        ha="center", va="center", fontsize=9.8, style="italic", color="#455A64")

save(fig, f"{IMG}/denormalized_orders.png")

# =========================================================
# NORMALIZED (3NF) — split into ORDERS + CUSTOMERS, no repeated attributes
# =========================================================
fig, ax = new_fig((11.5, 5.6))
ax.set_xlim(0, 11.5)
ax.set_ylim(0, 5.6)

hdr_o = ["order_id", "customer_id", "product", "price"]
rows_o = [
    ["ORD-1001", "C1", "AeroBuds Pro",   2499],
    ["ORD-1002", "C1", "VoltCharge 65W", 1299],
    ["ORD-1003", "C2", "PixelView 24",  13999],
    ["ORD-1004", "C1", "VoltCharge 65W", 1299],
]
cw_o = [1.9, 1.7, 2.5, 1.4]
bottom = draw_data_table(ax, 0.2, 5.4, cw_o, hdr_o, rows_o, title="ORDERS")

hdr_c = ["customer_id", "customer_name", "customer_email", "customer_city"]
rows_c = [
    ["C1", "Ritu Sharma", "ritu.s@mail.com",  "Mumbai"],
    ["C2", "Arjun Mehta", "arjun.m@mail.com", "Pune"],
]
cw_c = [1.9, 2.1, 2.7, 1.9]
draw_data_table(ax, 0.2, 2.6, cw_c, hdr_c, rows_c, title="CUSTOMERS")

ax.text(5.7, 0.55,
        "Each fact is stored exactly ONCE. Update Ritu's email in ONE place (CUSTOMERS) — every order reflects it via customer_id.\n"
        "No update anomalies, less storage — but reporting now needs a JOIN between ORDERS and CUSTOMERS.",
        ha="center", va="center", fontsize=9.8, style="italic", color="#455A64")

save(fig, f"{IMG}/normalized_orders.png")
