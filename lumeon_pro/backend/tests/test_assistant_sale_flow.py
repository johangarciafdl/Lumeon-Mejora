"""Regression tests for the assistant's critical sale invariants.

These tests intentionally exercise service boundaries rather than HTTP wiring,
so they remain useful with both SQLite and Supabase-backed deployments.
"""

import pytest

from services.inventory_service import InventoryError, reserve_items
from services.idempotency_service import key_for


def test_assistant_sale_idempotency_key_changes_with_payload():
    first = key_for(7, "user:7:desktop", "create_sale", {"items": [{"referencia": "P1", "cantidad": 1}]})
    second = key_for(7, "user:7:desktop", "create_sale", {"items": [{"referencia": "P1", "cantidad": 2}]})
    assert first != second


def test_inventory_cannot_be_reserved_twice_after_stock_is_exhausted():
    class Row(dict):
        pass

    class Cursor:
        rowcount = 1

    class Conn:
        def __init__(self):
            self.stock = 1
        def execute(self, sql, params):
            if self.stock < params[2]:
                class Failed: rowcount = 0
                return Failed()
            self.stock -= params[0]
            return Cursor()

    conn = Conn()
    reserve_items(conn, [{"referencia": "P1", "cantidad": 1}])
    with pytest.raises(InventoryError):
        reserve_items(conn, [{"referencia": "P1", "cantidad": 1}])
    assert conn.stock == 0
