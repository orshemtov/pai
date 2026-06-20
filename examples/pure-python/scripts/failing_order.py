import json
from decimal import Decimal


def calculate_discount(payload: dict[str, object]) -> Decimal:
    amount = Decimal(str(payload["amount"]))
    rate = Decimal(str(payload["discount_rate"]))
    return amount * rate


def summarize_order(payload: dict[str, object]) -> str:
    discount = calculate_discount(payload)
    summary = {
        "customer": payload["customer_name"],
        "discount": str(discount),
    }
    return json.dumps(summary, sort_keys=True)


def main() -> None:
    payload: dict[str, object] = {
        "customer_name": "Ada",
        "amount": "42.00",
    }

    print(summarize_order(payload))


if __name__ == "__main__":
    main()
