"""
Reusable data rules: our definition of an acceptable housing table.
It checks:
- Exactly five expected columns, in any order, and at least one row.
- No missing values in any required column.
- Integer IDs, bedrooms, and years; decimal areas and prices.
- Reasonable ranges for area, bedrooms, year built, and price.
- Unique house IDs.
"""
import great_expectations as gx

EXPECTED_COLUMNS = ["house_id", "area_sqft", "bedrooms", "year_built", "sale_price"]

def make_suite():
    suite = gx.ExpectationSuite(name="house_price_rules")
    
    # Schema: exact column names, but column order does not matter.
    suite.add_expectation(gx.expectations.ExpectTableColumnsToMatchSet(
        column_set=EXPECTED_COLUMNS, exact_match=True,
    ))
    suite.add_expectation(gx.expectations.ExpectTableRowCountToBeBetween(min_value=1))

    # Missing data: require a value in every required column.
    for column in EXPECTED_COLUMNS:
        suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(
            column=column, catch_exceptions=True,
        ))

    # Schema also includes data types. These types match pandas.read_csv inference.
    for column, dtype in {"house_id": "int64", "area_sqft": "float64",
                          "bedrooms": "int64", "year_built": "int64",
                          "sale_price": "float64"}.items():
        suite.add_expectation(gx.expectations.ExpectColumnValuesToBeOfType(
            column=column, type_=dtype, catch_exceptions=True,
        ))

    # Business rules: numeric does not automatically mean sensible.
    for column, low, high in [("area_sqft", 300, 10000), ("bedrooms", 1, 10),
                              ("year_built", 1900, 2026), ("sale_price", 10000, 5000000)]:
        suite.add_expectation(gx.expectations.ExpectColumnValuesToBeBetween(
            column=column, min_value=low, max_value=high, catch_exceptions=True,
        ))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToBeUnique(
        column="house_id", catch_exceptions=True,
    ))
    return suite
