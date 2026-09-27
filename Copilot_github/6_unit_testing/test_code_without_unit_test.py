import pytest

from code_without_unit_test import calculate_discount


@pytest.mark.parametrize(
    "price, discount, expected",
    [
        (100, 10, 90),
        (50, 50, 25),
        (99.99, 20, 79.992),
    ],
)
def test_calculate_discount_positive_cases(price, discount, expected):
    """Positive cases: valid price and discount values."""
    assert calculate_discount(price, discount) == pytest.approx(expected)


@pytest.mark.parametrize(
    "price, discount, expected",
    [
        (100, 0, 100),
        (100, 100, 0),
        (0, 25, 0),
    ],
)
def test_calculate_discount_edge_cases(price, discount, expected):
    """Edge cases: zero price, zero discount, and full discount."""
    assert calculate_discount(price, discount) == pytest.approx(expected)


@pytest.mark.parametrize(
    "price, discount, expected",
    [
        (-100, 10, -110),
        (100, -10, 110),
        (100, 150, -50),
    ],
)
def test_calculate_discount_negative_cases(price, discount, expected):
    """Negative cases: unexpected but valid numeric values."""
    assert calculate_discount(price, discount) == pytest.approx(expected)


def test_calculate_discount_invalid_type():
    """Invalid input types should raise a TypeError."""
    with pytest.raises(TypeError):
        calculate_discount("100", 10)
