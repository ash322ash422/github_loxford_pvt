import sys
sys.path.insert(0, "/tmp/dm_workshop")
from diagram_utils import draw_table, connect, new_fig, save, FACT_HEADER, DIM_HEADER, SNOWFLAKE_HEADER

IMG = "/tmp/dm_workshop/images"

# =========================================================
# STAR SCHEMA — fact in the middle, flattened dimensions around it
# =========================================================
fig, ax = new_fig((12, 8))
ax.set_xlim(0, 12)
ax.set_ylim(0, 8)

# Fact table in center
fact_fields = ["sales_key", "date_key", "store_key", "product_key", "customer_key", "quantity", "unit_price", "sales_amount"]
fact_bottom, fact_h, fact_anchor = draw_table(ax, 4.3, 6.0, 3.4, "FACT_SALES", fact_fields,
                                               header_color=FACT_HEADER,
                                               pk_fields=["sales_key"],
                                               fk_fields=["date_key", "store_key", "product_key", "customer_key"])

# Dimension tables around it (flattened / denormalized attributes)
dim_date_fields = ["date_key", "full_date", "day_name", "month_name", "quarter", "year"]
_, _, a1 = draw_table(ax, 0.3, 7.7, 3.0, "DIM_DATE", dim_date_fields, header_color=DIM_HEADER, pk_fields=["date_key"])

dim_store_fields = ["store_key", "store_id", "store_name", "city", "region", "country"]
_, _, a2 = draw_table(ax, 8.6, 7.7, 3.1, "DIM_STORE", dim_store_fields, header_color=DIM_HEADER, pk_fields=["store_key"])

dim_prod_fields = ["product_key", "sku", "product_name", "category", "subcategory", "brand"]
_, _, a3 = draw_table(ax, 8.6, 3.9, 3.1, "DIM_PRODUCT", dim_prod_fields, header_color=DIM_HEADER, pk_fields=["product_key"])

dim_cust_fields = ["customer_key", "customer_id", "customer_name", "city", "loyalty_tier"]
_, _, a4 = draw_table(ax, 0.3, 3.9, 3.0, "DIM_CUSTOMER", dim_cust_fields, header_color=DIM_HEADER, pk_fields=["customer_key"])

# Connectors: fact FK row -> dimension PK row
connect(ax, (fact_anchor["date_key"][0], fact_anchor["date_key"][2]), (a1["date_key"][1], a1["date_key"][2]))
connect(ax, (fact_anchor["store_key"][1], fact_anchor["store_key"][2]), (a2["store_key"][0], a2["store_key"][2]))
connect(ax, (fact_anchor["product_key"][1], fact_anchor["product_key"][2]), (a3["product_key"][0], a3["product_key"][2]))
connect(ax, (fact_anchor["customer_key"][0], fact_anchor["customer_key"][2]), (a4["customer_key"][1], a4["customer_key"][2]))

ax.text(6, 0.3, "STAR SCHEMA — dimensions are flattened (denormalized): one wide table per dimension, one hop from fact to any attribute",
        ha="center", va="center", fontsize=10, color="#455A64", style="italic")

save(fig, f"{IMG}/star_schema.png")

# =========================================================
# SNOWFLAKE SCHEMA — same fact, but DIM_STORE and DIM_PRODUCT normalized further
# =========================================================
fig, ax = new_fig((13.5, 10.5))
ax.set_xlim(0, 13.5)
ax.set_ylim(0, 10.5)

GAP = 0.5  # vertical gap between stacked tables

fact_bottom, fact_h, fact_anchor = draw_table(ax, 5.1, 10.2, 3.3, "FACT_SALES", fact_fields,
                                               header_color=FACT_HEADER,
                                               pk_fields=["sales_key"],
                                               fk_fields=["date_key", "store_key", "product_key", "customer_key"])

_, _, aD = draw_table(ax, 0.3, 10.2, 2.9, "DIM_DATE", dim_date_fields, header_color=DIM_HEADER, pk_fields=["date_key"])
_, _, aC = draw_table(ax, 10.3, 10.2, 3.0, "DIM_CUSTOMER", dim_cust_fields, header_color=DIM_HEADER, pk_fields=["customer_key"])

# Snowflaked STORE branch: DIM_STORE -> DIM_CITY -> DIM_REGION -> DIM_COUNTRY
sTop = 7.6
sBottom, sH, aS = draw_table(ax, 9.9, sTop, 3.2, "DIM_STORE", ["store_key", "store_id", "store_name", "city_key"],
                       header_color=DIM_HEADER, pk_fields=["store_key"], fk_fields=["city_key"])
