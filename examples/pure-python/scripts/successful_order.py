import json
from decimal import Decimal
from typing import TypedDict


class OrderItem(TypedDict):
    sku: str
    price: str
    quantity: int


class OrderPayload(TypedDict):
    order_id: str
    items: list[OrderItem]


def calculate_total(items: list[OrderItem]) -> Decimal:
    total = Decimal("0")
    for item in items:
        price = Decimal(item["price"])
        quantity = item["quantity"]
        total = total + (price * quantity)
    return total


def build_receipt(order: OrderPayload) -> dict[str, str]:
    items = order["items"]
    total = calculate_total(items)
    return {
        "order_id": order["order_id"],
        "total": str(total),
    }


def main() -> None:
    order: OrderPayload = {
        "order_id": "demo-100",
        "items": [
            {"sku": "notebook", "price": "6.50", "quantity": 2},
            {"sku": "pencil", "price": "1.25", "quantity": 4},
        ],
    }

    receipt = build_receipt(order)
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
