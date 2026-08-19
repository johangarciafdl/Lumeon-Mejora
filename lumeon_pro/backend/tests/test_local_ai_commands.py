from services.ai_orchestrator import _local_command_plan


def test_local_search_product():
    assert _local_command_plan("buscar producto 70983") == {
        "action": "search_product",
        "query": "70983",
    }


def test_local_low_stock():
    assert _local_command_plan("stock bajo") == {"action": "low_stock"}


def test_local_price_update_requires_confirmation():
    plan = _local_command_plan("cambia el precio del producto 70983 a 45000")
    assert plan["action"] == "update_product_price"
    assert plan["product_ref"] == "70983"
    assert plan["price"] == 45000.0
    assert "Confirmas" in plan["confirmation_message"]


def test_local_sale_with_phone_and_product_id():
    plan = _local_command_plan(
        "registrar venta para Carlos telefono 3008123268 productos 70983x2, 218453x1"
    )
    assert plan["action"] == "create_sale"
    assert plan["customer_name"] == "Carlos"
    assert plan["phone"] == "3008123268"
    assert plan["items"] == [
        {"referencia": "70983", "cantidad": 2},
        {"referencia": "218453", "cantidad": 1},
    ]