cityTop = sBottom - GAP
cityBottom, cityH, aCity = draw_table(ax, 9.9, cityTop, 3.2, "DIM_CITY", ["city_key", "city_name", "region_key"],
                          header_color=SNOWFLAKE_HEADER, pk_fields=["city_key"], fk_fields=["region_key"])
regTop = cityBottom - GAP
regBottom, regH, aReg = draw_table(ax, 9.9, regTop, 3.2, "DIM_REGION", ["region_key", "region_name", "country_key"],
                         header_color=SNOWFLAKE_HEADER, pk_fields=["region_key"], fk_fields=["country_key"])
ctyTop = regBottom - GAP
ctyBottom, ctyH, aCty = draw_table(ax, 9.9, ctyTop, 3.2, "DIM_COUNTRY", ["country_key", "country_name"],
                         header_color=SNOWFLAKE_HEADER, pk_fields=["country_key"])

# Snowflaked PRODUCT branch: DIM_PRODUCT -> DIM_SUBCATEGORY -> DIM_CATEGORY
pTop = 7.6
pBottom, pH, aP = draw_table(ax, 0.3, pTop, 3.0, "DIM_PRODUCT", ["product_key", "sku", "product_name", "subcat_key"],
                       header_color=DIM_HEADER, pk_fields=["product_key"], fk_fields=["subcat_key"])
subTop = pBottom - GAP
subBottom, subH, aSub = draw_table(ax, 0.3, subTop, 3.0, "DIM_SUBCATEGORY", ["subcat_key", "subcategory_name", "category_key"],
                         header_color=SNOWFLAKE_HEADER, pk_fields=["subcat_key"], fk_fields=["category_key"])
catTop = subBottom - GAP
catBottom, catH, aCat = draw_table(ax, 0.3, catTop, 3.0, "DIM_CATEGORY", ["category_key", "category_name"],
                         header_color=SNOWFLAKE_HEADER, pk_fields=["category_key"])

print("lowest point:", min(ctyBottom, catBottom))

# Fact -> dims
connect(ax, (fact_anchor["date_key"][0], fact_anchor["date_key"][2]), (aD["date_key"][1], aD["date_key"][2]))
connect(ax, (fact_anchor["customer_key"][1], fact_anchor["customer_key"][2]), (aC["customer_key"][0], aC["customer_key"][2]))
connect(ax, (fact_anchor["store_key"][1], fact_anchor["store_key"][2]), (aS["store_key"][0], aS["store_key"][2]))
connect(ax, (fact_anchor["product_key"][0], fact_anchor["product_key"][2]), (aP["product_key"][1], aP["product_key"][2]))

# Snowflake chains
connect(ax, (aS["city_key"][0]+1.6, aS["city_key"][2]-0.17), (aCity["city_key"][0]+1.6, aCity["city_key"][2]+0.17), color=SNOWFLAKE_HEADER)
connect(ax, (aCity["region_key"][0]+1.6, aCity["region_key"][2]-0.17), (aReg["region_key"][0]+1.6, aReg["region_key"][2]+0.17), color=SNOWFLAKE_HEADER)
connect(ax, (aReg["country_key"][0]+1.6, aReg["country_key"][2]-0.17), (aCty["country_key"][0]+1.6, aCty["country_key"][2]+0.17), color=SNOWFLAKE_HEADER)

connect(ax, (aP["subcat_key"][0]+1.5, aP["subcat_key"][2]-0.17), (aSub["subcat_key"][0]+1.5, aSub["subcat_key"][2]+0.17), color=SNOWFLAKE_HEADER)
connect(ax, (aSub["category_key"][0]+1.5, aSub["category_key"][2]-0.17), (aCat["category_key"][0]+1.5, aCat["category_key"][2]+0.17), color=SNOWFLAKE_HEADER)

ax.text(6.7, -0.35, "SNOWFLAKE SCHEMA — dimensions are normalized into sub-dimensions (Store→City→Region→Country, Product→Subcategory→Category): saves storage, costs extra JOINs",
        ha="center", va="center", fontsize=9.5, color="#455A64", style="italic")
ax.set_ylim(-0.7, 10.5)

save(fig, f"{IMG}/snowflake_schema.png")
