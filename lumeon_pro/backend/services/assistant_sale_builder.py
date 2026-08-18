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
        product_id = product.get("id") or product.get("producto_id")
        if not product_id:
            raise ValueError("Producto inválido")
        stock = int(product.get("stock", 0) or 0)
        if quantity > stock:
            raise ValueError(f"Stock insuficiente para {product.get('nombre', 'producto')}: disponible {stock}")

        price = float(product.get("precio_venta", 0) or 0)
        purchase = float(product.get("precio_compra", 0) or 0)
        if price < 0 or purchase < 0:
            raise ValueError("El precio del producto no puede ser negativo")

        # Merge repeated products instead of creating duplicate sale lines.
        for item in self.items:
            if int(item["producto_id"]) == int(product_id):
                new_quantity = int(item["cantidad"]) + quantity
                if new_quantity > stock:
                    raise ValueError(f"Stock insuficiente para {product.get('nombre', 'producto')}: disponible {stock}")
                item["cantidad"] = new_quantity
                return

        self.items.append({
            "producto_id": int(product_id),
            "referencia": str(product.get("referencia", "")),
            "nombre": str(product.get("nombre", "")),
            "cantidad": quantity,
            "precio_compra": purchase,
            "precio_venta": price,
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
        if any(int(i.get("cantidad", 0)) <= 0 for i in self.items):
            raise ValueError("Todas las cantidades deben ser mayores que cero")
