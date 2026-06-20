from scripts.successful_order import OrderPayload, build_receipt


def test_build_receipt_calculates_total() -> None:
    order: OrderPayload = {
        "order_id": "demo-test",
        "items": [
            {"sku": "notebook", "price": "6.50", "quantity": 2},
            {"sku": "pencil", "price": "1.25", "quantity": 4},
        ],
    }

    receipt = build_receipt(order)

    assert receipt == {"order_id": "demo-test", "total": "18.00"}


def test_intentional_failure_demonstrates_pai_test_event() -> None:
    order: OrderPayload = {
        "order_id": "demo-test",
        "items": [
            {"sku": "notebook", "price": "6.50", "quantity": 2},
        ],
    }

    receipt = build_receipt(order)

    assert receipt["total"] == "12.00"
