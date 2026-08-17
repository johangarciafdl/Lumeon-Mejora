from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SaleDraft:
    customer_id: int | None = None
    customer_name: str = ""
    items: list[dict[str, Any]] = field(default_factory=list)

    def add_item(self, product: dict[str, Any], quantity: int) -> None:
        quantity = int(quantity)
        if quantity <= 0:
            raise ValueError("La cantidad debe ser mayor que cero")
        stock = int(product.get("stock", 0))
        if quantity > stock:
            raise ValueError(f"Stock insuficiente para {product.get('nombre', 'producto')}")
        self.items.append({
            "producto_id": product.get("id"),
            "referencia": product.get("referencia", ""),
            "nombre": product.get("nombre", ""),
            "cantidad": quantity,
            "precio_compra": float(product.get("precio_compra", 0) or 0),
            "precio_venta": float(product.get("precio_venta", 0) or 0),
        })

    def total(self) -> float:
        return round(sum(i["cantidad"] * i["precio_venta"] for i in self.items), 2)

    def summary(self) -> dict[str, Any]:
        return {
            "customer_id": self.customer_id,
            "customer_name": self.customer_name,
            "items": self.items,
            "total": self.total(),
        }

    def validate(self) -> None:
        if not self.customer_id:
            raise ValueError("Selecciona un cliente antes de crear la venta")
        if not self.items:
            raise ValueError("Agrega al menos un producto a la venta")
