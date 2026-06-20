from dataclasses import dataclass


@dataclass
class Order:
    order_id: int
    customer: str
    status: str


ORDERS: dict[int, Order] = {
    100: Order(order_id=100, customer="Ada", status="packed"),
    200: Order(order_id=200, customer="Grace", status="shipped"),
}


def load_order(order_id: int) -> Order:
    return ORDERS[order_id]


def serialize_order(order: Order) -> dict[str, object]:
    return {
        "order_id": order.order_id,
        "customer": order.customer,
        "status": order.status,
    }
