import pytest

from services.assistant_sale_builder import SaleDraft


def product(stock=5):
    return {"id": 1, "referencia": "A1", "nombre": "Producto", "stock": stock, "precio_venta": 10000}


def test_sale_draft_calculates_total():
    draft = SaleDraft(customer_id=7, customer_name="Juan")
    draft.add_item(product(), 2)
    assert draft.total() == 20000


def test_sale_draft_rejects_stock_overage():
    draft = SaleDraft(customer_id=7)
    with pytest.raises(ValueError):
        draft.add_item(product(stock=1), 2)


def test_sale_draft_requires_customer_and_item():
    draft = SaleDraft()
    with pytest.raises(ValueError):
        draft.validate()
