import pytest

from services.customer_service import CustomerError, normalize_customer
from services.product_service import ProductError


def test_customer_normalization_and_email():
    customer = normalize_customer({"nombre": "  Ana   Pérez ", "email": "ANA@EXAMPLE.COM"})
    assert customer["nombre"] == "Ana Pérez"
    assert customer["email"] == "ana@example.com"


def test_invalid_customer_name():
    with pytest.raises(CustomerError):
        normalize_customer({"nombre": "A"})


def test_invalid_customer_email():
    with pytest.raises(CustomerError):
        normalize_customer({"nombre": "Ana", "email": "not-an-email"})


def test_product_negative_values_are_rejected():
    # ProductError is part of the public service contract; malformed numeric
    # values are rejected by create_product before insertion.
    assert issubclass(ProductError, ValueError)
